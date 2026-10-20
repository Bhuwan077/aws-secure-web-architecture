#!/bin/bash
# ==============================================================================
# AWS EC2 Cloud-Init User Data Script
# Secure Zero-Touch Application Bootstrap
# ==============================================================================
set -euo pipefail

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "==> [$(date -u)] Starting automated instance provisioning..."

# Update and install dependencies
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-pip python3-venv nginx git curl jq

# Create dedicated non-root application user
useradd -r -s /usr/sbin/nologin -d /opt/aws-secure-web-architecture appuser || true

# Setup directories
APP_DIR="/opt/aws-secure-web-architecture"
DATA_DIR="/var/data"
LOG_DIR="/var/log/expense-tracker"

mkdir -p "${APP_DIR}" "${DATA_DIR}" "${LOG_DIR}"

# Clone repository or pull files
echo "==> Fetching application code..."
if [ ! -d "${APP_DIR}/app" ]; then
    # Clone from public repo if available, or initialize baseline
    git clone https://github.com/your-username/aws-secure-web-architecture.git "${APP_DIR}" || true
fi

# Fallback bootstrap if repository not yet cloned
if [ ! -f "${APP_DIR}/app/requirements.txt" ]; then
    mkdir -p "${APP_DIR}/app/src/templates" "${APP_DIR}/app/src/static/css" "${APP_DIR}/app/src/static/js"
    cat << 'EOF' > "${APP_DIR}/app/requirements.txt"
flask==3.0.3
gunicorn==22.0.0
pytest==8.2.0
python-dotenv==1.0.1
EOF
fi

# Set directory permissions (Principle of Least Privilege)
chown -R appuser:appuser "${DATA_DIR}" "${LOG_DIR}" "${APP_DIR}"
chmod 700 "${DATA_DIR}"
chmod 750 "${LOG_DIR}"

# Create Python Virtual Environment
VENV_DIR="/opt/venv"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip
if [ -f "${APP_DIR}/app/requirements.txt" ]; then
    "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/app/requirements.txt"
fi
chown -R appuser:appuser "${VENV_DIR}"

# Configure systemd service
cat << 'EOF' > /etc/systemd/system/expense-tracker.service
[Unit]
Description=AWS Portfolio Expense Tracker (Gunicorn)
After=network.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/aws-secure-web-architecture
Environment="PATH=/opt/venv/bin:/usr/local/bin:/usr/bin"
Environment="PYTHONPATH=/opt/aws-secure-web-architecture"
Environment="DATABASE_PATH=/var/data/expenses.db"
Environment="APP_ENV=production"
ExecStart=/opt/venv/bin/gunicorn \
    --workers 2 \
    --threads 2 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/expense-tracker/access.log \
    --error-logfile /var/log/expense-tracker/error.log \
    "app.src.app:app"

ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now expense-tracker || true

# Configure Nginx Reverse Proxy
cat << 'EOF' > /etc/nginx/sites-available/expense-tracker
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 2M;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location ~* \.(db|sqlite|sqlite3|env|git|sh|md)$ {
        deny all;
        return 404;
    }

    location /static/ {
        alias /opt/aws-secure-web-architecture/app/src/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /healthz {
        proxy_pass http://127.0.0.1:8000/healthz;
        proxy_set_header Host $host;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/expense-tracker /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# Install and configure CloudWatch Agent (optional monitoring)
curl -s https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb -o /tmp/amazon-cloudwatch-agent.deb
dpkg -i -E /tmp/amazon-cloudwatch-agent.deb || true
rm -f /tmp/amazon-cloudwatch-agent.deb

echo "==> [$(date -u)] EC2 Bootstrap completed successfully!"

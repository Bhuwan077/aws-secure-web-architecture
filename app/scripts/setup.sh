#!/usr/bin/env bash
# ==============================================================================
# Host Bootstrap Script for AWS Secure Web Application Architecture
# Automates user creation, non-root permissions, systemd service, and Nginx.
# Supports: Ubuntu 22.04/24.04 LTS & Amazon Linux 2023
# ==============================================================================
set -euo pipefail

echo "==> Starting Host Provisioning..."

# Detect Package Manager
if command -v apt-get &>/dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y python3 python3-pip python3-venv nginx curl git
elif command -v dnf &>/dev/null; then
    dnf update -y
    dnf install -y python3 python3-pip python3-virtualenv nginx curl git
fi

# Create dedicated non-root application user
if ! id -u appuser &>/dev/null; then
    echo "==> Creating system user: appuser"
    useradd -r -s /usr/sbin/nologin -d /opt/aws-secure-web-architecture appuser
fi

# Ensure target directories exist
APP_DIR="/opt/aws-secure-web-architecture"
DATA_DIR="/var/data"
LOG_DIR="/var/log/expense-tracker"

mkdir -p "${APP_DIR}" "${DATA_DIR}" "${LOG_DIR}"

# Set secure permissions: Database directory accessible only by appuser (0700)
chown -R appuser:appuser "${DATA_DIR}" "${LOG_DIR}"
chmod 700 "${DATA_DIR}"
chmod 750 "${LOG_DIR}"

# Setup Python Virtual Environment
VENV_DIR="/opt/venv"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/app/requirements.txt"

# Ensure app directory permissions
chown -R appuser:appuser "${APP_DIR}" "${VENV_DIR}"

# Install Systemd Service
cp "${APP_DIR}/app/scripts/expense-tracker.service" /etc/systemd/system/expense-tracker.service
systemctl daemon-reload
systemctl enable --now expense-tracker

# Configure Nginx
if [ -d "/etc/nginx/sites-available" ]; then
    cp "${APP_DIR}/app/scripts/nginx.conf" /etc/nginx/sites-available/expense-tracker
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/expense-tracker /etc/nginx/sites-enabled/
else
    cp "${APP_DIR}/app/scripts/nginx.conf" /etc/nginx/conf.d/expense-tracker.conf
    # Remove default server block if present
    sed -i 's/default_server//g' /etc/nginx/nginx.conf 2>/dev/null || true
fi

nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "==> Application service is running and proxied via Nginx on port 80!"
curl -s http://127.0.0.1/healthz | grep "healthy" && echo "==> Health Check Verified."

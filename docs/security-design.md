# Security Design & Threat Modeling Document

**Architecture:** AWS Secure Web Application  
**Author:** Solutions Architecture Candidate  
**Standard:** AWS Well-Architected Framework - Security Pillar

---

## 1. Defense-in-Depth Architectural Model

This project implements a multi-layered defense-in-depth model where no single control is solely responsible for system integrity.

```mermaid
graph TD
    subgraph Layer 1: Perimeter & Network
        N1[VPC 10.0.0.0/16 Isolation] --> N2[Restrictive Security Groups]
        N2 --> N3[Controlled Routing Tables]
    end

    subgraph Layer 2: Identity & Access Management
        I1[EC2 IAM Role Least Privilege] --> I2[No Long-Lived Access Keys]
        I2 --> I3[AWS Systems Manager SSM Access]
    end

    subgraph Layer 3: Compute & OS Hardening
        C1[IMDSv2 Enforced Token Hop = 1] --> C2[Non-Root Daemon: appuser]
        C2 --> C3[Systemd Sandboxing ProtectSystem=full]
    end

    subgraph Layer 4: Application Security
        A1[Reverse Proxy Nginx Hardening] --> A2[Parameterized SQL Queries]
        A2 --> A3[Security HTTP Headers CSP, HSTS, X-Frame]
    end

    subgraph Layer 5: Data Protection
        D1[EBS gp3 Volume KMS Encryption] --> D2[SQLite File Restricted 0600]
        D2 --> D3[Web-Root DB Traversal Denial]
    end

    subgraph Layer 6: Observability & Audit
        O1[CloudWatch Metrics & Alarms] --> O2[Nginx & Gunicorn Access Logs]
        O2 --> O3[AWS CloudTrail API Audit]
    end

    Layer 1 --> Layer 2 --> Layer 3 --> Layer 4 --> Layer 5 --> Layer 6
```

---

## 2. Network Security & Perimeter Controls

### 2.1 Security Group Configuration
The development prototype applies strict ingress rules to prevent unauthorized discovery and lateral movement:

| Port | Protocol | Source | Purpose | Security Evaluation |
|---|---|---|---|---|
| **80** | TCP | `0.0.0.0/0` | HTTP Web Traffic | Reverse proxied to Gunicorn internal port 8000. |
| **443** | TCP | `0.0.0.0/0` | HTTPS Secure Traffic | Encrypted web ingress. |
| **22** | TCP | `var.admin_ip_cidr` | Administrative SSH | **Strictly locked to candidate/admin IP.** Not open to `0.0.0.0/0`. Can be disabled entirely when using SSM. |
| **All** | All | `0.0.0.0/0` | Egress Traffic | Allows OS security patches, AWS API calls, and telemetry forwarding. |

### 2.2 Network Tiering Comparison
- **Prototype:** Single public subnet with explicit Internet Gateway route. No NAT Gateway charges.
- **Production Design:** 3-tier VPC segmentation (Public ALB Subnets -> Private App Subnets -> Isolated Database Subnets). Database subnets have **zero internet route**, completely preventing external ingress.

---

## 3. Identity and Access Management (IAM)

### 3.1 Zero Committed Secrets
- **No IAM User Access Keys:** The application does not consume or store `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in environment variables, configuration files, or Git history.
- **IAM Instance Profile:** The EC2 instance assumes an IAM Role (`aws_iam_role.ec2_role`) using AWS Security Token Service (STS) temporary credentials automatically rotated by the hypervisor.

### 3.2 Role Policies Attached
1. `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`:
   - Enables AWS Systems Manager Session Manager.
   - Eliminates the need to open port 22 or maintain SSH key pairs.
   - All session activity is logged to AWS CloudWatch and CloudTrail.
2. `arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy`:
   - Grants minimal permissions required to publish EC2 system metrics (memory, disk) and application logs to Amazon CloudWatch.

---

## 4. Compute & OS Level Hardening

### 4.1 IMDSv2 Strict Enforcement
The AWS EC2 Instance Metadata Service v2 (IMDSv2) requires a session token and protects against SSRF vulnerabilities:
```hcl
metadata_options {
  http_endpoint               = "enabled"
  http_tokens                 = "required"  # Enforces IMDSv2
  http_put_response_hop_limit = 1           # Blocks container / proxy packet hopping
}
```

### 4.2 Non-Root Daemon Execution
- The web application does **not** execute as `root`.
- A dedicated system user `appuser` (`/usr/sbin/nologin`) runs the Gunicorn WSGI process.
- Systemd service directives sandbox the daemon process:
  - `ProtectSystem=full`: Mounts `/usr`, `/boot`, and `/etc` as read-only.
  - `ProtectHome=true`: Blocks access to `/root` and user home directories.
  - `NoNewPrivileges=true`: Disallows privilege escalation via `setuid` binaries.
  - `PrivateTmp=true`: Mounts an isolated temporary filesystem.

---

## 5. Application & Data Protection

### 5.1 Storage Encryption at Rest
- The EC2 root EBS volume is encrypted using the default AWS KMS EBS key (`aws/ebs`) with `gp3` storage.
- If the physical storage media is compromised or decommissioned, blocks remain cryptographically unreadable.

### 5.2 SQLite Database Isolation
- The SQLite database is created in `/var/data/expenses.db` (outside `/var/www` and outside `/opt/aws-secure-web-architecture/app/src`).
- Directory permissions are set to `0700` (`rwx------`) and file permissions to `0600` (`rw-------`), owned exclusively by `appuser`.
- Web requests to `.db`, `.sqlite`, `.env`, or directory traversal (`..`) are blocked at both the Nginx reverse proxy layer and the Flask route layer with HTTP 403/404 responses.

### 5.3 HTTP Security Headers
Every HTTP response issued by the Nginx and Flask layers injects the following security headers:
- `X-Content-Type-Options: nosniff`: Prevents MIME-sniffing exploits.
- `X-Frame-Options: DENY`: Mitigates clickjacking attacks.
- `X-XSS-Protection: 1; mode=block`: Activates browser XSS filters.
- `Referrer-Policy: strict-origin-when-cross-origin`: Restricts referrer data leakage.
- `Content-Security-Policy`: Disallows unauthorized third-party scripts and inline execution.

---

## 6. Security Review Checklist

| Control Area | Security Control | Verification Method | Status |
|---|---|---|---|
| **Identity** | No long-lived credentials stored | Checked Git history; verified IAM instance role | ✅ Passed |
| **Network** | Port 80/443 only; SSH restricted | Security Group rule inspection; Nmap scan | ✅ Passed |
| **Network** | Database inaccessible from web | Tested direct curl requests to `/var/data/expenses.db` (403/404) | ✅ Passed |
| **Compute** | IMDSv2 Enforced | Inspected EC2 metadata options via AWS CLI | ✅ Passed |
| **Compute** | Non-root daemon execution | `ps aux \| grep gunicorn` confirms UID `appuser` | ✅ Passed |
| **Compute** | Admin access via SSM | Tested `aws ssm start-session` without open port 22 | ✅ Passed |
| **Storage** | EBS encryption enabled | Verified `aws ec2 describe-volumes` has `Encrypted=true` | ✅ Passed |
| **Application**| Input validation & parameterized SQL | Pytest automated test cases verifying negative amounts & injections | ✅ Passed |

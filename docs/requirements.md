# Requirements Specification: Secure AWS Web Architecture

**Project:** Secure & Highly Available AWS Web Application  
**Author:** Solutions Architecture Candidate  
**Target AWS Budget:** \$0.00 / month (Free Tier Eligible)  
**Status:** Implemented (Prototype) / Documented (Production Blueprint)

---

## 1. Executive Summary

This project delivers a secure, modular, cloud-native web application demonstrating core AWS infrastructure design, network isolation, security best practices, Infrastructure as Code (IaC) with Terraform, and rigorous cost consciousness.

The repository addresses a critical real-world engineering challenge: **How to demonstrate enterprise-grade AWS architecture design, security hardening, and reliability without incurring recurring cloud expenses for a portfolio demonstration.**

---

## 2. Functional Requirements (FR)

| ID | Requirement | Description | Prototype Status | Production Status |
|---|---|---|---|---|
| **FR-01** | Record Management | Users can create, view, update, and delete cloud expenditure records via a web UI. | ✅ Implemented | ✅ Supported |
| **FR-02** | Aggregated Metrics | The system computes real-time summary statistics (total spend, average cost, cost center breakdown). | ✅ Implemented | ✅ Supported |
| **FR-03** | Search & Filtering | Users can filter expenses by predefined categories and search across titles and descriptions. | ✅ Implemented | ✅ Supported |
| **FR-04** | RESTful API | Provides JSON endpoints (`/api/expenses`, `/api/stats`, `/healthz`) for programmatic access. | ✅ Implemented | ✅ Supported |
| **FR-05** | Health Check Endpoint | Dedicated `/healthz` probe returns HTTP 200 with JSON status for ALB target groups and monitoring agents. | ✅ Implemented | ✅ Supported |
| **FR-06** | Input Validation | Validates input bounds (positive numeric amounts, sanitized strings, allowable category enum). | ✅ Implemented | ✅ Supported |

---

## 3. Non-Functional Requirements (NFR)

### 3.1 Security & Access Control
- **NFR-SEC-01 (Network Ingress):** Inbound traffic must be restricted to standard web ports (80/443). Administrative SSH access must be restricted to a specific developer IP CIDR or routed through AWS Systems Manager (SSM) Session Manager.
- **NFR-SEC-02 (Data Isolation):** Application database files must not be accessible via HTTP requests or stored in public web-root directories.
- **NFR-SEC-03 (Least Privilege IAM):** Instances must assume an IAM Role with minimal required permissions (`AmazonSSMManagedInstanceCore`, `CloudWatchAgentServerPolicy`). No permanent AWS Access Keys or Secret Keys may reside on the host or in source code.
- **NFR-SEC-04 (IMDSv2 Enforcement):** EC2 Instance Metadata Service v2 (IMDSv2) must be strictly enforced with a token hop limit of 1 to mitigate Server-Side Request Forgery (SSRF) risks.
- **NFR-SEC-05 (Daemon Isolation):** The application daemon must run under a dedicated, non-privileged system user (`appuser`) with sandboxed systemd controls (`ProtectSystem=full`, `NoNewPrivileges=true`).

### 3.2 Reliability & Availability
- **NFR-REL-01 (Prototype):** The single-instance development prototype runs inside a dedicated public subnet. If the host fails, service disruption occurs (evaluated and documented trade-off).
- **NFR-REL-02 (Production Blueprint):** The recommended enterprise architecture spans multiple Availability Zones (AZs) with an Application Load Balancer, an Auto Scaling Group across private subnets, and an Amazon RDS Multi-AZ database.

### 3.3 Cost Consciousness & Resource Control
- **NFR-COST-01:** The deployed prototype must remain within AWS Free Tier limits (\$0.00/month target):
  - EC2: 750 hours/month of `t2.micro` or `t3.micro`.
  - EBS: 20 GB gp3 volume (within the 30 GB Free Tier ceiling).
  - Networking: Zero NAT Gateway charges in prototype mode (direct route to Internet Gateway).
  - Database: Local SQLite on encrypted EBS volume instead of multi-AZ RDS.
- **NFR-COST-02:** Teardown reproducibility must be guaranteed via `terraform destroy` to eliminate zombie resources and unexpected bills.

### 3.4 Infrastructure as Code (IaC) & Maintainability
- **NFR-IAC-01:** All cloud networking, compute, IAM roles, and security groups must be provisioned and managed declaratively using Terraform (>= 1.5.0).
- **NFR-IAC-02:** Configurations must follow modular conventions with strict variable validation, standard tags, and clear outputs.

---

## 4. Architecture Scope Comparison

```
+------------------------------------+------------------------------------------+
| Development Prototype (Deployed)   | Production Architecture (Documented)    |
+------------------------------------+------------------------------------------+
| Single AWS VPC (10.0.0.0/16)       | Multi-Tier Multi-AZ VPC (10.0.0.0/16)   |
| 1 Public Subnet (10.0.1.0/24)      | 2 Public, 2 Private App, 2 Private DB   |
| 1 EC2 Instance (t3.micro)          | Auto Scaling Group (Min: 2, Max: 6)     |
| Direct Internet Gateway Routing    | Public ALB + Managed NAT Gateways        |
| Local SQLite on Encrypted EBS      | Multi-AZ Amazon RDS PostgreSQL/MySQL     |
| Cost: ~$0.00 / month (Free Tier)   | Cost: ~$132.84 / month (Documented)     |
+------------------------------------+------------------------------------------+
```

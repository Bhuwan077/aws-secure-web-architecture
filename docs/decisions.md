# Architecture Decision Records (ADR)

**Project:** AWS Secure Web Architecture  
**Format:** Michael Nygard ADR Template  
**Status:** Accepted & Evaluated

---

## ADR-001: SQLite for Prototype vs Managed Amazon RDS for Production

### Context
A relational database is required to store expense records with ACID compliance. Managed database solutions like Amazon RDS PostgreSQL or MySQL offer automated failover, point-in-time recovery, and multi-AZ replication. However, an always-on RDS instance (`db.t4g.micro` Multi-AZ) costs roughly \$30–\$35 per month, violating our \$0.00 portfolio budget goal.

### Decision
- **Prototype Implementation:** Deploy a local SQLite database in a secured directory (`/var/data/expenses.db`) on the EC2 host. Protect it with strict Linux permissions (`0700` directory, `0600` file) and block all HTTP path traversal to `.db` files.
- **Production Architecture Proposal:** Migrate to Amazon RDS PostgreSQL Multi-AZ running across private database subnets with automated snapshots, KMS encryption, and connection pooling.

### Consequences
- **Positive:** Reduces running database costs to **\$0.00**; zero latency IPC access; simplified local development and CI testing.
- **Negative:** The prototype database is co-located on the compute instance; an instance termination destroys unbacked-up data.
- **Mitigation:** The production blueprint (`terraform/production-blueprint/rds.tf`) completely solves data durability and horizontal scaling.

---

## ADR-002: Single-Instance EC2 vs Multi-AZ ALB + Auto Scaling Group

### Context
The application must be accessible over the internet. A highly available production system requires horizontal scaling and self-healing across at least two Availability Zones behind an Application Load Balancer (ALB). An ALB carries a minimum base fee of ~$16–$19/month regardless of traffic volume.

### Decision
- **Prototype:** Provision a single EC2 instance (`t3.micro` or `t2.micro` Free Tier eligible) inside a public subnet with a direct route to an Internet Gateway.
- **Production Blueprint:** Deploy an Application Load Balancer distributing traffic to an Auto Scaling Group (min 2, max 6 instances) placed inside private application subnets.

### Consequences
- **Positive:** Enables full testing of VPC, security groups, systemd, Gunicorn, Nginx, and IAM without incurring ALB hourly charges.
- **Negative:** Single Point of Failure (SPOF). If the instance hypervisor crashes or is rebooted, the application experiences temporary downtime.
- **Mitigation:** Document failure test results in `docs/test-results.md` and supply the complete production IaC in `terraform/production-blueprint/`.

---

## ADR-003: AWS Systems Manager (SSM) Session Manager vs Inbound SSH (Port 22)

### Context
Administrative shell access is required for operating system debugging, log inspection, and troubleshooting. Traditional approaches open TCP port 22 to `0.0.0.0/0` or deploy an intermediate Bastion Host (jump box).

### Decision
Attach the AWS-managed policy `AmazonSSMManagedInstanceCore` to the EC2 IAM Instance Profile. Restrict or completely close port 22 in the Security Group and rely on AWS Systems Manager Session Manager for administrative shell access.

### Consequences
- **Positive:**
  - **Zero Open Ports:** Inbound port 22 does not need to be exposed to the public internet.
  - **No Key Management:** Eliminates risks associated with leaked private SSH keys (`.pem`).
  - **Audit Logging:** Every command and session is logged and audited in AWS CloudTrail and CloudWatch Logs.
  - **Centralized Access Control:** Access is governed via AWS IAM identity policies, supporting Multi-Factor Authentication (MFA).
- **Negative:** Requires the SSM agent to run on the EC2 instance (pre-installed by default on Ubuntu and Amazon Linux).

---

## ADR-004: HashiCorp Terraform vs AWS CloudFormation / CDK

### Context
Infrastructure must be provisioned deterministically as code (IaC) to enable version control, automated peer reviews, and clean teardowns.

### Decision
Use **HashiCorp Terraform** with declarative HCL (HashiCorp Configuration Language) and the official AWS provider (`hashicorp/aws`).

### Consequences
- **Positive:**
  - Widely recognized industry standard demonstrating multi-cloud IaC proficiency to recruiters.
  - Granular state management and execution planning via `terraform plan`.
  - Clean modularity with separate files for variables, security, and outputs.
- **Negative:** Requires state file management (stored locally for portfolio demonstration; S3 + DynamoDB locking documented for production).

---

## ADR-005: Network Isolation and Multi-Tier VPC Segmentation

### Context
Enterprise compliance (PCI-DSS, SOC 2, HIPAA) requires rigorous network segmentation between public ingress, application runtimes, and persistence layers.

### Decision
- Segment the production VPC into 3 distinct tiers across 2 Availability Zones:
  1. **Public Tier (`10.0.1.0/24`, `10.0.2.0/24`):** ALB and NAT Gateways.
  2. **Private App Tier (`10.0.10.0/24`, `10.0.11.0/24`):** EC2 Auto Scaling instances with outbound-only internet access via NAT.
  3. **Private Database Tier (`10.0.20.0/24`, `10.0.21.0/24`):** RDS Multi-AZ instances with **zero internet route**.
- Chain security groups so each tier only accepts traffic directly from its authorized upstream tier.

### Consequences
- **Positive:** Even if a web vulnerability compromises the application runtime, an attacker cannot directly route to the database from the public internet.
- **Negative:** Increased networking complexity and routing tables; managed NAT Gateways incur additional operational cost.

# ==============================================================================
# Security Groups & IAM Role Configuration
# Principle of Least Privilege & Defense in Depth
# ==============================================================================

# --- EC2 Security Group ---
resource "aws_security_group" "web_sg" {
  name        = "${var.environment}-web-server-sg"
  description = "Security group for web application instance restricting ingress"
  vpc_id      = aws_vpc.main.id

  # Inbound HTTP (Public traffic to reverse proxy)
  ingress {
    description = "Allow inbound HTTP from public internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Inbound HTTPS (For TLS termination if configured)
  ingress {
    description = "Allow inbound HTTPS from public internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Administrative Inbound SSH (Restricted to specified CIDR)
  ingress {
    description = "Restricted administrative SSH access (Use SSM Session Manager when possible)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_ip_cidr]
  }

  # Outbound Egress: Allow outbound connectivity for package updates, SSM, and CloudWatch
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-web-sg"
  }
}

# --- IAM Role for EC2 Instance ---
resource "aws_iam_role" "ec2_role" {
  name = "${var.environment}-ec2-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.environment}-ec2-iam-role"
  }
}

# Attach AWS Systems Manager (SSM) Managed Instance Core Policy
# Best Practice: Enables remote interactive shell access without opening port 22 or storing SSH keys!
resource "aws_iam_role_policy_attachment" "ssm_core" {
  count      = var.enable_ssm ? 1 : 0
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach CloudWatch Agent Policy for publishing custom metrics & OS logs
resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Instance Profile to attach IAM Role to EC2 Instance
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.environment}-ec2-instance-profile"
  role = aws_iam_role.ec2_role.name
}

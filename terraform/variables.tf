variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "dev"
}

variable "owner_tag" {
  description = "Identifier for the resource owner or candidate"
  type        = string
  default     = "solutions-architect-candidate"
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet hosting the web tier"
  type        = string
  default     = "10.0.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance size (use Free Tier eligible t2.micro or t3.micro)"
  type        = string
  default     = "t3.micro"
}

variable "admin_ip_cidr" {
  description = "Specific IP CIDR allowed for administrative SSH access (e.g. '203.0.113.25/32'). Do not use 0.0.0.0/0 in production."
  type        = string
  default     = "0.0.0.0/0"
}

variable "ssh_key_name" {
  description = "Optional name of existing AWS EC2 Key Pair for SSH access. Leave empty if managing via AWS Systems Manager (SSM)."
  type        = string
  default     = ""
}

variable "enable_ssm" {
  description = "Attach AWS Systems Manager Core policy to EC2 IAM Role for secure zero-open-port management"
  type        = bool
  default     = true
}

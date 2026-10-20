# 3-Tier Layered Security Groups

# Tier 1: Public ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.environment}-alb-sg"
  description = "Controls traffic to Application Load Balancer"
  vpc_id      = aws_vpc.prod.id

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP redirect from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "Forward to App Tier"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [] # Chained in app SG
  }

  tags = {
    Name = "${var.environment}-alb-sg"
    Tier = "Security-Tier-1-ALB"
  }
}

# Tier 2: Private App Tier Security Group
resource "aws_security_group" "app" {
  name        = "${var.environment}-app-instances-sg"
  description = "Allows incoming traffic ONLY from ALB"
  vpc_id      = aws_vpc.prod.id

  ingress {
    description     = "Traffic strictly from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Outbound to internet via NAT Gateway for updates"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-app-sg"
    Tier = "Security-Tier-2-App"
  }
}

# Tier 3: Private Database Security Group
resource "aws_security_group" "db" {
  name        = "${var.environment}-rds-database-sg"
  description = "Allows incoming traffic ONLY from App EC2 instances"
  vpc_id      = aws_vpc.prod.id

  ingress {
    description     = "Database port strictly from App SG"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description = "No outbound internet access"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/16"]
  }

  tags = {
    Name = "${var.environment}-db-sg"
    Tier = "Security-Tier-3-DB"
  }
}

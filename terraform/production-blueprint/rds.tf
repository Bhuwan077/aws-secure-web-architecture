# Amazon RDS PostgreSQL Database (Multi-AZ Production Tier)

resource "aws_db_subnet_group" "db_subnets" {
  name       = "${var.environment}-db-subnet-group"
  subnet_ids = aws_subnet.private_db[*].id

  tags = {
    Name = "${var.environment}-db-subnet-group"
  }
}

resource "aws_db_instance" "db" {
  identifier            = "${var.environment}-postgres-db"
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  engine                = "postgres"
  engine_version        = "16.1"
  instance_class        = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = "SuperSecurePlaceholderDbPassword2026!" # In actual production, inject via AWS Secrets Manager

  db_subnet_group_name   = aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids = [aws_security_group.db.id]

  # High Availability Setting
  multi_az = true

  # Security & Compliance
  storage_encrypted   = true
  publicly_accessible = false
  skip_final_snapshot = true # For demo simplicity; false in enterprise

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Sun:04:30-Sun:05:30"

  tags = {
    Name = "${var.environment}-rds-postgres"
  }
}

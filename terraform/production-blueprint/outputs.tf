output "alb_dns_name" {
  description = "Application Load Balancer DNS entrypoint"
  value       = aws_lb.main.dns_name
}

output "rds_endpoint" {
  description = "Private database endpoint (accessible only from app tier)"
  value       = aws_db_instance.db.endpoint
}

output "vpc_id" {
  description = "Production VPC ID"
  value       = aws_vpc.prod.id
}

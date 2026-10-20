output "vpc_id" {
  description = "The ID of the provisioned VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "The ID of the public web subnet"
  value       = aws_subnet.public.id
}

output "instance_id" {
  description = "The EC2 Instance ID"
  value       = aws_instance.web.id
}

output "instance_public_ip" {
  description = "Public IPv4 address assigned to the EC2 instance"
  value       = aws_instance.web.public_ip
}

output "instance_public_dns" {
  description = "Public DNS hostname of the EC2 instance"
  value       = aws_instance.web.public_dns
}

output "application_url" {
  description = "Direct browser URL to access the deployed application"
  value       = "http://${aws_instance.web.public_ip}"
}

output "health_check_url" {
  description = "Application health check endpoint for monitoring"
  value       = "http://${aws_instance.web.public_ip}/healthz"
}

output "ssm_connect_command" {
  description = "Secure zero-open-port command to start an interactive AWS SSM Session"
  value       = "aws ssm start-session --target ${aws_instance.web.id} --region ${var.aws_region}"
}

output "ssh_connect_command" {
  description = "SSH connection string (requires private key and your IP in admin_ip_cidr)"
  value       = var.ssh_key_name != "" ? "ssh -i path/to/${var.ssh_key_name}.pem ubuntu@${aws_instance.web.public_ip}" : "SSH Key not configured. Connect securely using SSM Session Manager instead."
}

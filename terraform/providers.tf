provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AWS-Secure-Web-Architecture"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner_tag
      CostCenter  = "Portfolio-Demo"
    }
  }
}

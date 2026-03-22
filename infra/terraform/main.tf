terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "gold-agent-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.aws_region
}

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

module "dynamodb" {
  source       = "./modules/dynamodb"
  project_name = var.project_name
  environment  = var.environment
}

module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
  environment  = var.environment

  # Pass ARNs from other modules
  prices_bucket_arn       = module.s3.prices_bucket_arn
  live_prices_table_arn   = module.dynamodb.live_prices_table_arn
  source_health_table_arn = module.dynamodb.source_health_table_arn
  quota_tracker_table_arn = module.dynamodb.quota_tracker_table_arn
}
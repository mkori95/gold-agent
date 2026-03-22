variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name — used as prefix for all resource names"
  type        = string
  default     = "gold-agent"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}
variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "prices_bucket_arn" {
  description = "ARN of the S3 prices bucket"
  type        = string
}

variable "live_prices_table_arn" {
  description = "ARN of the live_prices DynamoDB table"
  type        = string
}

variable "source_health_table_arn" {
  description = "ARN of the source_health DynamoDB table"
  type        = string
}

variable "quota_tracker_table_arn" {
  description = "ARN of the quota_tracker DynamoDB table"
  type        = string
}
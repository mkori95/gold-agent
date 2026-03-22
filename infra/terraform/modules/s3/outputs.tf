output "prices_bucket_name" {
  description = "Name of the prices S3 bucket"
  value       = aws_s3_bucket.prices.id
}

output "prices_bucket_arn" {
  description = "ARN of the prices S3 bucket"
  value       = aws_s3_bucket.prices.arn
}
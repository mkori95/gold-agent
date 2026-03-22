output "consolidator_role_arn" {
  description = "ARN of the consolidator Lambda IAM role"
  value       = aws_iam_role.consolidator.arn
}

output "consolidator_role_name" {
  description = "Name of the consolidator Lambda IAM role"
  value       = aws_iam_role.consolidator.name
}
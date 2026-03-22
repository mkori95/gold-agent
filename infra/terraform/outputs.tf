output "consolidator_role_arn" {
  description = "ARN of the consolidator Lambda IAM role"
  value       = module.iam.consolidator_role_arn
}
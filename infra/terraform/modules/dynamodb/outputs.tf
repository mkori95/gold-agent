output "live_prices_table_name" {
  value = aws_dynamodb_table.live_prices.name
}

output "source_health_table_name" {
  value = aws_dynamodb_table.source_health.name
}

output "quota_tracker_table_name" {
  value = aws_dynamodb_table.quota_tracker.name
}
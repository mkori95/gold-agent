# ============================================================
# live_prices — latest consensus price per metal
# Partition key: metal (gold, silver, platinum, copper)
# ============================================================
resource "aws_dynamodb_table" "live_prices" {
  name         = "${var.project_name}-live-prices"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "metal"

  attribute {
    name = "metal"
    type = "S"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ============================================================
# source_health — circuit breaker state per data source
# Partition key: source_id (gold_api_com, metals_dev etc)
# ============================================================
resource "aws_dynamodb_table" "source_health" {
  name         = "${var.project_name}-source-health"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "source_id"

  attribute {
    name = "source_id"
    type = "S"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ============================================================
# quota_tracker — API usage counts per source per month
# Partition key: source_id
# Sort key: month (2026-03) — allows querying by source + month
# ============================================================
resource "aws_dynamodb_table" "quota_tracker" {
  name         = "${var.project_name}-quota-tracker"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "source_id"
  range_key    = "month"

  attribute {
    name = "source_id"
    type = "S"
  }

  attribute {
    name = "month"
    type = "S"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
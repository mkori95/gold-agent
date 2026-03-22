# ============================================================
# IAM Role — Consolidator Lambda
# Allows Lambda service to assume this role
# ============================================================
resource "aws_iam_role" "consolidator" {
  name = "${var.project_name}-consolidator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ============================================================
# IAM Policy — Consolidator Lambda permissions
# DynamoDB + S3 + CloudWatch Logs + Secrets Manager
# ============================================================
resource "aws_iam_policy" "consolidator" {
  name        = "${var.project_name}-consolidator-policy"
  description = "Permissions for Gold Agent consolidator Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [

      # --------------------------------------------------------
      # DynamoDB — read/write on all 3 tables
      # --------------------------------------------------------
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.live_prices_table_arn,
          var.source_health_table_arn,
          var.quota_tracker_table_arn
        ]
      },

      # --------------------------------------------------------
      # S3 — read/write on prices bucket
      # --------------------------------------------------------
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.prices_bucket_arn,
          "${var.prices_bucket_arn}/*"
        ]
      },

      # --------------------------------------------------------
      # CloudWatch Logs — Lambda logging
      # --------------------------------------------------------
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },

      # --------------------------------------------------------
      # Secrets Manager — read API keys
      # --------------------------------------------------------
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:ap-south-1:*:secret:gold-agent/*"
        ]
      }

      # --------------------------------------------------------
      # Future roles — add here as phases progress
      # Phase 2: whatsapp-handler-role
      # Phase 2: agent-brain-role
      # Phase 2: alert-checker-role
      # Phase 3: rate-validator-role
      # Phase 4: report-role
      # --------------------------------------------------------
    ]
  })
}

# ============================================================
# Attach policy to role
# ============================================================
resource "aws_iam_role_policy_attachment" "consolidator" {
  role       = aws_iam_role.consolidator.name
  policy_arn = aws_iam_policy.consolidator.arn
}
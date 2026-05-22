#!/usr/bin/env bash
# deploy_whisper.sh — builds the Whisper container image, pushes to ECR,
# sets the S3 lifecycle rule for voice-temp/, then runs sam build + sam deploy.
#
# Run once to set up Enhancement 2 (voice support), then re-run any time
# you change src/lambdas/whisper-transcriber/handler.py or Dockerfile.
#
# Prerequisites:
#   - Docker running
#   - AWS CLI configured (aws sts get-caller-identity works)
#   - SAM CLI installed (sam --version works)
#   - gold-agent-phase2-role has:
#       s3:PutObject, s3:DeleteObject on gold-agent-prices/voice-temp/*
#       s3:GetObject                  on gold-agent-prices/voice-temp/*
#       lambda:InvokeFunction         on gold-agent-whisper-transcriber

set -euo pipefail

REGION="ap-south-1"
ECR_REPO="gold-agent-whisper"
S3_BUCKET="gold-agent-prices"
STACK_NAME="gold-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Resolve account ID ────────────────────────────────────────────────────────
echo "Resolving AWS account..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "$REGION")
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:latest"

echo ""
echo "  Account : $ACCOUNT_ID"
echo "  Region  : $REGION"
echo "  Image   : $IMAGE_URI"
echo ""

# ── 1. ECR repository ─────────────────────────────────────────────────────────
echo "[1/6] ECR repository..."
if aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$REGION" &>/dev/null; then
  echo "      Already exists — skipping create"
else
  aws ecr create-repository \
    --repository-name "$ECR_REPO" \
    --region "$REGION" \
    --image-scanning-configuration scanOnPush=true \
    --output table
  echo "      Created: $ECR_REPO"
fi

# ── 2. Docker login ───────────────────────────────────────────────────────────
echo "[2/6] Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin \
  "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# ── 3. Build image ────────────────────────────────────────────────────────────
echo "[3/6] Building Docker image (linux/amd64) — this takes ~5 min first time..."
docker build \
  --platform linux/amd64 \
  -t "${ECR_REPO}:latest" \
  "${SCRIPT_DIR}/src/lambdas/whisper-transcriber/"

# ── 4. Push to ECR ────────────────────────────────────────────────────────────
echo "[4/6] Pushing image to ECR..."
docker tag "${ECR_REPO}:latest" "$IMAGE_URI"
docker push "$IMAGE_URI"
echo "      Pushed: $IMAGE_URI"

# ── 5. S3 lifecycle rule for voice-temp/ ─────────────────────────────────────
echo "[5/6] Setting S3 lifecycle rule (voice-temp/ expires after 1 day)..."
aws s3api put-bucket-lifecycle-configuration \
  --bucket "$S3_BUCKET" \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "voice-temp-auto-delete",
      "Filter": {"Prefix": "voice-temp/"},
      "Status": "Enabled",
      "Expiration": {"Days": 1}
    }]
  }'
echo "      Done"

# ── 6. SAM build + deploy ─────────────────────────────────────────────────────
echo "[6/6] SAM build + deploy..."
cd "$SCRIPT_DIR"
sam build

if [ -f "$SCRIPT_DIR/samconfig.toml" ]; then
  sam deploy --no-confirm-changeset --resolve-image-repos
else
  sam deploy \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --resolve-s3 \
    --resolve-image-repos \
    --no-confirm-changeset
fi

echo ""
echo "Done. gold-agent-whisper-transcriber is live."
echo ""
echo "IAM checklist (one-time, if not already done):"
echo "  gold-agent-phase2-role needs:"
echo "    s3:PutObject + s3:DeleteObject  → arn:aws:s3:::gold-agent-prices/voice-temp/*"
echo "    s3:GetObject                    → arn:aws:s3:::gold-agent-prices/voice-temp/*"
echo "    lambda:InvokeFunction           → arn:aws:lambda:ap-south-1:${ACCOUNT_ID}:function:gold-agent-whisper-transcriber"

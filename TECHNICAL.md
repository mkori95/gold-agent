# Gold Agent — Technical Reference

> Ops runbook: all commands, data locations, Lambda inventory, CloudWatch, and end-to-end flow descriptions.

---

## Quick Reference — Lambda Invoke Commands

Run any Lambda manually from your terminal. All commands write output to `/tmp/*.json`.

```bash
# ── Consolidator — fetch prices from all APIs and write to DynamoDB + S3
aws lambda invoke \
  --function-name gold-agent-consolidator \
  --region ap-south-1 \
  --invocation-type RequestResponse \
  --payload '{}' /tmp/consolidator.json \
  && cat /tmp/consolidator.json | python3 -m json.tool

# ── Daily Digest — send WhatsApp template to all daily_summary subscribers
aws lambda invoke \
  --function-name gold-agent-daily-digest \
  --region ap-south-1 \
  --invocation-type RequestResponse \
  --payload '{}' /tmp/digest.json \
  && cat /tmp/digest.json

# ── Alert Checker — check all active alerts against current DynamoDB prices
aws lambda invoke \
  --function-name gold-agent-alert-checker \
  --region ap-south-1 \
  --invocation-type RequestResponse \
  --payload '{}' /tmp/alerts.json \
  && cat /tmp/alerts.json

# ── Agent Brain — simulate a user message end-to-end (replace phone number)
aws lambda invoke \
  --function-name gold-agent-brain \
  --region ap-south-1 \
  --invocation-type RequestResponse \
  --payload '{"phone_number":"91XXXXXXXXXX","text":"What is gold price today?","language":"en","city":"Hyderabad","intent":"price_query","history":[]}' \
  /tmp/brain.json \
  && cat /tmp/brain.json

# ── WhatsApp Handler — simulate a Meta webhook payload
aws lambda invoke \
  --function-name gold-agent-whatsapp-handler \
  --region ap-south-1 \
  --invocation-type RequestResponse \
  --payload '{"body":{"entry":[{"changes":[{"value":{"messages":[{"id":"test_id","from":"91XXXXXXXXXX","type":"text","text":{"body":"gold price"},"timestamp":"1716000000"}],"contacts":[{"profile":{"name":"Test User"}}]}}]}]}}' \
  /tmp/whatsapp.json \
  && cat /tmp/whatsapp.json

# ── Whisper Transcriber — process a voice note already in S3
aws lambda invoke \
  --function-name gold-agent-whisper-transcriber \
  --region ap-south-1 \
  --invocation-type RequestResponse \
  --payload '{"s3_bucket":"gold-agent-prices","s3_key":"voice-temp/test.ogg","phone_number":"91XXXXXXXXXX","language_hint":"en"}' \
  /tmp/whisper.json \
  && cat /tmp/whisper.json
```

> **Important:** Only invoke the consolidator during Indian trading hours (10 AM – 6 PM IST).
> Off-hours RapidAPI data is stale and the DynamoDB sanity guard will skip the gold write.

---

## Quick Reference — CloudWatch Log Tailing

```bash
# Live tail — watch in real time as messages arrive (most useful for debugging)
aws logs tail /aws/lambda/gold-agent-whatsapp-handler  --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-brain             --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-consolidator      --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-daily-digest      --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-alert-checker     --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-whisper-transcriber --follow --region ap-south-1

# Last consolidator run — check what was written and which sources responded
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-consolidator \
  --region ap-south-1 \
  --start-time $(($(date -u +%s) - 3600))000 \
  --filter-pattern "WRITTEN OK"

# Check if consolidator skipped gold (stale data guard triggered)
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-consolidator \
  --region ap-south-1 \
  --start-time $(($(date -u +%s) - 86400))000 \
  --filter-pattern "SKIPPED"

# Check scraper errors (API quota, 403, timeouts)
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-consolidator \
  --region ap-south-1 \
  --start-time $(($(date -u +%s) - 86400))000 \
  --filter-pattern "ERROR"

# Check digest delivery — how many sent vs failed
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-daily-digest \
  --region ap-south-1 \
  --start-time $(($(date -u +%s) - 86400))000 \
  --filter-pattern "digest complete"

# Check alert checker — how many alerts fired today
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-alert-checker \
  --region ap-south-1 \
  --start-time $(($(date -u +%s) - 86400))000 \
  --filter-pattern "Alert run complete"

# Watch a full message conversation (replace phone number)
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-brain \
  --region ap-south-1 \
  --start-time $(($(date -u +%s) - 3600))000 \
  --filter-pattern "91XXXXXXXXXX"
```

---

## Quick Reference — DynamoDB Health Check

```bash
# Check current gold price and quality in DynamoDB (most important check)
aws dynamodb get-item \
  --table-name gold-agent-live-prices \
  --key '{"metal": {"S": "gold"}}' \
  --region ap-south-1 \
  --output json | python3 -c "
import json, sys
item = json.load(sys.stdin).get('Item', {})
print('22K per gram: ₹' + item.get('price_22k_inr', {}).get('S', '?'))
print('24K per gram: ₹' + item.get('price_24k_inr', {}).get('S', '?'))
print('USD spot:    \$' + item.get('price_usd', {}).get('S', '?'))
print('Confidence: ', item.get('confidence', {}).get('S', '?'))
print('Sources:    ', [x['S'] for x in item.get('sources_used', {}).get('L', [])])
print('Updated:    ', item.get('updated_at', {}).get('S', '?'))
"

# List all daily digest subscribers
aws dynamodb scan \
  --table-name gold-agent-users \
  --filter-expression "daily_summary = :t" \
  --expression-attribute-values '{":t": {"BOOL": true}}' \
  --region ap-south-1 \
  --query 'Items[*].{phone:phone_number.S,city:city.S,lang:language.S}'

# Check all active price alerts
aws dynamodb scan \
  --table-name gold-agent-alert-preferences \
  --filter-expression "active = :t" \
  --expression-attribute-values '{":t": {"BOOL": true}}' \
  --region ap-south-1 \
  --query 'Items[*].{phone:phone_number.S,metal:metal.S,dir:direction.S,threshold:threshold_inr.N}'
```

---

## Table of Contents

1. [AWS Account & Region](#aws-account--region)
2. [Deployed Lambdas](#deployed-lambdas)
3. [DynamoDB Tables](#dynamodb-tables)
4. [S3 Bucket Structure](#s3-bucket-structure)
5. [CloudWatch Logs](#cloudwatch-logs)
6. [Useful CLI Commands](#useful-cli-commands)
7. [SAM / CloudFormation](#sam--cloudformation)
8. [End-to-End Workflows](#end-to-end-workflows)

---

## AWS Account & Region

| Item | Value |
|---|---|
| Account ID | 077419561931 |
| Region | ap-south-1 (Mumbai) |
| Stack name | gold-agent |
| Execution role (Phase 2) | gold-agent-phase2-role |
| Execution role (Consolidator) | gold-agent-consolidator-role |
| Developer IAM user | gold-agent-dev |
| ECR repository | gold-agent-whisper |
| S3 deployment bucket | resolved automatically via `--resolve-s3` |
| SAM config | samconfig.toml (in repo root) |

---

## Deployed Lambdas

### gold-agent-consolidator

| Property | Value |
|---|---|
| Runtime | python3.12 (zip) |
| Handler | `src/lambdas/consolidator/handler.handler` |
| Memory | 256MB |
| Timeout | 300s |
| Trigger | EventBridge cron — `cron(45 5 * * ? *)` = 11:15AM IST daily |
| Role | gold-agent-consolidator-role |

What it does: runs all 4 scrapers, merges results with anomaly detection and trimmed mean, writes one row per metal to DynamoDB `gold-agent-live-prices`, writes full JSON snapshot to S3.

**Data quality guards (in `dynamo_writer.py`):**
- **Guard 1 — minimum sources:** skips gold write if fewer than 2 spot-price sources responded (single-source consensus is unreliable — `gold_api_com` has returned stale cached $3,100 prices in observed runs).
- **Guard 2 — sanity floor:** skips gold write if the 22K per-gram average from Indian city rates is below ₹8,000. Off-hours RapidAPI data returns ~₹895/gram (stale cache). Real price is ₹14,000+.
- If either guard fires, existing DynamoDB value is preserved and a `[GOLD] SKIPPED` warning is logged.

---

### gold-agent-whatsapp-handler

| Property | Value |
|---|---|
| Runtime | python3.12 (zip) |
| Handler | `src/lambdas/whatsapp_handler/handler.handler` |
| Memory | 256MB |
| Timeout | 30s |
| Trigger | API Gateway — GET /webhook (Meta verification) + POST /webhook (messages) |
| Role | gold-agent-phase2-role |
| Secrets | `gold-agent/whatsapp` → WHATSAPP_VERIFY_TOKEN, WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID |

What it does: validates HMAC-SHA256 signature, parses text and audio messages, detects language, classifies intent, manages session history, invokes agent-brain async. For voice notes: downloads OGG from Meta, uploads to S3 `voice-temp/`, invokes whisper-transcriber async.

---

### gold-agent-brain

| Property | Value |
|---|---|
| Runtime | python3.12 (zip) |
| Handler | `src/lambdas/agent_brain/handler.handler` |
| Memory | 512MB |
| Timeout | 60s |
| Trigger | Async invocation by whatsapp-handler and whisper-transcriber |
| Role | gold-agent-phase2-role |
| Secrets | `gold-agent/anthropic` → ANTHROPIC_API_KEY; `gold-agent/whatsapp` → WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID |

What it does: routes alert_setup/remove/list to `conversation/` handlers, everything else to Claude (Sonnet 4.6) with a structured live price block injected into the system prompt.

---

### gold-agent-alert-checker

| Property | Value |
|---|---|
| Runtime | python3.12 (zip) |
| Handler | `src/lambdas/alert_checker/handler.handler` |
| Memory | 256MB |
| Timeout | 120s |
| Trigger | EventBridge — `rate(1 hour)` |
| Role | gold-agent-phase2-role |
| Secrets | `gold-agent/whatsapp` → WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID |

What it does: scans DynamoDB `gold-agent-alert-preferences` for all active alerts, compares each threshold against `price_22k_inr` from the live-prices table, sends a WhatsApp notification if breached, respects 12-hour cooldown per user per alert.

---

### gold-agent-daily-digest

| Property | Value |
|---|---|
| Runtime | python3.12 (zip) |
| Handler | `src/lambdas/daily_digest/handler.handler` |
| Memory | 256MB |
| Timeout | 300s |
| Trigger | EventBridge cron — `cron(15 6 * * ? *)` = 11:45AM IST daily |
| Role | gold-agent-phase2-role |
| Secrets | `gold-agent/whatsapp` → WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID |

What it does: queries all users with `daily_summary = true`, fetches today's prices from DynamoDB, diffs against yesterday and last week via S3 snapshots, sends a WhatsApp approved template message (`gold_agent_daily_update`, 16 variables) per user. Does **not** invoke the consolidator — reads DynamoDB only.

---

### gold-agent-whisper-transcriber

| Property | Value |
|---|---|
| Runtime | Container image (ECR) |
| Image | `077419561931.dkr.ecr.ap-south-1.amazonaws.com/gold-agent-whisper:latest` |
| Memory | 3008MB (~2 vCPU) |
| Timeout | 120s |
| Trigger | Async invocation by whatsapp-handler |
| Role | gold-agent-phase2-role |

What it does: downloads OGG file from S3 `voice-temp/`, transcribes with Whisper base model (pre-baked in image, no network fetch on cold start), deletes OGG from S3, invokes agent-brain async with transcript. Warm invocations complete in ~16s.

Docker image contents: `public.ecr.aws/lambda/python:3.12` base, CPU-only PyTorch, openai-whisper, imageio-ffmpeg (provides static Linux ffmpeg binary), Whisper base model cached at `/var/task/.whisper_cache`.

---

## DynamoDB Tables

All tables in region ap-south-1.

### gold-agent-live-prices

| Attribute | Type | Role |
|---|---|---|
| `metal` | String | HASH (partition key) |

One row per metal: `gold`, `silver`, `platinum`, `copper`.

Key fields written by consolidator:

| Field | Example | Meaning |
|---|---|---|
| `price_usd` | `3287.60` | Spot price USD/troy oz |
| `price_inr` | `298800` | Spot converted to INR (not shown to users) |
| `price_22k_inr` | `14558` | Indian retail per gram 22K (city average incl. duty + GST) |
| `price_24k_inr` | `15876` | Indian retail per gram 24K |
| `city_rates` | `{"Chennai": 145580, ...}` | Per-city price per 10g in INR |
| `confidence` | `"high"` | `high` / `medium` / `low` based on source agreement |
| `sources_used` | `["gold_api_com", ...]` | Which scrapers contributed |
| `snapshot_date` | `"2026-05-22"` | Date of this row |
| `updated_at` | ISO timestamp | When the row was written |

To read current gold price:
```bash
aws dynamodb get-item \
  --table-name gold-agent-live-prices \
  --key '{"metal": {"S": "gold"}}' \
  --region ap-south-1
```

---

### gold-agent-alert-preferences

| Attribute | Type | Role |
|---|---|---|
| `phone_number` | String | HASH (partition key) |
| `alert_id` | String | RANGE (sort key) |

`alert_id` format: `{phone_number}#{metal}#{direction}` — e.g. `919876543210#gold#below`

Key fields:

| Field | Example |
|---|---|
| `metal` | `"gold"` |
| `direction` | `"below"` or `"above"` |
| `threshold_inr` | `14000` |
| `karat` | `"22K"` |
| `active` | `true` |
| `last_triggered` | ISO timestamp (for 12hr cooldown) |
| `language` | `"en"` / `"hi"` / `"ta"` / `"te"` |
| `city` | `"Hyderabad"` |

To list all alerts for a user:
```bash
aws dynamodb query \
  --table-name gold-agent-alert-preferences \
  --key-condition-expression "phone_number = :p" \
  --expression-attribute-values '{":p": {"S": "919876543210"}}' \
  --region ap-south-1
```

---

### gold-agent-conversation-history

| Attribute | Type | Role |
|---|---|---|
| `phone_number` | String | HASH |
| `timestamp` | String | RANGE |

Stores last 10 turns per user (5 user + 5 assistant). 30-minute timeout — session_manager checks `timestamp` and resets history if the last turn is older than 30 min.

---

### gold-agent-users

| Attribute | Type | Role |
|---|---|---|
| `phone_number` | String | HASH |

Key fields:

| Field | Example |
|---|---|
| `language` | `"hi"` |
| `city` | `"Mumbai"` |
| `daily_summary` | `true` |
| `joined_at` | ISO timestamp |

---

### gold-agent-source-health

| Attribute | Type | Role |
|---|---|---|
| `source_id` | String | HASH |

Tracks circuit breaker state per scraper (`open` / `closed` / `half_open`), consecutive failures, last success timestamp.

---

### gold-agent-quota-tracker

| Attribute | Type | Role |
|---|---|---|
| `source_id` | String | HASH |

Tracks monthly API call counts per source. Prevents exceeding the 100/month limit on metals_dev and goldapi_io.

---

## S3 Bucket Structure

Bucket: **gold-agent-prices** (ap-south-1)

```
gold-agent-prices/
├── prices/
│   ├── latest.json                   ← always the most recent consolidator run (overwritten each run)
│   └── YYYY/MM/DD/
│       └── HH:MM.json                ← full consolidator output per run
│           Example: prices/2026/05/23/11:15.json
│
└── voice-temp/
    └── {message_id}.ogg              ← WhatsApp voice note, deleted after transcription
        Example: voice-temp/wamid.HBg...abc.ogg
        Lifecycle: auto-deleted after 1 day (S3 lifecycle rule on voice-temp/ prefix)
```

### Snapshot JSON structure

```json
{
  "metal": "gold",
  "snapshot_date": "2026-05-22",
  "price_usd": 3287.60,
  "price_inr": 298800,
  "price_22k_inr": 14558,
  "price_24k_inr": 15876,
  "confidence": "high",
  "sources_used": ["gold_api_com", "metals_dev", "goldapi_io", "rapid_api_gold_silver"],
  "city_rates": {
    "Chennai": 145580,
    "Mumbai": 145100,
    "Hyderabad": 144900,
    "...": "71 cities"
  },
  "raw_sources": {
    "gold_api_com": { "price_usd": 3287.60 },
    "metals_dev": { "price_usd": 3286.50, "usd_to_inr": 90.91 },
    "goldapi_io": { "price_usd": 3287.00, "price_gram_22k": 96.89 }
  }
}
```

To list snapshots for today:
```bash
aws s3 ls s3://gold-agent-prices/prices/$(date +%Y/%m/%d)/ --region ap-south-1
```

To read the latest snapshot:
```bash
aws s3 cp s3://gold-agent-prices/prices/latest.json - --region ap-south-1 | python3 -m json.tool
```

To read a specific day's snapshot:
```bash
aws s3 cp s3://gold-agent-prices/prices/2026/05/23/11:15.json - --region ap-south-1 | python3 -m json.tool
```

---

## CloudWatch Logs

All Lambda log groups follow the pattern `/aws/lambda/{function-name}`.

### Log group names

| Lambda | Log Group |
|---|---|
| consolidator | `/aws/lambda/gold-agent-consolidator` |
| whatsapp-handler | `/aws/lambda/gold-agent-whatsapp-handler` |
| agent-brain | `/aws/lambda/gold-agent-brain` |
| alert-checker | `/aws/lambda/gold-agent-alert-checker` |
| daily-digest | `/aws/lambda/gold-agent-daily-digest` |
| whisper-transcriber | `/aws/lambda/gold-agent-whisper-transcriber` |

### Tail live logs

```bash
# Watch whatsapp-handler in real time (useful when testing a message)
aws logs tail /aws/lambda/gold-agent-whatsapp-handler \
  --follow --region ap-south-1

# Watch whisper-transcriber (cold start + transcription)
aws logs tail /aws/lambda/gold-agent-whisper-transcriber \
  --follow --region ap-south-1

# Watch agent-brain (Claude calls, price context, alert writes)
aws logs tail /aws/lambda/gold-agent-brain \
  --follow --region ap-south-1

# Watch all three at once (separate terminals)
aws logs tail /aws/lambda/gold-agent-whatsapp-handler --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-brain --follow --region ap-south-1
aws logs tail /aws/lambda/gold-agent-whisper-transcriber --follow --region ap-south-1
```

### Search recent logs

```bash
# Last 15 minutes of errors across agent-brain
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-brain \
  --filter-pattern "ERROR" \
  --start-time $(date -v-15M +%s000) \
  --region ap-south-1

# Find all voice transcriptions in last hour
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-whisper-transcriber \
  --filter-pattern "Transcription complete" \
  --start-time $(date -v-1H +%s000) \
  --region ap-south-1

# See consolidator run outcome
aws logs filter-log-events \
  --log-group-name /aws/lambda/gold-agent-consolidator \
  --filter-pattern "snapshot" \
  --start-time $(date -v-24H +%s000) \
  --region ap-south-1
```

### Using SAM logs (simpler)

```bash
sam logs -n gold-agent-brain --stack-name gold-agent --region ap-south-1
sam logs -n gold-agent-whatsapp-handler --stack-name gold-agent --region ap-south-1 --tail
sam logs -n gold-agent-whisper-transcriber --stack-name gold-agent --region ap-south-1 --tail
```

---

## Useful CLI Commands

### Manual Lambda invocations

```bash
# Trigger consolidator manually (refreshes DynamoDB + S3)
aws lambda invoke \
  --function-name gold-agent-consolidator \
  --region ap-south-1 \
  --payload '{}' \
  /tmp/consolidator_out.json
cat /tmp/consolidator_out.json

# Invoke agent-brain directly (simulate a user message)
aws lambda invoke \
  --function-name gold-agent-brain \
  --region ap-south-1 \
  --payload '{"phone_number":"919876543210","text":"What is gold price today?","language":"en","city":"Hyderabad","intent":"price_query","history":[]}' \
  /tmp/brain_out.json
cat /tmp/brain_out.json

# Trigger alert-checker manually
aws lambda invoke \
  --function-name gold-agent-alert-checker \
  --region ap-south-1 \
  --payload '{}' \
  /tmp/alert_out.json

# Trigger daily-digest manually
aws lambda invoke \
  --function-name gold-agent-daily-digest \
  --region ap-south-1 \
  --payload '{}' \
  /tmp/digest_out.json
```

### DynamoDB queries

```bash
# Read all live prices (all metals)
aws dynamodb scan \
  --table-name gold-agent-live-prices \
  --region ap-south-1

# Read gold price only
aws dynamodb get-item \
  --table-name gold-agent-live-prices \
  --key '{"metal": {"S": "gold"}}' \
  --region ap-south-1

# List all users with daily summary enabled
aws dynamodb scan \
  --table-name gold-agent-users \
  --filter-expression "daily_summary = :t" \
  --expression-attribute-values '{":t": {"BOOL": true}}' \
  --region ap-south-1

# Check alerts for a specific user
aws dynamodb query \
  --table-name gold-agent-alert-preferences \
  --key-condition-expression "phone_number = :p" \
  --expression-attribute-values '{":p": {"S": "919876543210"}}' \
  --region ap-south-1

# Scan all active alerts
aws dynamodb scan \
  --table-name gold-agent-alert-preferences \
  --filter-expression "active = :t" \
  --expression-attribute-values '{":t": {"BOOL": true}}' \
  --region ap-south-1

# Read conversation history for a user
aws dynamodb query \
  --table-name gold-agent-conversation-history \
  --key-condition-expression "phone_number = :p" \
  --expression-attribute-values '{":p": {"S": "919876543210"}}' \
  --scan-index-forward false \
  --limit 10 \
  --region ap-south-1
```

### S3 operations

```bash
# List today's snapshots
aws s3 ls s3://gold-agent-prices/snapshots/$(date +%Y/%m/%d)/ --region ap-south-1

# Read latest gold snapshot (adjust filename)
aws s3 cp s3://gold-agent-prices/snapshots/2026/05/22/snapshot_gold_20260522T113000.json - \
  --region ap-south-1

# List voice temp files (should be empty if whisper is working)
aws s3 ls s3://gold-agent-prices/voice-temp/ --region ap-south-1
```

### Deployment

```bash
# Standard deploy (zip Lambdas — whatsapp-handler, agent-brain, alert-checker, etc.)
sam build && sam deploy --region ap-south-1 --no-confirm-changeset --resolve-image-repos

# Full deploy including Whisper container rebuild + push + SAM deploy
./deploy_whisper.sh

# Deploy only after Dockerfile change (re-runs docker build + push + sam deploy)
./deploy_whisper.sh

# Check deployed stack status
aws cloudformation describe-stacks \
  --stack-name gold-agent \
  --region ap-south-1 \
  --query 'Stacks[0].StackStatus'

# List all stack resources
aws cloudformation list-stack-resources \
  --stack-name gold-agent \
  --region ap-south-1
```

### Stuck CloudFormation stack

```bash
# If stack is stuck in UPDATE_ROLLBACK_FAILED
aws cloudformation continue-update-rollback \
  --stack-name gold-agent \
  --region ap-south-1 \
  --resources-to-skip WhatsAppHandlerFunction AgentBrainFunction AlertCheckerFunction ConsolidatorFunction DailyDigestFunction
```

### ECR operations

```bash
# Log in to ECR (needed before docker push)
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  077419561931.dkr.ecr.ap-south-1.amazonaws.com

# List images in ECR repo
aws ecr list-images \
  --repository-name gold-agent-whisper \
  --region ap-south-1

# Check ECR repo policy
aws ecr get-repository-policy \
  --repository-name gold-agent-whisper \
  --region ap-south-1
```

### Check Lambda configuration

```bash
# See all env vars, memory, timeout for a function
aws lambda get-function-configuration \
  --function-name gold-agent-brain \
  --region ap-south-1

# See last invocation errors
aws lambda list-event-source-mappings \
  --function-name gold-agent-alert-checker \
  --region ap-south-1
```

---

## SAM / CloudFormation

### Template file: `template.yml` (repo root)

The SAM template defines all 6 deployed Lambdas plus API Gateway.

**Key sections:**

| Section | What it defines |
|---|---|
| `Globals.Function` | Default memory (256MB), timeout (300s), shared env vars (DynamoDB table names, S3 bucket, region) |
| `GoldAgentApi` | API Gateway with StageName `prod` — receives Meta webhooks at `/webhook` |
| `ConsolidatorFunction` | Daily scraper, EventBridge cron |
| `WhatsAppHandlerFunction` | API Gateway GET+POST `/webhook`, 30s timeout, WhatsApp secrets |
| `AgentBrainFunction` | 512MB, 60s, Anthropic + WhatsApp secrets |
| `AlertCheckerFunction` | EventBridge rate(1 hour), WhatsApp secrets |
| `DailyDigestFunction` | EventBridge cron 11:45AM IST, WhatsApp secrets |
| `WhisperTranscriberFunction` | PackageType: Image, 3008MB, 120s, ECR ImageUri |

**Global environment variables** (available in all Lambda functions):

| Variable | Value |
|---|---|
| `S3_BUCKET_NAME` | `gold-agent-prices` |
| `DYNAMO_TABLE_LIVE_PRICES` | `gold-agent-live-prices` |
| `DYNAMO_TABLE_SOURCE_HEALTH` | `gold-agent-source-health` |
| `DYNAMO_TABLE_QUOTA_TRACKER` | `gold-agent-quota-tracker` |
| `DYNAMO_TABLE_USERS` | `gold-agent-users` |
| `DYNAMO_TABLE_ALERT_PREFERENCES` | `gold-agent-alert-preferences` |
| `DYNAMO_TABLE_CONVERSATION_HISTORY` | `gold-agent-conversation-history` |
| `AWS_REGION_NAME` | `ap-south-1` |
| `AGENT_BRAIN_FUNCTION_NAME` | `gold-agent-brain` |

**Important:** `Runtime` is set per-function (not in Globals) because `WhisperTranscriberFunction` uses `PackageType: Image` and cannot have a Runtime attribute. SAM rejects the template if Runtime is in Globals when any image-based function exists.

### Webhook URL

After deploy, the Meta webhook URL is in stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name gold-agent \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text
```

Format: `https://{api-id}.execute-api.ap-south-1.amazonaws.com/prod/webhook`

### Secrets Manager paths

| Secret | Keys inside |
|---|---|
| `gold-agent/whatsapp` | WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN |
| `gold-agent/anthropic` | ANTHROPIC_API_KEY |
| `gold-agent/metals-dev` | METALS_DEV_API_KEY |
| `gold-agent/goldapi-io` | GOLDAPI_IO_KEY |
| `gold-agent/rapidapi` | RAPIDAPI_KEY |

---

## End-to-End Workflows

### 1. WhatsApp Text Message Flow

```
User sends "What is gold price in Hyderabad?"
    ↓
Meta Cloud API validates → POST to API Gateway /webhook (ap-south-1)
    ↓
whatsapp-handler (30s timeout)
  1. Validate X-Hub-Signature-256 HMAC header (reject if wrong)
  2. Parse message — type=text, body="What is gold price in Hyderabad?"
  3. Detect language — English (no Devanagari/Tamil/Telugu script)
  4. Classify intent — regex match → "price_query"
  5. Load session from DynamoDB conversation-history (last 10 turns, check 30-min timeout)
  6. InvokeFunction async → agent-brain (Event invocation, no wait)
  7. Return HTTP 200 to Meta immediately (Meta retries if it gets anything else)
    ↓
agent-brain (60s timeout)
  1. Intent = price_query → general Claude path
  2. context_builder.py: check module-level 1hr cache → if stale, scan gold-agent-live-prices
  3. Build price block: "22K gold per gram (INR): ₹14,558 ... City: Hyderabad: ₹1,44,900 per 10g"
  4. prompt_builder.py: build system prompt with live data + explicit "use ONLY these numbers"
  5. Call Claude Sonnet 4.6 with system prompt + 10-turn conversation history
  6. Claude generates reply in English referencing ₹14,490/gram for Hyderabad
  7. whatsapp_client.send_text() → POST to Meta Graph API → user receives reply
```

---

### 2. Voice Note Flow

```
User sends a voice message (OGG Opus format, WhatsApp compression)
    ↓
Meta Cloud API → POST /webhook with audio object: {"id": "wamid.HBg...", "mime_type": "audio/ogg; codecs=opus"}
    ↓
whatsapp-handler
  1. Parse message — type=audio, media_id="wamid.HBg..."
  2. detect language, classify intent (skipped — goes straight to voice path)
  3. _handle_audio():
     a. whatsapp_client.download_media(media_id):
        - GET https://graph.facebook.com/v19.0/{media_id} → gets {"url": "https://lookaside.fbsbx.com/..."}
        - GET that URL with Bearer {WHATSAPP_TOKEN} → returns raw OGG bytes
     b. Upload bytes to S3: gold-agent-prices/voice-temp/{message_id}.ogg
     c. InvokeFunction async → whisper-transcriber
  4. Return HTTP 200 to Meta
    ↓
whisper-transcriber (3008MB, 120s timeout — container image)
  1. Event: {s3_bucket, s3_key, phone_number, city, language_hint}
  2. Download OGG from S3 to /tmp/{s3_key}
  3. Load Whisper base model from /var/task/.whisper_cache (pre-baked — no network)
     - Warm invocation: ~2s (model already loaded in _model global)
     - Cold start: ~15s (Python import + model load from image filesystem)
  4. model.transcribe(ogg_path, fp16=False) → {"text": "What is the gold price today in Hyderabad?"}
  5. s3.delete_object(Bucket, Key) — OGG deleted immediately
  6. InvokeFunction async → agent-brain with transcript as text
    ↓
agent-brain — same path as text message from here (Claude with price context → WhatsApp reply)
```

**Whisper mishear note:** WhatsApp audio is compressed to 16kHz OGG Opus. "gold price" → "goldfish" is possible with the base model due to audio quality. The Whisper large model would improve accuracy but costs more (9x memory). Base model is a deliberate tradeoff for cost.

---

### 3. Price Consolidation Pipeline (Daily, 11:15AM IST)

```
EventBridge fires cron(45 5 * * ? *) [05:45 UTC = 11:15 IST]
    ↓
consolidator Lambda
  1. Load scraper configs from config/sources.json
  2. Run active scrapers (quota check from DynamoDB quota-tracker first):
     - gold_api_com: GET https://api.gold-api.com/price/XAU → spot USD/troy oz (no auth, unlimited)
     - metals_dev: GET https://api.metals.dev/v1/latest → spot + MCX/IBJA + currencies.INR (100/month)
     - goldapi_io: GET https://www.goldapi.io/api/XAU/USD → spot + karat gram prices (100/month)
     - rapid_api_gold_silver: GET per-city gold + silver rates for 77 locations (550k/month)
  3. merger.py: anomaly detection (validate against metals.json price ranges) → trimmed mean
  4. Average Indian city 22K rates from rapid_api → price_22k_inr
  5. dynamo_writer.py: PutItem on gold-agent-live-prices — one row per metal (overwrite)
  6. s3_writer.py: put_object to snapshots/YYYY/MM/DD/snapshot_{metal}_{ts}.json
```

Key: `price_22k_inr` is what users see. It is NOT a conversion — it is the actual average retail price from 71 Indian cities already including import duty + GST. International spot converted to INR is ~35% lower.

---

### 4. Alert Setup Flow

```
User sends "Alert me when gold drops below ₹14,000"
    ↓
whatsapp-handler → intent = "alert_setup" → agent-brain async
    ↓
agent-brain
  1. intent = alert_setup → conversation/alert_setup.py
  2. Call Claude Haiku (NOT Sonnet — pure JSON extraction, no price data in context)
     Prompt: "Extract {metal, direction, threshold_inr, karat} from this message"
     → {"metal": "gold", "direction": "below", "threshold_inr": 14000, "karat": "22K"}
  3. If extraction fails → send clarification message, return (no write)
  4. dynamo_writer.put_alert():
     - PutItem on gold-agent-alert-preferences
     - phone_number (HASH) + alert_id = "919876543210#gold#below" (RANGE)
     - active = true
  5. After successful write → send confirmation: "Alert set! I'll notify you when 22K gold drops below ₹14,000/gram"
```

Confirmation is only sent AFTER the DynamoDB write succeeds. The system never claims to have set an alert it didn't write.

---

### 5. Alert Check Flow (Hourly)

```
EventBridge fires rate(1 hour)
    ↓
alert-checker Lambda
  1. Scan gold-agent-alert-preferences where active = true
  2. For each alert:
     a. Get metal's price_22k_inr from gold-agent-live-prices
     b. Compare: threshold_checker.check(alert, current_price)
        - direction="below": fire if current_price < threshold_inr
        - direction="above": fire if current_price > threshold_inr
     c. cooldown_manager: check last_triggered — skip if < 12 hours ago
     d. If threshold breached + not in cooldown:
        - alert_formatter.format(alert, current_price, language) → message in user's language
        - whatsapp_client.send_text(phone_number, message)
        - Update last_triggered = now in DynamoDB
```

12-hour cooldown prevents repeated notifications when a price oscillates near the threshold. Without it, a price at ₹14,050 that bounces above/below ₹14,000 every hour would send 24 messages per day.

---

### 6. Daily Digest Flow (11:45AM IST)

```
EventBridge fires cron(15 6 * * ? *) [06:15 UTC = 11:45 IST]
    ↓
daily-digest Lambda
  1. Scan gold-agent-users where daily_summary = true
  2. Fetch today's prices from gold-agent-live-prices
  3. For each user:
     a. Get city from user profile (fallback: national average)
     b. price_diff.py: find yesterday's snapshot in S3 (walks back up to 14 days)
        - S3 key: snapshots/YYYY/MM/DD/snapshot_gold_{ts}.json
        - actual comparison date always shown in message
     c. digest_builder.py: build message with 24K/22K/18K prices, silver, platinum,
        change vs yesterday, change vs last week, "prices last updated: 11:15 AM IST"
     d. whatsapp_client.send_text(phone_number, message)
```

The 30-minute gap (consolidator 11:15, digest 11:45) ensures fresh data is always available before the digest runs.

---

### 7. Alert Setup via Natural Language (Hindi example)

```
User sends "सोना ₹14,000 से नीचे आए तो बताना" (Hindi)
    ↓
whatsapp-handler
  1. Detect language: Devanagari script → Hindi
  2. Classify intent: "alert" keyword present → alert_setup
  3. Invoke agent-brain async
    ↓
agent-brain / alert_setup.py
  1. Haiku extraction prompt: includes the Hindi text
  2. Haiku understands the meaning: metal=gold, direction=below, threshold_inr=14000
  3. DynamoDB write → alert_id = "919876543210#gold#below"
  4. Confirmation sent in Hindi: "ठीक है! जब सोना ₹14,000 से नीचे जाएगा, तब मैं आपको बताऊंगा।"
    ↓
When price drops below ₹14,000:
  alert-checker → alert_formatter.format(language="hi") → Hindi WhatsApp notification
```

---

## IAM Roles and Key Permissions

### gold-agent-phase2-role

Used by: whatsapp-handler, agent-brain, alert-checker, daily-digest, whisper-transcriber

Required permissions:
- `dynamodb:GetItem, PutItem, UpdateItem, Query, Scan` on all gold-agent-* tables
- `s3:GetObject, PutObject, DeleteObject` on `gold-agent-prices/*`
- `lambda:InvokeFunction` on gold-agent-brain, gold-agent-whisper-transcriber
- `secretsmanager:GetSecretValue` on gold-agent/whatsapp, gold-agent/anthropic
- `logs:CreateLogGroup, CreateLogStream, PutLogEvents`
- `ecr:GetDownloadUrlForLayer, BatchGetImage, GetAuthorizationToken` (for whisper-transcriber to pull its own image)

### gold-agent-consolidator-role

Used by: consolidator only

Required permissions:
- `dynamodb:PutItem, UpdateItem` on gold-agent-live-prices, gold-agent-source-health, gold-agent-quota-tracker
- `s3:PutObject` on `gold-agent-prices/snapshots/*`
- `secretsmanager:GetSecretValue` on gold-agent/metals-dev, gold-agent/goldapi-io, gold-agent/rapidapi

### ECR repository policy (gold-agent-whisper)

Lambda service needs pull access. Apply once:
```bash
aws ecr set-repository-policy \
  --repository-name gold-agent-whisper \
  --region ap-south-1 \
  --policy-text '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "LambdaECRImagePull",
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": ["ecr:GetDownloadUrlForLayer","ecr:BatchGetImage","ecr:GetAuthorizationToken"]
    }]
  }'
```

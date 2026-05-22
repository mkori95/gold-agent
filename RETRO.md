# Deployment Retrospective — Issues & Fixes

## Issue 1: Lambda package too large (>262MB unzipped)
**Symptom:** `sam deploy` fails with "Unzipped size must be smaller than 262144000 bytes"
**Root cause:** `infra/terraform/.terraform/` (Terraform provider cache, 692MB) was being bundled into every Lambda package. `.samignore` had `infra/` and `.terraform/` but these patterns only match top-level directories — nested paths like `infra/terraform/.terraform/` are not matched.
**Fix:**
1. Delete the `.terraform` cache (it's a local cache, safe to delete — `terraform init` recreates it):
   ```
   rm -rf infra/terraform/.terraform
   ```
2. Add nested pattern to `.samignore`:
   ```
   **/.terraform/
   infra/terraform/.terraform/
   ```
3. Remove `boto3` from `requirements.txt` — Lambda Python 3.12 runtime provides it, no need to bundle.
4. Clean build cache before rebuilding: `rm -rf .aws-sam && sam build`

---

## Issue 2: API Gateway permission denied during `sam deploy`
**Symptom:** CloudFormation fails with "no identity-based policy allows the apigateway:POST action"
**Root cause:** The IAM user (`gold-agent-dev`) had 10 managed policies attached (the AWS limit) and was missing `AmazonAPIGatewayAdministrator`.
**Fix:** Add an **inline policy** (separate quota from managed policies):
```bash
aws iam put-user-policy \
  --user-name gold-agent-dev \
  --policy-name gold-agent-apigateway \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"apigateway:*","Resource":"*"}]}'
```

---

## Issue 3: Python imports fail for hyphenated Lambda directories
**Symptom:** `ModuleNotFoundError` — Python can't import `src.lambdas.whatsapp-handler`
**Root cause:** Python identifiers can't contain hyphens, so directories like `whatsapp-handler` are not importable.
**Fix:** Create symlinks with underscored names pointing to the hyphenated directories:
```bash
ln -s whatsapp-handler src/lambdas/whatsapp_handler
ln -s agent-brain src/lambdas/agent_brain
ln -s alert-checker src/lambdas/alert_checker
```

---

## Issue 4: Alert setup claimed success without writing to DynamoDB
**Symptom:** Claude confirmed "alert set" but nothing was written to DynamoDB.
**Root cause:** `alert_setup` intent was routed to Claude, which responded conversationally but never triggered any backend write.
**Fix:** Route `alert_setup` to a dedicated handler (`conversation/alert_setup.py`) that: extracts params via Claude JSON extraction → writes to DynamoDB via `put_alert()` → only confirms to user after write succeeds. Claude is never trusted to "handle" a database action.
**Principle:** Claude handles conversation only. Any action that writes to the database must go through a dedicated handler that confirms only after the write succeeds.

---

## Deployment Checklist (Phase 2)
1. Get permanent WhatsApp System User token from Meta Business Manager
2. Store secrets: `aws secretsmanager put-secret-value --secret-id gold-agent/whatsapp ...` and `create-secret` for `gold-agent/anthropic`
3. Create IAM role `gold-agent-phase2-role` (trusted entity: AWS service → Lambda) with `AWSLambdaBasicExecutionRole` + inline policy for DynamoDB/SecretsManager/Lambda invoke
4. Create DynamoDB tables: `gold-agent-users`, `gold-agent-alert-preferences`, `gold-agent-conversation-history`
5. `rm -rf infra/terraform/.terraform && rm -rf .aws-sam && sam build && sam deploy --region ap-south-1 --no-confirm-changeset`
6. Paste `WebhookUrl` output into Meta WhatsApp → Configuration → webhook URL with verify token `goldagent_webhook_2026`
7. Subscribe to: `messages`, `message_deliveries`, `message_reads`

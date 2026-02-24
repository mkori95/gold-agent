#!/bin/bash

# ============================================================
# Gold Agent — Project Structure Setup Script
# Run this once from the root of your gold-agent repo
# ============================================================

echo "🚀 Setting up Gold Agent project structure..."

# Helper function — creates folder and adds .gitkeep
make_dir() {
    mkdir -p "$1"
    touch "$1/.gitkeep"
}

# ============================================================
# .github — CI/CD workflows and issue templates
# ============================================================
make_dir ".github/workflows"
make_dir ".github/ISSUE_TEMPLATE"

touch ".github/workflows/deploy.yml"
touch ".github/workflows/test.yml"
touch ".github/workflows/lint.yml"
touch ".github/ISSUE_TEMPLATE/bug_report.md"
touch ".github/ISSUE_TEMPLATE/feature_request.md"

echo "✅ .github/ done"

# ============================================================
# docs — all documentation
# ============================================================
make_dir "docs/architecture/diagrams"
make_dir "docs/api"
make_dir "docs/runbooks"
make_dir "docs/phases"

touch "docs/architecture/overview.md"
touch "docs/architecture/data-flow.md"
touch "docs/architecture/aws-services.md"
touch "docs/architecture/phase-plan.md"
touch "docs/api/endpoints.md"
touch "docs/api/whatsapp-webhooks.md"
touch "docs/runbooks/scraper-failure.md"
touch "docs/runbooks/api-quota-exceeded.md"
touch "docs/runbooks/circuit-breaker-tripped.md"
touch "docs/runbooks/deployment.md"
touch "docs/phases/phase-1-engine.md"
touch "docs/phases/phase-2-product.md"
touch "docs/phases/phase-3-community.md"
touch "docs/phases/phase-4-business.md"

echo "✅ docs/ done"

# ============================================================
# infra — AWS infrastructure as code (SAM)
# ============================================================
make_dir "infra/vpc"
make_dir "infra/lambda"
make_dir "infra/s3"
make_dir "infra/dynamodb"
make_dir "infra/eventbridge"
make_dir "infra/api-gateway"
make_dir "infra/cloudwatch"
make_dir "infra/sns"
make_dir "infra/ses"
make_dir "infra/secrets"
make_dir "infra/iam"

touch "infra/template.yaml"
touch "infra/vpc/vpc.yaml"
touch "infra/lambda/functions.yaml"
touch "infra/s3/buckets.yaml"
touch "infra/dynamodb/tables.yaml"
touch "infra/eventbridge/rules.yaml"
touch "infra/api-gateway/api.yaml"
touch "infra/cloudwatch/alarms.yaml"
touch "infra/cloudwatch/dashboard.yaml"
touch "infra/sns/topics.yaml"
touch "infra/ses/email-templates.yaml"
touch "infra/secrets/secrets.yaml"
touch "infra/iam/roles.yaml"

echo "✅ infra/ done"

# ============================================================
# src/lambdas — all Lambda functions
# ============================================================

# --- scraper (Phase 1) ---
make_dir "src/lambdas/scraper"
touch "src/lambdas/scraper/handler.py"
touch "src/lambdas/scraper/scheduler.py"
touch "src/lambdas/scraper/circuit_breaker.py"
touch "src/lambdas/scraper/quota_manager.py"
touch "src/lambdas/scraper/health_tracker.py"
touch "src/lambdas/scraper/source_selector.py"
touch "src/lambdas/scraper/parallel_runner.py"
touch "src/lambdas/scraper/notifier.py"
touch "src/lambdas/scraper/README.md"

# --- consolidator (Phase 1) ---
make_dir "src/lambdas/consolidator"
touch "src/lambdas/consolidator/handler.py"
touch "src/lambdas/consolidator/merger.py"
touch "src/lambdas/consolidator/validator.py"
touch "src/lambdas/consolidator/anomaly_detector.py"
touch "src/lambdas/consolidator/trimmed_mean.py"
touch "src/lambdas/consolidator/s3_writer.py"
touch "src/lambdas/consolidator/dynamo_writer.py"
touch "src/lambdas/consolidator/README.md"

# --- agent-brain (Phase 2) ---
make_dir "src/lambdas/agent-brain"
touch "src/lambdas/agent-brain/handler.py"
touch "src/lambdas/agent-brain/context_builder.py"
touch "src/lambdas/agent-brain/claude_client.py"
touch "src/lambdas/agent-brain/prompt_builder.py"
touch "src/lambdas/agent-brain/language_handler.py"
touch "src/lambdas/agent-brain/market_analyser.py"
touch "src/lambdas/agent-brain/trend_detector.py"
touch "src/lambdas/agent-brain/summary_writer.py"
touch "src/lambdas/agent-brain/README.md"

# --- whatsapp-handler (Phase 2) ---
make_dir "src/lambdas/whatsapp-handler"
touch "src/lambdas/whatsapp-handler/handler.py"
touch "src/lambdas/whatsapp-handler/signature_validator.py"
touch "src/lambdas/whatsapp-handler/message_parser.py"
touch "src/lambdas/whatsapp-handler/language_detector.py"
touch "src/lambdas/whatsapp-handler/intent_classifier.py"
touch "src/lambdas/whatsapp-handler/user_manager.py"
touch "src/lambdas/whatsapp-handler/session_manager.py"
touch "src/lambdas/whatsapp-handler/response_formatter.py"
touch "src/lambdas/whatsapp-handler/response_sender.py"
touch "src/lambdas/whatsapp-handler/template_sender.py"
touch "src/lambdas/whatsapp-handler/window_checker.py"
touch "src/lambdas/whatsapp-handler/README.md"

# --- conversation (Phase 2) ---
make_dir "src/lambdas/conversation"
touch "src/lambdas/conversation/handler.py"
touch "src/lambdas/conversation/price_query.py"
touch "src/lambdas/conversation/calculator.py"
touch "src/lambdas/conversation/alert_setup.py"
touch "src/lambdas/conversation/education.py"
touch "src/lambdas/conversation/festival_advisor.py"
touch "src/lambdas/conversation/trend_explainer.py"
touch "src/lambdas/conversation/comparison.py"
touch "src/lambdas/conversation/README.md"

# --- alert-checker (Phase 2) ---
make_dir "src/lambdas/alert-checker"
touch "src/lambdas/alert-checker/handler.py"
touch "src/lambdas/alert-checker/threshold_checker.py"
touch "src/lambdas/alert-checker/alert_trigger.py"
touch "src/lambdas/alert-checker/alert_formatter.py"
touch "src/lambdas/alert-checker/cooldown_manager.py"
touch "src/lambdas/alert-checker/README.md"

# --- weekly-digest (Phase 2) ---
make_dir "src/lambdas/weekly-digest"
touch "src/lambdas/weekly-digest/handler.py"
touch "src/lambdas/weekly-digest/data_fetcher.py"
touch "src/lambdas/weekly-digest/digest_builder.py"
touch "src/lambdas/weekly-digest/digest_formatter.py"
touch "src/lambdas/weekly-digest/subscriber_fetcher.py"
touch "src/lambdas/weekly-digest/bulk_sender.py"
touch "src/lambdas/weekly-digest/README.md"

# --- festival-advisory (Phase 2) ---
make_dir "src/lambdas/festival-advisory"
touch "src/lambdas/festival-advisory/handler.py"
touch "src/lambdas/festival-advisory/calendar_reader.py"
touch "src/lambdas/festival-advisory/advisory_builder.py"
touch "src/lambdas/festival-advisory/advisory_formatter.py"
touch "src/lambdas/festival-advisory/subscriber_fetcher.py"
touch "src/lambdas/festival-advisory/bulk_sender.py"
touch "src/lambdas/festival-advisory/README.md"

# --- rate-validator (Phase 3) ---
make_dir "src/lambdas/rate-validator"
touch "src/lambdas/rate-validator/handler.py"
touch "src/lambdas/rate-validator/guardrail_1_minimum.py"
touch "src/lambdas/rate-validator/guardrail_2_spread.py"
touch "src/lambdas/rate-validator/guardrail_3_market_anchor.py"
touch "src/lambdas/rate-validator/guardrail_4_time_decay.py"
touch "src/lambdas/rate-validator/guardrail_5_reputation.py"
touch "src/lambdas/rate-validator/guardrail_6_unique_users.py"
touch "src/lambdas/rate-validator/trimmed_mean.py"
touch "src/lambdas/rate-validator/confidence_scorer.py"
touch "src/lambdas/rate-validator/reputation_updater.py"
touch "src/lambdas/rate-validator/summary_writer.py"
touch "src/lambdas/rate-validator/README.md"

# --- location (Phase 3) ---
make_dir "src/lambdas/location"
touch "src/lambdas/location/handler.py"
touch "src/lambdas/location/coordinates_parser.py"
touch "src/lambdas/location/places_client.py"
touch "src/lambdas/location/jeweller_finder.py"
touch "src/lambdas/location/jeweller_formatter.py"
touch "src/lambdas/location/rate_prioritiser.py"
touch "src/lambdas/location/README.md"

# --- gamification (Phase 3) ---
make_dir "src/lambdas/gamification"
touch "src/lambdas/gamification/handler.py"
touch "src/lambdas/gamification/badge_engine.py"
touch "src/lambdas/gamification/badge_definitions.py"
touch "src/lambdas/gamification/streak_tracker.py"
touch "src/lambdas/gamification/leaderboard.py"
touch "src/lambdas/gamification/milestone_checker.py"
touch "src/lambdas/gamification/celebration_sender.py"
touch "src/lambdas/gamification/README.md"

# --- report (Phase 4) ---
make_dir "src/lambdas/report"
touch "src/lambdas/report/handler.py"
touch "src/lambdas/report/data_fetcher.py"
touch "src/lambdas/report/report_builder.py"
touch "src/lambdas/report/pdf_generator.py"
touch "src/lambdas/report/s3_uploader.py"
touch "src/lambdas/report/email_sender.py"
touch "src/lambdas/report/README.md"

# --- data-api (Phase 4) ---
make_dir "src/lambdas/data-api"
touch "src/lambdas/data-api/handler.py"
touch "src/lambdas/data-api/live_prices.py"
touch "src/lambdas/data-api/historical_prices.py"
touch "src/lambdas/data-api/city_rates.py"
touch "src/lambdas/data-api/response_builder.py"
touch "src/lambdas/data-api/README.md"

# --- web-chat (Phase 4) ---
make_dir "src/lambdas/web-chat"
touch "src/lambdas/web-chat/handler.py"
touch "src/lambdas/web-chat/session_manager.py"
touch "src/lambdas/web-chat/context_builder.py"
touch "src/lambdas/web-chat/claude_client.py"
touch "src/lambdas/web-chat/README.md"

echo "✅ src/lambdas/ done"

# ============================================================
# src/scrapers — scraping engine and site scrapers
# ============================================================
make_dir "src/scrapers/engine"
make_dir "src/scrapers/sites"

touch "src/scrapers/engine/base_scraper.py"
touch "src/scrapers/engine/api_fetcher.py"
touch "src/scrapers/engine/html_scraper.py"
touch "src/scrapers/engine/response_parser.py"
touch "src/scrapers/engine/data_normaliser.py"
touch "src/scrapers/engine/rate_limiter.py"

touch "src/scrapers/sites/goldapi_io.py"
touch "src/scrapers/sites/gold_api_com.py"
touch "src/scrapers/sites/free_gold_api.py"
touch "src/scrapers/sites/yahoo_finance.py"
touch "src/scrapers/sites/ibja.py"
touch "src/scrapers/sites/kitco.py"
touch "src/scrapers/sites/moneycontrol.py"
touch "src/scrapers/sites/goodreturns.py"
touch "src/scrapers/sites/rapaport.py"

echo "✅ src/scrapers/ done"

# ============================================================
# src/shared — shared utilities across all lambdas
# ============================================================
make_dir "src/shared/db"
make_dir "src/shared/models"
make_dir "src/shared/notifications"
make_dir "src/shared/utils"

touch "src/shared/db/dynamo_client.py"
touch "src/shared/db/dynamo_reader.py"
touch "src/shared/db/dynamo_writer.py"
touch "src/shared/db/s3_client.py"
touch "src/shared/db/s3_reader.py"
touch "src/shared/db/s3_writer.py"

touch "src/shared/models/price.py"
touch "src/shared/models/source.py"
touch "src/shared/models/user.py"
touch "src/shared/models/alert.py"
touch "src/shared/models/jeweller.py"
touch "src/shared/models/community_rate.py"
touch "src/shared/models/badge.py"

touch "src/shared/notifications/sns_client.py"
touch "src/shared/notifications/ses_client.py"
touch "src/shared/notifications/whatsapp_client.py"
touch "src/shared/notifications/notification_formatter.py"

touch "src/shared/utils/logger.py"
touch "src/shared/utils/date_helper.py"
touch "src/shared/utils/currency_formatter.py"
touch "src/shared/utils/metal_helper.py"
touch "src/shared/utils/config_loader.py"
touch "src/shared/utils/error_handler.py"

echo "✅ src/shared/ done"

# ============================================================
# src/frontend — React Dashboard (Phase 4)
# ============================================================
make_dir "src/frontend/public"
make_dir "src/frontend/src/pages"
make_dir "src/frontend/src/components"
make_dir "src/frontend/src/services"
make_dir "src/frontend/src/utils"

touch "src/frontend/src/pages/Dashboard.jsx"
touch "src/frontend/src/pages/Charts.jsx"
touch "src/frontend/src/pages/CityRates.jsx"
touch "src/frontend/src/pages/FestivalGuide.jsx"
touch "src/frontend/src/pages/Chat.jsx"

touch "src/frontend/src/components/PriceCard.jsx"
touch "src/frontend/src/components/SourceBadge.jsx"
touch "src/frontend/src/components/PriceChart.jsx"
touch "src/frontend/src/components/CityMap.jsx"
touch "src/frontend/src/components/AlertBanner.jsx"
touch "src/frontend/src/components/ChatWindow.jsx"
touch "src/frontend/src/components/LanguageSwitcher.jsx"

touch "src/frontend/src/services/api.js"
touch "src/frontend/src/services/websocket.js"
touch "src/frontend/src/services/auth.js"

touch "src/frontend/src/utils/formatters.js"
touch "src/frontend/src/utils/constants.js"

touch "src/frontend/package.json"

echo "✅ src/frontend/ done"

# ============================================================
# config — all JSON config files
# ============================================================
make_dir "config"

touch "config/sources.json"
touch "config/festivals.json"
touch "config/metals.json"
touch "config/cities.json"
touch "config/alerts.json"
touch "config/badges.json"
touch "config/languages.json"

echo "✅ config/ done"

# ============================================================
# tests — unit, integration, fixtures
# ============================================================
make_dir "tests/unit/scrapers"
make_dir "tests/unit/lambdas"
make_dir "tests/unit/shared"
make_dir "tests/integration"
make_dir "tests/fixtures"

touch "tests/unit/scrapers/test_api_fetcher.py"
touch "tests/unit/scrapers/test_html_scraper.py"
touch "tests/unit/scrapers/test_data_normaliser.py"

touch "tests/unit/lambdas/test_scraper_handler.py"
touch "tests/unit/lambdas/test_consolidator.py"
touch "tests/unit/lambdas/test_circuit_breaker.py"
touch "tests/unit/lambdas/test_quota_manager.py"
touch "tests/unit/lambdas/test_anomaly_detector.py"
touch "tests/unit/lambdas/test_trimmed_mean.py"

touch "tests/unit/shared/test_dynamo_reader.py"
touch "tests/unit/shared/test_s3_writer.py"
touch "tests/unit/shared/test_currency_formatter.py"

touch "tests/integration/test_scraper_to_s3.py"
touch "tests/integration/test_consolidator_flow.py"
touch "tests/integration/test_circuit_breaker_flow.py"

touch "tests/fixtures/mock_goldapi_response.json"
touch "tests/fixtures/mock_kitco_html.html"
touch "tests/fixtures/mock_dynamo_tables.json"

echo "✅ tests/ done"

# ============================================================
# scripts — setup, deploy, maintenance
# ============================================================
make_dir "scripts/setup"
make_dir "scripts/deploy"
make_dir "scripts/maintenance"
make_dir "scripts/seed"

touch "scripts/setup/setup_local.sh"
touch "scripts/setup/setup_aws.sh"
touch "scripts/setup/create_secrets.sh"

touch "scripts/deploy/deploy_infra.sh"
touch "scripts/deploy/deploy_lambdas.sh"
touch "scripts/deploy/deploy_frontend.sh"

touch "scripts/maintenance/check_source_health.sh"
touch "scripts/maintenance/reset_quota.sh"
touch "scripts/maintenance/enable_source.sh"

touch "scripts/seed/seed_test_data.py"

echo "✅ scripts/ done"

# ============================================================
# Root level files (skip ones GitHub already created)
# ============================================================
touch ".env.example"
touch ".pylintrc"
touch "CONTRIBUTING.md"
touch "CHANGELOG.md"
touch "requirements.txt"

echo "✅ Root files done"

# ============================================================
# Done
# ============================================================
echo ""
echo "🎉 Project structure created successfully!"
echo ""
echo "Next step: Copy CONTEXT.md into this folder, then run:"
echo "  git add ."
echo "  git commit -m 'Initial project structure'"
echo "  git push"
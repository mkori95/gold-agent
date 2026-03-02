# CONTEXT.md — Gold Agent Project
### Read This First Before Every New Chat Session

---

## ⚠️ How To Use This File

1. At the start of every new Claude chat session — paste this entire file first
2. Tell Claude: "Continue building the Gold Agent project based on this context"
3. At the end of every session — ask Claude to update this file with what changed
4. Save the updated version back to this file in the repo

---

## 🎯 What We Are Building

A **WhatsApp-first precious metals and gems advisor for Indian families** — specifically targeting Indian housewives and everyday gold buyers who currently have no simple, trustworthy, vernacular source of gold price information and buying advice.

### The One Line Product Vision
> "A personal gold buying advisor that lives in WhatsApp — tells you the right time to buy gold, silver and platinum — in your language, for your city, before every festival."

### Why This Exists
- Indian housewives check gold prices by calling their jeweller (conflict of interest) or asking their husband
- No app or service serves this audience in Hindi, Tamil or Telugu
- WhatsApp is already on every phone — no download needed
- General AI (ChatGPT, Claude, Gemini) cannot do proactive alerts, persistent memory, or city-specific Indian rates reliably
- The India-specific angle (IBJA rates, city-wise INR, MCX, festival calendar) is our strongest differentiator

---

## 📦 Metals and Gems Covered

- **Gold** — USD spot + INR city rates (22K, 24K)
- **Silver** — USD spot + INR rates
- **Platinum** — USD spot + INR rates
- **Copper** — USD spot (festival context — vessels, idols)
- **Diamond** — Skipped for now. Rapaport is paywalled. Will revisit in Phase 2.

---

## 🌍 Languages Supported at Launch

- Hindi
- Tamil
- Telugu

Language is auto-detected from user's message. User never has to select.

---

## 💰 Commercial Model

Keeping free for now. Future phases:
- Jeweller partnership program (Priority 1 rate display)
- Digital gold referrals (SafeGold, Augmont)
- Premium subscription
- API access for businesses

---

## 🏗️ Architecture Overview

### Deployment
- Fully serverless on AWS
- No EC2 — everything is Lambda
- GitHub repository (open source, monorepo)

### Primary Product
- WhatsApp Business API (Meta Cloud API)
- Users save a phone number and chat naturally
- No app download, no account creation required
- Phone number = identity (OTP for alerts)

### Secondary Product (Phase 4)
- React web dashboard on S3 + CloudFront
- Same data, more visual
- Available in Hindi, Tamil, Telugu, English

---

## ☁️ Complete AWS Services List

| Service | Purpose |
|---|---|
| Route 53 | DNS — custom domain |
| ACM | Free SSL certificate |
| CloudFront | CDN — delivers web dashboard fast |
| WAF | Firewall — protects API from abuse |
| VPC + Subnets | Private network for Lambdas |
| NAT Gateway | Lets Lambdas reach internet for scraping |
| VPC Endpoints | Private path to S3 and DynamoDB |
| API Gateway | Receives WhatsApp webhooks + web API calls |
| Lambda (x13+) | All business logic |
| EventBridge | Scheduling — hourly, weekly, festival |
| S3 | Prices, analysis, festivals, reports, app files |
| DynamoDB | Users, live prices, alerts, conversations, quotas |
| Athena | Historical SQL queries on S3 data |
| Secrets Manager | All API keys and credentials |
| IAM | Permissions for every Lambda |
| SES | Email alerts and weekly reports |
| SNS | Internal system alerts to developer |
| CloudWatch | Logs, alarms, system health dashboard |
| X-Ray | Request tracing and debugging |

---

## 🗄️ Storage Strategy

### S3 (long term memory + archive)
```
/prices/gold/YYYY/MM/DD/HH:MM.json
/prices/silver/YYYY/MM/DD/HH:MM.json
/prices/platinum/YYYY/MM/DD/HH:MM.json
/analysis/YYYY/MM/DD/summary_hindi.txt
/analysis/YYYY/MM/DD/summary_tamil.txt
/analysis/YYYY/MM/DD/summary_telugu.txt
/festivals/calendar.json
/reports/weekly/
/community/
/app/  ← React frontend files
```

### DynamoDB Tables
| Table | Purpose |
|---|---|
| live_prices | Latest consensus price per metal — what users see |
| source_health | Health status of every data source |
| quota_tracker | API usage counts per source per month |
| users | User profiles — phone, language, city, joined |
| alert_preferences | User price threshold alerts |
| conversation_history | Last 10 messages per user |
| community_rates | Individual jeweller rate reports |
| jeweller_community_summary | Validated community rate per jeweller |
| user_reputation | Reporter trust scores for gamification |
| jeweller_partners | Phase 4 — paid partner jewellers |
| gamification_badges | Phase 3 — badge awards per user |

### live_prices DynamoDB record structure
```
consensus_price_usd    ← the trimmed mean result
consensus_price_inr    ← converted using Metals.Dev INR rate
confidence_level       ← "high" / "medium" / "low" / "unavailable"
sources_used           ← list of source_ids that contributed
sources_count          ← number of sources
source_prices          ← all individual raw prices preserved
spread_percent         ← how far apart the sources were
karats                 ← 24K, 22K, 18K prices in USD and INR
city_rates             ← per gram INR per city from GoodReturns
extra                  ← mcx_gold, ibja_gold, lbma prices etc
timestamp              ← when calculated
```

### Athena
Sits on top of S3 /prices/ folder. Used for historical queries and dashboard charts.

---

## 📊 Data Sources — FINAL ACTIVE LIST

> ⚠️ These are the ONLY active sources. yahoo_finance.py, ibja.py, kitco.py, moneycontrol.py, rapaport.py were removed or skipped.

### Active Sources (in build order)
| # | Source ID | File | Metals | Limit | Status |
|---|---|---|---|---|---|
| 1 | gold_api_com | gold_api_com.py | Gold, Silver, Platinum, Copper | Unlimited | ✅ Built & tested |
| 2 | metals_dev | metals_dev.py | Gold, Silver, Platinum, Copper | 100/month | ✅ Built & tested |
| 3 | goldapi_io | goldapi_io.py | Gold, Silver, Platinum | 100/month | ✅ Built & tested |
| 4 | free_gold_api | free_gold_api.py | Gold (historical) | Unlimited | ❌ Disabled permanently |
| 5 | goodreturns | goodreturns.py | Gold (city-wise INR) | Unlimited | ✅ Built & tested |
| 6 | moneycontrol | — | MCX backup | Unlimited | ⏭️ Skipped — MCX already in Metals.Dev |
| 7 | rapaport | — | Diamond index | Unlimited | ⏭️ Skipped — paywalled |

### Why Sources Were Skipped
- **moneycontrol** — MCX gold/silver data is already captured in `metals_dev.py` extra{} fields. Duplicate data, scraping risk not worth it.
- **rapaport** — Actual price list is behind a paid subscription. No public HTML to scrape. Diamond data deferred to Phase 2.
- **free_gold_api** — Returns full dataset from 1258 AD — no date filtering supported. Disabled permanently.

### Current Metal Coverage
| Metal | Sources |
|---|---|
| Gold | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ goodreturns ✅ |
| Silver | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Platinum | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Copper | gold_api_com ✅ metals_dev ✅ |
| Diamond | ❌ skipped for now |

### Phase 4 Paid Sources (future — not building yet)
| Source | Cost | Why |
|---|---|---|
| Metals-API.com | $4.99/month | City-wise Indian prices — replaces GoodReturns scraper |
| IBJA Official API | Contact for pricing | RBI approved benchmark — most authoritative India source |

---

## ⚙️ Source Configuration System

Single `config/sources.json` file controls everything:
- `type` — api / scraper
- `priority` — 1 / 2 / 3
- `enabled` — true / false
- `health_status` — healthy / warning / disabled
- `rate_limit` — requests per month + strategy
- `schedule` — frequency in minutes + active hours + timezone
- `failure_handling` — retry count + auto recovery + fallback source
- `metals` — which metals this source covers
- `fields_map` — maps our standard field names to API-specific field names

### Adding New Sources
Edit sources.json only — no code changes needed.

---

## 🧠 ALL BUSINESS LOGIC — FINALISED DECISIONS

### 1. Data Collection Logic

- Every source runs **independently on its own schedule** — they don't wait for each other
- **Collect from ALL sources always** — priority does not mean skipping lower priority sources
- **Sources run in parallel** — not sequentially — makes the pipeline faster
- One source failing never affects any other source

---

### 2. Circuit Breaker Logic

```
Failure 1  →  Log warning, retry in 15 minutes
Failure 2  →  Email alert to developer, retry in 15 minutes
Failure 3  →  Disable source completely — SNS + Email immediately
           →  Auto recovery attempt every 60 minutes
           →  If recovers → re-enable + notify ✅
           →  If still broken → stay disabled + notify again ❌
```

Stored in DynamoDB `source_health` table — `consecutive_failures` field increments on each failure.

---

### 3. Quota Management Logic

For rate-limited sources (GoldAPI.io, Metals.Dev — 100 calls/month):

```
Usage 0–79%    →  Run normally
Usage 80–94%   →  Send warning to developer
Usage 95–99%   →  Switch to fallback source defined in sources.json
Usage 100%     →  Disable for rest of month, fallback only
Day 1 of month →  Auto-reset quota counter
```

Stored in DynamoDB `quota_tracker` table.

---

### 4. Price Consensus Logic (Trimmed Mean)

**Step by step:**
```
Step 1  →  Collect all prices for a metal from all active sources
Step 2  →  Run anomaly detection — reject any price outside metals.json range
Step 3  →  Sort prices lowest to highest
Step 4  →  Drop the single highest and single lowest (trim outliers)
Step 5  →  Average the remaining prices
Step 6  →  That average = consensus price
```

**Source count rules:**
```
4+ sources  →  Trim + average            →  confidence: "high"
3 sources   →  Median (middle value)     →  confidence: "high"
2 sources   →  Simple average            →  confidence: "medium"
1 source    →  Use as-is, flag clearly   →  confidence: "low"
0 sources   →  No data — alert developer →  confidence: "unavailable"
```

**Phase 1 — equal weights for all sources.** Reputation weighting added in Phase 2 once we have real accuracy data to measure against.

**Anomaly detection** — before including any price in the calculation:
- Check against `price_range_usd` in metals.json
- If price is outside range → reject that data point for this run + log warning
- Example: gold at $500 or $50,000 → rejected immediately

**Spread monitoring** — after calculating consensus:
- Calculate `spread_percent` = (max - min) / consensus × 100
- Large spread signals something unusual is happening
- Log it — may alert developer if spread exceeds threshold

**GoodReturns is NOT included in trimmed mean** — it gives per gram INR retail rates, not troy ounce spot prices. It feeds directly into `city_rates{}` on the snapshot only.

---

### 5. INR Conversion Logic

```
Source provides INR directly (GoodReturns)  →  Use as-is — no conversion
Source provides USD only (all API sources)  →  Convert using exchange rate
Exchange rate source                        →  Metals.Dev only (single source of truth)
Exchange rate field                         →  currencies.INR from Metals.Dev response
Exchange rate formula                       →  usd_to_inr = 1 / currencies.INR
Exchange rate storage                       →  scraper.inr_rate on MetalsDevScraper
                                               → passed to DataNormaliser by consolidator
```

INR conversion happens in the **consolidator via DataNormaliser** — never in individual scrapers.
Exception: GoodReturns scraper returns `price_inr` directly because that's all it has.

---

### 6. Consolidator Output — Final Snapshot Structure

```json
{
  "snapshot_id": "2026-03-02T16:00:00+00:00",
  "consolidated_at": "2026-03-02T16:00:00+00:00",
  "inr_rate": 0.01099,
  "usd_to_inr": 90.99,
  "metals": {
    "gold": {
      "price_usd": 5213.00,
      "price_inr": 473878.0,
      "unit": "troy_ounce",
      "confidence": "high",
      "sources_used": ["gold_api_com", "metals_dev", "goldapi_io"],
      "sources_count": 3,
      "source_prices": {
        "gold_api_com": 5210.50,
        "metals_dev": 5215.00,
        "goldapi_io": 5213.50
      },
      "spread_percent": 0.09,
      "karats": {
        "24K": { "price_usd": 5212.49, "price_inr": 473771.0 },
        "22K": { "price_usd": 4778.78, "price_inr": 434407.0 },
        "18K": { "price_usd": 3910.25, "price_inr": 355583.0 }
      },
      "city_rates": {
        "mumbai":    { "24K": 9780.0, "22K": 8950.0, "18K": 7340.0 },
        "delhi":     { "24K": 9760.0, "22K": 8930.0, "18K": 7320.0 },
        "chennai":   { "24K": 9790.0, "22K": 8960.0, "18K": 7350.0 }
      },
      "extra": {
        "mcx_gold": 5464.365,
        "ibja_gold": 5401.8482,
        "lbma_gold_am": 5174.75,
        "lbma_gold_pm": 5167.35
      }
    },
    "silver": { },
    "platinum": { },
    "copper": { }
  }
}
```

---

### 7. Consolidator Testing Approach

- Written as a **standalone Python class** first — testable locally like all scrapers
- Thin Lambda wrapper added at the end (5 lines)
- No Docker, no SAM, no LocalStack needed for Phase 1
- Run locally: `python src/lambdas/consolidator/consolidator.py`

---

### 8. Jeweller Rate Priority Logic

The ONLY place where source priority affects what the user sees:

```
User asks about a specific jeweller
         ↓
Is there a verified PARTNER rate?     → Show it  ✅  Phase 4
         ↓ No
Is there a valid COMMUNITY rate?      → Show it with confidence level  ✅  Phase 3
         ↓ No
Fall back to MARKET rate + education  → Explain what to expect  ✅  Phase 2
```

---

### 9. Community Rate Validation Logic

A rate must pass ALL 6 guardrails — fail any one → rate not shown:

```
Guardrail 1  →  Minimum 3 unique phone numbers reported
Guardrail 2  →  Spread between all reports must be < 2%
Guardrail 3  →  Rate must be within ±5% of official market rate
Guardrail 4  →  All reports must be less than 24 hours old
Guardrail 5  →  Weight by reporter reputation score
Guardrail 6  →  One report per phone number per jeweller
```

Calculation: trimmed mean with reputation weights — same trimmed mean concept as price consensus.

---

### 10. Community Rate Confidence Logic

```
3+ reports AND spread < 0.5%   →  ⭐⭐⭐ High confidence — show to user
3–5 reports AND spread < 1%    →  ⭐⭐ Medium confidence — show to user
Anything else                  →  Don't show — fall back to market rate
```

---

### 11. User Reputation Logic

Every user who submits jeweller rates has a hidden score (0–100):

```
Starting score     →  50 (neutral — new, unknown reporter)
Accurate report    →  Score increases
Outlier report     →  Score decreases
Consistent reports →  Score grows over time
```

Accuracy measured by comparing reporter's submission to final community consensus after calculation.
Close to consensus = accurate. Far from consensus = outlier.

---

### 12. Alert Logic

```
User sets price threshold  →  e.g. "Tell me when gold hits ₹55,000"
Alert checker runs         →  Every hour via EventBridge
Threshold breached         →  Send WhatsApp message immediately
Cooldown                   →  4 hours before alerting same user again
                              (prevents spam if price fluctuates near threshold)
```

---

### 13. Festival Advisory Logic

```
EventBridge checks festival calendar  →  Daily
7 days before any festival            →  Trigger advisory Lambda
Advisory Lambda fetches               →  Current price + trend + historical context
Sends proactive WhatsApp to           →  All opted-in users in relevant region
Language                              →  User's saved preference (Hindi/Tamil/Telugu)
```

---

### 14. Language Detection Logic

```
First message from user     →  Auto-detect language
Save to DynamoDB            →  All future messages in same language
User can override           →  "Switch to Hindi" / "Hindi mein bolo"
Default if detection fails  →  English
```

---

### 15. WhatsApp 24-Hour Window Logic

```
User messages us            →  24-hour window opens
Within 24 hours             →  Reply freely in any format
After 24 hours of silence   →  Can only send pre-approved templates
Alert or digest needed      →  Check window first
  Window open               →  Send as regular message
  Window closed             →  Send as approved template
```

---

## 💬 WhatsApp — Meta Cloud API

### Key Rules
- First 1,000 user-initiated conversations/month → FREE
- 24-hour window rule — after 24hr silence, can only send approved templates
- 7 templates needed upfront — submitted once, approved in 24-48hrs
- Quality rating must stay GREEN — no spam, always add value
- Dedicated phone number needed (virtual number ok)
- Tier 1 = 1,000 unique users/day — grows automatically

### Templates Needed
1. welcome_message
2. price_alert
3. weekly_digest
4. festival_advisory
5. daily_morning_rate
6. price_drop_alert
7. price_rise_alert

---

## 🏪 Jeweller Rate System — 3 Solutions Combined

### Priority Logic (for jeweller rate queries only)
```
PRIORITY 1 — Partner Rate (Solution 2)
→ Verified rate from paying jeweller partner

PRIORITY 2 — Community Rate (Solution 3)
→ Crowdsourced from users
→ Show WITH market rate alongside

PRIORITY 3 — Market Rate + Education (Solution 1)
→ Show official market rate for city
→ Educate on what to expect at jeweller
→ Ask user to report rate when they visit
```

---

## 🎮 Gamification (Phase 3)

| Badge | Trigger |
|---|---|
| 🌟 First Timer | Sent first message |
| 🥇 Gold Reporter | First rate report submitted |
| ⭐ Trusted Voice | 5 accurate rate reports |
| 💎 Community Star | 20 accurate reports |
| 🏆 Gold Sakhi Expert | 50 accurate reports |
| 🎯 Streak Master | 4 weeks consistent engagement |
| 🙏 Festival Hero | Reported rate during festival season |

---

## 🗺️ Phase Plan

### Phase 1 — The Engine (Months 1-2) ← WE ARE HERE
**Goal:** Fully automated data pipeline. No user-facing product yet.

Status: All scrapers complete. Building consolidator next.

### Phase 2 — The Product (Months 2-3)
WhatsApp chatbot with real users.

### Phase 3 — The Community (Months 3-4)
Crowdsourced jeweller rates, location, gamification.

### Phase 4 — The Business (Months 5-6)
Revenue, web dashboard, scale.

---

## 📁 Correct Project Folder Structure

```
gold-agent/
├── config/
│   ├── alerts.json
│   ├── badges.json
│   ├── cities.json                         (empty — placeholder, tidy up later)
│   ├── festivals.json
│   ├── languages.json
│   ├── metals.json                         ✅ finalised
│   └── sources.json                        ✅ finalised
├── docs/
│   ├── api/
│   │   ├── endpoints.md
│   │   └── whatsapp-webhooks.md
│   ├── architecture/
│   │   ├── aws-services.md
│   │   ├── data-flow.md
│   │   ├── diagrams/
│   │   ├── overview.md
│   │   └── phase-plan.md
│   ├── phases/
│   │   ├── phase-1-engine.md
│   │   ├── phase-2-product.md
│   │   ├── phase-3-community.md
│   │   └── phase-4-business.md
│   └── runbooks/
│       ├── api-quota-exceeded.md
│       ├── circuit-breaker-tripped.md
│       ├── deployment.md
│       └── scraper-failure.md
├── infra/
│   ├── api-gateway/api.yaml
│   ├── cloudwatch/
│   │   ├── alarms.yaml
│   │   └── dashboard.yaml
│   ├── dynamodb/tables.yaml
│   ├── eventbridge/rules.yaml
│   ├── iam/roles.yaml
│   ├── lambda/functions.yaml
│   ├── s3/buckets.yaml
│   ├── secrets/secrets.yaml
│   ├── ses/email-templates.yaml
│   ├── sns/topics.yaml
│   ├── template.yaml
│   └── vpc/vpc.yaml
├── scripts/
│   ├── deploy/
│   │   ├── deploy_frontend.sh
│   │   ├── deploy_infra.sh
│   │   └── deploy_lambdas.sh
│   ├── maintenance/
│   │   ├── check_source_health.sh
│   │   ├── enable_source.sh
│   │   └── reset_quota.sh
│   ├── seed/
│   │   └── seed_test_data.py
│   └── setup/
│       ├── create_secrets.sh
│       ├── setup_aws.sh
│       └── setup_local.sh
├── src/
│   ├── __init__.py
│   ├── frontend/                           ← Phase 4
│   │   ├── package.json
│   │   ├── public/
│   │   └── src/
│   │       ├── components/
│   │       │   ├── AlertBanner.jsx
│   │       │   ├── ChatWindow.jsx
│   │       │   ├── CityMap.jsx
│   │       │   ├── LanguageSwitcher.jsx
│   │       │   ├── PriceCard.jsx
│   │       │   ├── PriceChart.jsx
│   │       │   └── SourceBadge.jsx
│   │       ├── pages/
│   │       │   ├── Charts.jsx
│   │       │   ├── Chat.jsx
│   │       │   ├── CityRates.jsx
│   │       │   ├── Dashboard.jsx
│   │       │   └── FestivalGuide.jsx
│   │       ├── services/
│   │       │   ├── api.js
│   │       │   ├── auth.js
│   │       │   └── websocket.js
│   │       └── utils/
│   │           ├── constants.js
│   │           └── formatters.js
│   ├── lambdas/
│   │   ├── agent-brain/                    ← Phase 2
│   │   │   ├── claude_client.py
│   │   │   ├── context_builder.py
│   │   │   ├── handler.py
│   │   │   ├── language_handler.py
│   │   │   ├── market_analyser.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── summary_writer.py
│   │   │   └── trend_detector.py
│   │   ├── alert-checker/                  ← Phase 2
│   │   │   ├── alert_formatter.py
│   │   │   ├── alert_trigger.py
│   │   │   ├── cooldown_manager.py
│   │   │   ├── handler.py
│   │   │   └── threshold_checker.py
│   │   ├── consolidator/                   ← BUILD NEXT (Phase 1)
│   │   │   ├── anomaly_detector.py
│   │   │   ├── dynamo_writer.py
│   │   │   ├── handler.py
│   │   │   ├── merger.py
│   │   │   ├── s3_writer.py
│   │   │   ├── trimmed_mean.py
│   │   │   └── validator.py
│   │   ├── conversation/                   ← Phase 2
│   │   │   ├── alert_setup.py
│   │   │   ├── calculator.py
│   │   │   ├── comparison.py
│   │   │   ├── education.py
│   │   │   ├── festival_advisor.py
│   │   │   ├── handler.py
│   │   │   ├── price_query.py
│   │   │   └── trend_explainer.py
│   │   ├── data-api/                       ← Phase 2
│   │   │   ├── city_rates.py
│   │   │   ├── handler.py
│   │   │   ├── historical_prices.py
│   │   │   ├── live_prices.py
│   │   │   └── response_builder.py
│   │   ├── festival-advisory/              ← Phase 2
│   │   │   ├── advisory_builder.py
│   │   │   ├── advisory_formatter.py
│   │   │   ├── bulk_sender.py
│   │   │   ├── calendar_reader.py
│   │   │   ├── handler.py
│   │   │   └── subscriber_fetcher.py
│   │   ├── gamification/                   ← Phase 3
│   │   │   ├── badge_definitions.py
│   │   │   ├── badge_engine.py
│   │   │   ├── celebration_sender.py
│   │   │   ├── handler.py
│   │   │   ├── leaderboard.py
│   │   │   ├── milestone_checker.py
│   │   │   └── streak_tracker.py
│   │   ├── location/                       ← Phase 3
│   │   │   ├── coordinates_parser.py
│   │   │   ├── handler.py
│   │   │   ├── jeweller_finder.py
│   │   │   ├── jeweller_formatter.py
│   │   │   ├── places_client.py
│   │   │   └── rate_prioritiser.py
│   │   ├── rate-validator/                 ← Phase 3
│   │   │   ├── confidence_scorer.py
│   │   │   ├── guardrail_1_minimum.py
│   │   │   ├── guardrail_2_spread.py
│   │   │   ├── guardrail_3_market_anchor.py
│   │   │   ├── guardrail_4_time_decay.py
│   │   │   ├── guardrail_5_reputation.py
│   │   │   ├── guardrail_6_unique_users.py
│   │   │   ├── handler.py
│   │   │   ├── reputation_updater.py
│   │   │   ├── summary_writer.py
│   │   │   └── trimmed_mean.py
│   │   ├── report/                         ← Phase 4
│   │   │   ├── data_fetcher.py
│   │   │   ├── email_sender.py
│   │   │   ├── handler.py
│   │   │   ├── pdf_generator.py
│   │   │   ├── report_builder.py
│   │   │   └── s3_uploader.py
│   │   ├── scraper/                        ← Phase 1
│   │   │   ├── circuit_breaker.py
│   │   │   ├── handler.py
│   │   │   ├── health_tracker.py
│   │   │   ├── notifier.py
│   │   │   ├── parallel_runner.py
│   │   │   ├── quota_manager.py
│   │   │   ├── scheduler.py
│   │   │   └── source_selector.py
│   │   ├── web-chat/                       ← Phase 4
│   │   │   ├── claude_client.py
│   │   │   ├── context_builder.py
│   │   │   ├── handler.py
│   │   │   └── session_manager.py
│   │   ├── weekly-digest/                  ← Phase 2
│   │   │   ├── bulk_sender.py
│   │   │   ├── data_fetcher.py
│   │   │   ├── digest_builder.py
│   │   │   ├── digest_formatter.py
│   │   │   ├── handler.py
│   │   │   └── subscriber_fetcher.py
│   │   └── whatsapp-handler/               ← Phase 2
│   │       ├── handler.py
│   │       ├── intent_classifier.py
│   │       ├── language_detector.py
│   │       ├── message_parser.py
│   │       ├── response_formatter.py
│   │       ├── response_sender.py
│   │       ├── session_manager.py
│   │       ├── signature_validator.py
│   │       ├── template_sender.py
│   │       ├── user_manager.py
│   │       └── window_checker.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── api_fetcher.py              ✅ built
│   │   │   ├── base_scraper.py             ✅ built
│   │   │   ├── data_normaliser.py          ✅ built
│   │   │   ├── html_scraper.py             ✅ built — curl_cffi Cloudflare bypass
│   │   │   ├── rate_limiter.py             (empty placeholder)
│   │   │   └── response_parser.py          (empty placeholder)
│   │   └── sites/
│   │       ├── __init__.py
│   │       ├── free_gold_api.py            ❌ disabled permanently
│   │       ├── gold_api_com.py             ✅ built and tested
│   │       ├── goldapi_io.py               ✅ built and tested
│   │       ├── goodreturns.py              ✅ built and tested
│   │       ├── metals_dev.py               ✅ built and tested
│   │       ├── moneycontrol.py             ⏭️ skipped — MCX covered by Metals.Dev
│   │       └── rapaport.py                 ⏭️ skipped — paywalled
│   └── shared/
│       ├── db/
│       │   ├── dynamo_client.py
│       │   ├── dynamo_reader.py
│       │   ├── dynamo_writer.py
│       │   ├── s3_client.py
│       │   ├── s3_reader.py
│       │   └── s3_writer.py
│       ├── models/
│       │   ├── alert.py
│       │   ├── badge.py
│       │   ├── community_rate.py
│       │   ├── jeweller.py
│       │   ├── price.py
│       │   ├── source.py
│       │   └── user.py
│       ├── notifications/
│       │   ├── notification_formatter.py
│       │   ├── ses_client.py
│       │   ├── sns_client.py
│       │   └── whatsapp_client.py
│       └── utils/
│           ├── config_loader.py
│           ├── currency_formatter.py
│           ├── date_helper.py
│           ├── error_handler.py
│           ├── logger.py
│           └── metal_helper.py
├── tests/
│   ├── fixtures/
│   │   ├── mock_dynamo_tables.json
│   │   ├── mock_goldapi_response.json
│   │   └── mock_kitco_html.html
│   ├── integration/
│   │   ├── test_circuit_breaker_flow.py
│   │   ├── test_consolidator_flow.py
│   │   └── test_scraper_to_s3.py
│   └── unit/
│       ├── lambdas/
│       │   ├── test_anomaly_detector.py
│       │   ├── test_circuit_breaker.py
│       │   ├── test_consolidator.py
│       │   ├── test_quota_manager.py
│       │   ├── test_scraper_handler.py
│       │   └── test_trimmed_mean.py
│       ├── scrapers/
│       │   ├── test_api_fetcher.py
│       │   ├── test_data_normaliser.py
│       │   ├── test_gold_api_com.py        ✅ passing
│       │   ├── test_goldapi_io.py          ✅ passing
│       │   ├── test_goodreturns.py         ✅ passing
│       │   ├── test_html_scraper.py
│       │   └── test_metals_dev.py          ✅ passing
│       └── shared/
│           ├── test_currency_formatter.py
│           ├── test_dynamo_reader.py
│           └── test_s3_writer.py
├── .env
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── CONTEXT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── requirements.txt                        ✅ curl_cffi==0.7.4 added
├── setup.py
└── setup_structure.sh
```
---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 (Mac) |
| AI Brain | Anthropic Claude API (claude-sonnet-4-6) |
| Infrastructure | AWS SAM |
| Primary Channel | Meta WhatsApp Business Cloud API |
| Scraping | curl_cffi + BeautifulSoup |
| Frontend | React (Phase 4) |
| Package Manager | pip + venv |
| Version Control | GitHub (SSH keys) |
| Region | ap-south-1 (Mumbai) |

---

## 💻 Local Dev Setup

```bash
# Always activate venv first
source venv/bin/activate

# Always run scripts from project root
python src/lambdas/consolidator/consolidator.py

# Never run from inside src/ or tests/ folders
```

### Python Package Setup (already done — do not redo)
- `setup.py` exists at project root
- `pip install -e .` already run
- All `__init__.py` files exist in src/, src/scrapers/, src/scrapers/engine/, src/scrapers/sites/
- Import pattern: `from src.scrapers.engine.base_scraper import BaseScraper`
- File path pattern: always use relative paths from project root e.g. `open("config/sources.json")`

---

## 🔑 Environment Variables

All API keys are in `.env` at project root. Every file loads this automatically.

```
METALS_DEV_API_KEY=...
GOLDAPI_IO_KEY=...
GOLD_API_COM_KEY=...    (not needed — no auth)
```

Phase 2+:
```
ANTHROPIC_API_KEY=...
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_ID=...
GOOGLE_PLACES_KEY=...
```

---

## 📐 Code Patterns — Follow These in Every File

### 1. Every file starts with
```python
from dotenv import load_dotenv
load_dotenv()
```
This is the FIRST import in every file. Non-negotiable.

### 2. Every scraper inherits from BaseScraper
```python
class MySourceScraper(BaseScraper):
    def __init__(self, source_config: dict):
        super().__init__(source_config)
        self.fetcher = APIFetcher(source_config)  # for API sources
        self.scraper = HTMLScraper(source_config) # for HTML scrapers

    def fetch(self) -> list:
        # implement this — return list of price records
```

### 3. Standard price record format (from build_price_record)
```json
{
    "metal": "gold",
    "price_usd": 5226.19,
    "currency": "USD",
    "price_inr": null,
    "unit": "troy_ounce",
    "source_id": "goldapi_io",
    "source_name": "GoldAPI.io",
    "timestamp": "2026-02-27T10:00:00Z",
    "extra": {}
}
```

### 4. price_inr is always null from API scrapers
INR conversion happens in consolidator via DataNormaliser — NOT in individual scrapers.
Exception: GoodReturns returns `price_inr` directly, `price_usd` = null.

### 5. One metal/city failure never stops others
Always wrap per-metal or per-city logic in try/except and continue on failure.

### 6. HTML scraper uses curl_cffi — not requests
`html_scraper.py` uses `from curl_cffi import requests` with `impersonate="chrome120"`.
Never revert to standard `requests` — Indian finance sites are heavily Cloudflare-protected.

### 7. Test files for HTML scrapers use subclass to limit cities
```python
class SampleGoodReturnsScraper(GoodReturnsScraper):
    CITIES = ["mumbai", "chennai", "hyderabad", "delhi", "bangalore"]
```

### 8. Test file structure
- TEST 1 — Load sources.json
- TEST 2 — Find source config block
- TEST 3 — Check API key (if applicable)
- TEST 4 — Initialise scraper
- TEST 5 — Run scraper (live call)
- TEST 6 — Check all metals/cities returned
- TEST 7+ — Source-specific validations
- Final TEST — Print full JSON output

---

## 🔍 What Each Built Scraper Does

### gold_api_com.py
- No auth — unlimited calls
- 4 metals: gold, silver, platinum, copper
- Symbols: XAU, XAG, XPT, HG
- One API call per metal (4 calls total per run)

### metals_dev.py
- Auth: query param — `?api_key=KEY`
- 4 metals: gold, silver, platinum, copper — ONE API call for all
- **INR exchange rate** stored in `scraper.inr_rate` — used by consolidator
- INR rate formula: `currencies.INR = 0.011` → `1 USD = 1/0.011 = ₹91`
- Copper: per pound in API → converted to troy ounce (`price_per_toz = price_per_lb / 0.0685714`)
- Gold extra{}: mcx_gold, mcx_gold_am, mcx_gold_pm, ibja_gold, lbma_gold_am, lbma_gold_pm
- Silver extra{}: mcx_silver, mcx_silver_am, mcx_silver_pm, lbma_silver
- Platinum extra{}: lbma_platinum_am, lbma_platinum_pm

### goldapi_io.py
- Auth: header — `x-access-token: KEY`
- 3 metals: gold, silver, platinum (NO copper)
- One API call per metal (3 calls total)
- **Unique: karat-wise gram prices** — no other source gives this
- Standard karats (24K, 22K, 18K) → `extra.karats{}`
- Extended karats (21K, 20K, 16K, 14K, 10K) → `extra.extended_karats{}`
- Market data: ask, bid, change, change_percent, prev_close, open, high, low

### goodreturns.py
- No auth — unlimited HTML scraping via curl_cffi (Cloudflare bypass)
- Gold only — 28 cities — one HTTP request per city
- 5 second polite delay between cities
- URL: `https://www.goodreturns.in/gold-rates/{city}.html`
- `price_usd` = None, `price_inr` = 22K price, `unit` = "gram"
- `extra.karat_prices{}` = 24K, 22K, 18K per gram INR
- Price sanity: > ₹1,000 and < ₹1,00,000 per gram

#### All 28 GoodReturns Cities
```
mumbai, delhi, chennai, hyderabad, bangalore, kolkata,
ahmedabad, pune, jaipur, lucknow, kerala, coimbatore,
madurai, visakhapatnam, vijayawada, surat, nagpur, nashik,
chandigarh, bhubaneswar, patna, vadodara, rajkot, mangalore,
mysore, salem, trichy, ayodhya
```

---

## 🌐 html_scraper.py — Cloudflare Bypass

### Problem
GoodReturns.in is behind Cloudflare Bot Management. Standard `requests` sends a Python TLS fingerprint — blocked with 403.

### Solution
`curl_cffi` with `impersonate="chrome120"` — mimics Chrome's exact TLS handshake. Cloudflare passes it through.

### Changes
- `from curl_cffi import requests` (was `import requests`)
- `impersonate="chrome120"` added to `requests.get()`
- Added `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User` headers
- `curl_cffi==0.7.4` added to `requirements.txt`

---

## 📌 Key Decisions Log

| Decision | What We Chose | Why |
|---|---|---|
| Deployment | AWS Serverless Lambda | Cost effective, scales, no idle cost |
| Database | DynamoDB + S3 + Athena | No RDS needed, fully serverless |
| Primary channel | WhatsApp | 500M+ Indian users, no app needed |
| Languages | Hindi, Tamil, Telugu | Largest underserved vernacular markets |
| Repo type | Monorepo | One developer, simpler to manage |
| Infra as code | AWS SAM | Version controlled, reproducible |
| Scraping approach | API-first, scrape as fallback | APIs more reliable, less maintenance |
| Source management | Config-driven (sources.json) | Add sources without code changes |
| Failure handling | Circuit breaker pattern | Self-healing, auto-notify on failure |
| Price consensus | Trimmed mean | Drops outliers — more robust than simple average |
| Source weighting | Equal weights Phase 1 | Add reputation weighting in Phase 2 with real data |
| Confidence levels | high/medium/low/unavailable | Agent brain knows how much to trust the price |
| INR conversion | Metals.Dev only | Single source of truth for exchange rate |
| Commercial model | Free first, partnerships later | Build users before monetising |
| Code philosophy | One file one responsibility | Readable, testable, maintainable |
| Moneycontrol | Skipped | MCX data already in Metals.Dev extra{} — duplicate |
| Rapaport | Skipped | Paywalled — no public data to scrape |
| Diamond data | Deferred to Phase 2 | Core product is gold/silver for Indian families |
| Copper | Covered by gold_api_com + metals_dev | No new scraper needed |
| cities.json | Keep empty for now | City data lives in goodreturns.py CITIES + sources.json |
| Consolidator testing | Standalone script + thin Lambda wrapper | No Docker needed — same pattern as scrapers |
| HTML scraper library | curl_cffi instead of requests | Bypasses Cloudflare TLS fingerprinting |
| GoodReturns unit | "gram" not "troy_ounce" | Retail per-gram city rates — not spot |
| GoodReturns in consensus | Excluded from trimmed mean | Different unit and price type — goes to city_rates{} only |
| Raw source prices | Always stored in snapshot | Never throw data away — source_prices{} preserved |
| Spread monitoring | Calculated and stored | Large spread = signal of unusual market activity |
| Alert cooldown | 4 hours | Prevents spam when price fluctuates near threshold |
| Festival advisory | 7 days before | Enough lead time for users to plan purchases |

---

## 🧑‍💻 Developer Info

- Name: Manikanta
- OS: Mac
- Python: 3.12
- Python level: Intermediate
- AWS: IAM user created under wife's root account
- AWS Region: ap-south-1 (Mumbai)
- GitHub: Account exists, SSH keys configured
- VS Code: Installed, configured to use venv

---

## 📍 Current Status

**Phase:** Phase 1 — Building the consolidator

**Scrapers — ALL COMPLETE:**
- ✅ gold_api_com.py — built, tested
- ✅ metals_dev.py — built, tested
- ✅ goldapi_io.py — built, tested
- ✅ goodreturns.py — built, tested (28 cities, Cloudflare bypass)
- ❌ free_gold_api.py — disabled permanently
- ⏭️ moneycontrol.py — skipped (MCX covered by Metals.Dev)
- ⏭️ rapaport.py — skipped (paywalled)

**Engine — COMPLETE:**
- ✅ base_scraper.py
- ✅ api_fetcher.py
- ✅ html_scraper.py — curl_cffi Cloudflare bypass
- ✅ data_normaliser.py

**Next Immediate Task:**
Build `src/lambdas/consolidator/consolidator.py`
- Standalone Python class
- Runs all scrapers
- Extracts INR rate from Metals.Dev
- Applies trimmed mean per metal
- Builds final snapshot with city_rates, karats, extra fields
- Thin Lambda wrapper at the end

**After consolidator:**
- `test_consolidator.py` — run it locally
- Wire consolidator to EventBridge schedule
- Move to Phase 2 — WhatsApp bot

---

*Last updated: Session 8 — All business logic decisions documented. Moneycontrol and Rapaport skipped (reasons documented). Copper confirmed covered. Consolidator design finalised. Ready to build consolidator.py next.*
*Update this file at the end of every working session.*
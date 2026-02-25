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
- **Diamond** — Rapaport index only + 4C education (no single price — positioned as buying guide)

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
/prices/diamond/YYYY/MM/DD/index.json
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
| live_prices | Latest price per source per metal per city |
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

### Athena
Sits on top of S3 /prices/ folder. Used for historical queries and dashboard charts.

---

## 📊 Data Sources

### Priority 1 — Free APIs (always prefer)
| Source | Metals | Limit |
|---|---|---|
| GoldAPI.io | Gold, Silver, Platinum | 100/month |
| Gold-API.com | Gold, Silver | Unlimited |
| FreeGoldAPI.com | Gold (historical) | Unlimited |
| Yahoo Finance (GC=F) | Gold Futures | Unlimited |
| IBJA API | Gold, Silver India | Unlimited |

### Priority 2 — Paid APIs
Empty for now — placeholder exists in config

### Priority 3 — Scrapers (last resort)
| Source | Metals | Notes |
|---|---|---|
| Kitco.com | Gold, Silver, Platinum | USD spot |
| Moneycontrol | Gold, Silver | MCX India rates |
| GoodReturns.in | Gold | City-wise INR rates |
| Rapaport | Diamond | Index only |

### Key Rule
All sources run on their own schedule independently. Priority only applies to jeweller rate recommendations — NOT to data collection. We collect from everywhere always.

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

### Adding New Sources
Edit sources.json only — no code changes needed.

---

## 🔄 Circuit Breaker Pattern

Every source has automatic failure handling:

```
Fail 1 → consecutive_failures = 1 → warning → retry in 15 min
Fail 2 → consecutive_failures = 2 → warning → retry in 15 min
Fail 3 → consecutive_failures = 3 → CIRCUIT BREAKER TRIPS
       → health_status = disabled
       → enabled = false in DynamoDB
       → SNS + SES notification sent to developer
       → Auto recovery attempt after 60 minutes
       → If recovered → re-enable + notify ✅
       → If still broken → stay disabled + notify again ❌
```

### Notification Severity Levels
- ⚠️ WARNING (1 failure) — CloudWatch log only
- 🔶 ALERT (2 failures) — Email via SES
- 🔴 CRITICAL (3 failures) — Email + SNS immediately
- ✅ RECOVERY — Email "source is back"
- 🚨 MIN SOURCES BREACHED — Email + SNS urgently

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
→ Show cleanly with ✅ Partner Verified badge

↓ NOT AVAILABLE

PRIORITY 2 — Community Rate (Solution 3)
→ Crowdsourced from users
→ Show WITH market rate alongside
→ Give user choices of what to do next

↓ NOT AVAILABLE

PRIORITY 3 — Market Rate + Education (Solution 1)
→ Show official market rate for city
→ Educate on what to expect at jeweller
→ Ask user to report rate when they visit
→ This converts to Solution 3 data over time
```

### Community Rate Guardrails (6 rules)
1. **Minimum 3 unique users** — don't show until 3 different phone numbers confirm
2. **Spread check** — spread % must be < 2% (percentage based not absolute)
3. **Market anchor** — reject if outside ±5% of official market rate
4. **Time decay** — reports expire after 24 hours
5. **Reputation weighting** — proven reporters get more weight
6. **Unique phone per report** — one report per person per jeweller

### Rate Calculation
Trimmed mean — drop highest and lowest, average the rest. Weighted by reporter reputation score.

### Confidence Levels
- ⭐⭐⭐ High — 3+ reports, spread < 0.5%
- ⭐⭐ Medium — 3-5 reports, spread < 1%
- ⭐ Low — don't show

---

## 🎮 Gamification

Active from Phase 3. Badges awarded via WhatsApp message.

### Badges
| Badge | Trigger |
|---|---|
| 🌟 First Timer | Sent first message |
| 🥇 Gold Reporter | First rate report submitted |
| ⭐ Trusted Voice | 5 accurate rate reports |
| 💎 Community Star | 20 accurate reports |
| 🏆 Gold Sakhi Expert | 50 accurate reports |
| 🎯 Streak Master | 4 weeks consistent engagement |
| 🙏 Festival Hero | Reported rate during festival season |

### Leaderboard
City-wise top reporters. Shown on request.

---

## 🗓️ Festival Calendar

Agent proactively messages users 7 days before each festival:
- Akshaya Tritiya (most important gold buying day)
- Dhanteras
- Dussehra
- Gudi Padwa
- Ugadi
- Pongal
- Onam
- Navratri
- Regional wedding seasons (Feb-May and Oct-Nov peak)

---

## 🤖 Conversation Types Handled

| Type | Example | Available |
|---|---|---|
| Price query | "Aaj gold ka bhav?" | Phase 2 |
| Calculator | "₹50,000 mein kitna gold?" | Phase 2 |
| Alert setup | "₹55,000 pe batao" | Phase 2 |
| Metal education | "22K vs 24K kya fark?" | Phase 2 |
| Trend question | "Kya price badhega?" | Phase 2 |
| Festival advice | "Akshaya Tritiya pe kharidun?" | Phase 2 |
| City comparison | "Mumbai ya Chennai mein sasta?" | Phase 2 |
| Location query | "Mere paas jewellers?" | Phase 3 |
| Rate reporting | "GRT mein ₹57,400 hai" | Phase 3 |
| Partner rate | "Verified jeweller rate" | Phase 4 |

---

## 📱 Location Intelligence (Phase 3)

- User shares WhatsApp location (native feature)
- We receive lat/long coordinates
- Google Places API finds nearby jewellers
- Returns name, distance, rating, opening hours
- Rate prioritiser applies Priority 1/2/3 logic per jeweller

---

## 🗺️ Phase Plan

### Phase 1 — The Engine (Months 1-2)
**Goal:** Fully automated data pipeline. No user-facing product yet.

What we build:
- sources.json config system
- Scraper Lambda (all sources, all metals)
- Consolidator Lambda (merge, validate, anomaly detect)
- Circuit breaker and health tracking
- S3 storage structure (all folders created)
- DynamoDB tables (all tables created, most empty)
- EventBridge hourly trigger
- CloudWatch monitoring and alarms
- SNS/SES failure notifications
- Full AWS infrastructure via SAM
- GitHub repo with complete folder structure and placeholders

Success criteria:
- Data collected every hour without failure
- All 3 metals covered
- 5 Indian cities covered
- Anomalies flagged correctly
- Zero errors in CloudWatch for 48 hours

### Phase 2 — The Product (Months 2-3)
**Goal:** Working WhatsApp chatbot with real users.

What we build:
- Meta WhatsApp Business API setup
- WhatsApp Handler Lambda
- Conversation Lambda (all conversation types)
- Agent Brain Lambda (Claude integration, multilingual)
- Alert Checker Lambda
- Weekly Digest Lambda
- Festival Advisory Lambda
- User management (auto-create on first message)
- Language detection and preference saving
- Basic gamification (welcome badge, streak counter)

Success criteria:
- Bot responds in < 10 seconds
- All 3 languages working
- 10 real test users for 1 week
- Zero wrong price information

### Phase 3 — The Community (Months 3-4)
**Goal:** Crowdsourced jeweller rates, location, gamification.

What we build:
- Location Lambda (Google Places API)
- Rate Validation Lambda (all 6 guardrails)
- Gamification Lambda (full badge system)
- Reputation scoring system
- Community rate priority logic fully active
- Leaderboard system

Success criteria:
- Location sharing working
- Community rates showing with confidence levels
- All 6 guardrails catching bad data
- Badges being awarded
- 100+ active users contributing

### Phase 4 — The Business (Months 5-6)
**Goal:** Revenue, web dashboard, scale.

What we build:
- Jeweller partnership program + dashboard
- React web dashboard (5 pages)
- Referral program
- Digital gold partnerships (SafeGold, Augmont)
- Report Lambda (weekly PDF)
- Data API Lambda (for dashboard)
- Web Chat Lambda

Success criteria:
- 10+ paying jeweller partners
- Web dashboard live
- 1000+ active WhatsApp users
- Revenue covering operational costs

---

## 📁 Complete Project Folder Structure

```
gold-agent/
├── .github/
│   ├── workflows/
│   │   ├── deploy.yml
│   │   ├── test.yml
│   │   └── lint.yml
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── docs/
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── data-flow.md
│   │   ├── aws-services.md
│   │   ├── phase-plan.md
│   │   └── diagrams/
│   ├── api/
│   │   ├── endpoints.md
│   │   └── whatsapp-webhooks.md
│   ├── runbooks/
│   │   ├── scraper-failure.md
│   │   ├── api-quota-exceeded.md
│   │   ├── circuit-breaker-tripped.md
│   │   └── deployment.md
│   └── phases/
│       ├── phase-1-engine.md
│       ├── phase-2-product.md
│       ├── phase-3-community.md
│       └── phase-4-business.md
├── infra/
│   ├── template.yaml
│   ├── vpc/vpc.yaml
│   ├── lambda/functions.yaml
│   ├── s3/buckets.yaml
│   ├── dynamodb/tables.yaml
│   ├── eventbridge/rules.yaml
│   ├── api-gateway/api.yaml
│   ├── cloudwatch/
│   │   ├── alarms.yaml
│   │   └── dashboard.yaml
│   ├── sns/topics.yaml
│   ├── ses/email-templates.yaml
│   ├── secrets/secrets.yaml
│   └── iam/roles.yaml
├── src/
│   ├── lambdas/
│   │   ├── scraper/
│   │   │   ├── handler.py
│   │   │   ├── scheduler.py
│   │   │   ├── circuit_breaker.py
│   │   │   ├── quota_manager.py
│   │   │   ├── health_tracker.py
│   │   │   ├── source_selector.py
│   │   │   ├── parallel_runner.py
│   │   │   ├── notifier.py
│   │   │   └── README.md
│   │   ├── consolidator/
│   │   │   ├── handler.py
│   │   │   ├── merger.py
│   │   │   ├── validator.py
│   │   │   ├── anomaly_detector.py
│   │   │   ├── trimmed_mean.py
│   │   │   ├── s3_writer.py
│   │   │   ├── dynamo_writer.py
│   │   │   └── README.md
│   │   ├── agent-brain/           ← Phase 2
│   │   ├── whatsapp-handler/      ← Phase 2
│   │   ├── conversation/          ← Phase 2
│   │   ├── alert-checker/         ← Phase 2
│   │   ├── weekly-digest/         ← Phase 2
│   │   ├── festival-advisory/     ← Phase 2
│   │   ├── rate-validator/        ← Phase 3
│   │   ├── location/              ← Phase 3
│   │   ├── gamification/          ← Phase 3
│   │   ├── report/                ← Phase 4
│   │   ├── data-api/              ← Phase 4
│   │   └── web-chat/              ← Phase 4
│   ├── scrapers/
│   │   ├── engine/
│   │   │   ├── base_scraper.py
│   │   │   ├── api_fetcher.py
│   │   │   ├── html_scraper.py
│   │   │   ├── response_parser.py
│   │   │   ├── data_normaliser.py
│   │   │   └── rate_limiter.py
│   │   └── sites/
│   │       ├── goldapi_io.py
│   │       ├── gold_api_com.py
│   │       ├── free_gold_api.py
│   │       ├── yahoo_finance.py
│   │       ├── ibja.py
│   │       ├── kitco.py
│   │       ├── moneycontrol.py
│   │       ├── goodreturns.py
│   │       └── rapaport.py
│   ├── shared/
│   │   ├── db/
│   │   │   ├── dynamo_client.py
│   │   │   ├── dynamo_reader.py
│   │   │   ├── dynamo_writer.py
│   │   │   ├── s3_client.py
│   │   │   ├── s3_reader.py
│   │   │   └── s3_writer.py
│   │   ├── models/
│   │   │   ├── price.py
│   │   │   ├── source.py
│   │   │   ├── user.py
│   │   │   ├── alert.py
│   │   │   ├── jeweller.py
│   │   │   ├── community_rate.py
│   │   │   └── badge.py
│   │   ├── notifications/
│   │   │   ├── sns_client.py
│   │   │   ├── ses_client.py
│   │   │   ├── whatsapp_client.py
│   │   │   └── notification_formatter.py
│   │   └── utils/
│   │       ├── logger.py
│   │       ├── date_helper.py
│   │       ├── currency_formatter.py
│   │       ├── metal_helper.py
│   │       ├── config_loader.py
│   │       └── error_handler.py
│   └── frontend/                  ← Phase 4
├── config/
│   ├── sources.json
│   ├── festivals.json
│   ├── metals.json
│   ├── cities.json
│   ├── alerts.json
│   ├── badges.json
│   └── languages.json
├── tests/
│   ├── unit/
│   │   ├── scrapers/
│   │   ├── lambdas/
│   │   └── shared/
│   ├── integration/
│   └── fixtures/
│       ├── mock_goldapi_response.json
│       ├── mock_kitco_html.html
│       └── mock_dynamo_tables.json
├── scripts/
│   ├── setup/
│   │   ├── setup_local.sh
│   │   ├── setup_aws.sh
│   │   └── create_secrets.sh
│   ├── deploy/
│   │   ├── deploy_infra.sh
│   │   ├── deploy_lambdas.sh
│   │   └── deploy_frontend.sh
│   ├── maintenance/
│   │   ├── check_source_health.sh
│   │   ├── reset_quota.sh
│   │   └── enable_source.sh
│   └── seed/
│       └── seed_test_data.py
├── .env.example
├── .gitignore
├── .pylintrc
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
├── CONTEXT.md                     ← THIS FILE
└── requirements.txt
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| AI Brain | Anthropic Claude API (claude-sonnet-4-6) |
| Infrastructure | AWS SAM (Serverless Application Model) |
| Primary Channel | Meta WhatsApp Business Cloud API |
| Scraping | requests + BeautifulSoup (Lambda friendly) |
| Frontend | React (Phase 4) |
| Package Manager | pip + venv |
| Code Style | pylint |
| Version Control | GitHub (open source, monorepo) |

---

## 💻 Local Dev Setup (Mac)

```bash
# Clone repo
git clone https://github.com/[username]/gold-agent
cd gold-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and fill in keys
cp .env.example .env

# Configure AWS CLI
aws configure
# Region: ap-south-1 (Mumbai)
```

Required in .env:
- ANTHROPIC_API_KEY
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- GOLDAPI_IO_KEY
- WHATSAPP_TOKEN (Phase 2)
- WHATSAPP_PHONE_ID (Phase 2)
- GOOGLE_PLACES_KEY (Phase 3)

---

## 🧑‍💻 Developer Info

- OS: Mac
- Python: Intermediate
- AWS: IAM user created under wife's root account
- AWS Region: ap-south-1 (Mumbai — closest to India)
- GitHub: Account exists
- VS Code: Installed

---

## 📍 Current Status

**Phase:** Phase 1 — Scraper engine complete — ready to build site scrapers

**Last Completed:**
- Virtual environment created and configured
- requirements.txt filled with all dependencies
- VS Code configured to use venv Python interpreter
- Scraper engine built — 4 files complete:
  - base_scraper.py — foundation class
  - api_fetcher.py — REST API handler
  - html_scraper.py — HTML scraper handler
  - data_normaliser.py — standard format converter
- metals.json updated — price ranges moved to config
- Everything pushed to GitHub

**Next Immediate Task:**
Build individual site scrapers — one at a time.

Start in this exact order:

Step 1 — src/scrapers/sites/gold_api_com.py
- Simplest source — no auth, unlimited, clean JSON
- Test immediately after building
- Wait for confirmation before next

Step 2 — src/scrapers/sites/metals_dev.py
- Most complex — multiple metals, INR rate, MCX, IBJA
- Update INR rate in data_normaliser after each run

Step 3 — src/scrapers/sites/goldapi_io.py
- Karat prices — header auth
- Map price_gram_24k and price_gram_22k correctly

Step 4 — src/scrapers/sites/free_gold_api.py
- Historical only — different handling
- Returns array not single record

Step 5 — src/scrapers/sites/goodreturns.py
- HTML scraper — city wise INR rates
- Use fetch_multiple for 8 cities

Step 6 — src/scrapers/sites/moneycontrol.py
- HTML scraper — MCX backup

Step 7 — src/scrapers/sites/rapaport.py
- HTML scraper — diamond index only — weekly

Do NOT skip ahead. Build and test one at a time.

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
| Rate calculation | Trimmed mean + reputation weight | Protects against outliers |
| Commercial model | Free first, partnerships later | Build users before monetising |
| Code philosophy | One file one responsibility | Readable, testable, maintainable |
| Version control | SSH keys on Mac | No username/password needed |
| Project structure | All placeholder files created upfront | See full shape of project from day one |
| Metals list | Gold, Silver, Platinum, Copper, Diamond | Copper added for Indian festival context |
| Yahoo Finance | Dropped | No clean REST API, redundant |
| MetalpriceAPI.com | Dropped for now | Free tier = 24hr delay |
| Metals-API.com | Future Phase 4 | Paid only — add when revenue starts |
| GoldAPI.io schedule | Twice daily | Stay within 100/month free limit |
| Metals.Dev schedule | Twice daily | Stay within 100/month free limit |
| Price ranges | Stored in metals.json | Not hardcoded — change without code edits |
| Karat prices | Calculate from purity if not provided | Works for all sources automatically |
| INR conversion | Stored from Metals.Dev | Single source of truth for exchange rate |
| Timestamp formats | Normalised to ISO 8601 UTC | Consistent across all sources |

---

*Last updated: Session 4 — Scraper engine complete, all 4 engine files built and pushed*
*Update this file at the end of every working session*
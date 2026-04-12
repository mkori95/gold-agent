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
| EventBridge | Scheduling — daily, weekly, festival |
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
/prices/YYYY/MM/DD/HH:MM.json
/prices/latest.json
/analysis/YYYY/MM/DD/summary_hindi.txt
/festivals/calendar.json
/reports/weekly/
/community/
/app/  ← React frontend files
```

### DynamoDB Tables
| Table | Purpose |
|---|---|
| gold-agent-live-prices | Latest consensus price per metal — what users see |
| gold-agent-source-health | Health status of every data source |
| gold-agent-quota-tracker | API usage counts per source per month |
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
metal                  ← partition key (gold / silver / platinum / copper)
price_usd              ← consensus trimmed mean result
price_inr              ← converted using Metals.Dev INR rate
unit                   ← troy_ounce
confidence             ← "high" / "medium" / "low" / "unavailable"
sources_used           ← list of source_ids that contributed
sources_count          ← number of validated sources
spread_percent         ← how far apart the sources were
spread_flagged         ← true if spread > 2%
snapshot_id            ← ISO timestamp of snapshot
inr_rate               ← INR exchange rate used
usd_to_inr             ← 1 / inr_rate
updated_at             ← when written
```

### Athena
Sits on top of S3 /prices/ folder. Used for historical queries and dashboard charts.

---

## 📊 Data Sources — ACTIVE LIST

### Active Sources
| # | Source ID | File | Metals | Limit | Status |
|---|---|---|---|---|---|
| 1 | gold_api_com | gold_api_com.py | Gold, Silver, Platinum, Copper | Unlimited | ✅ Built & tested |
| 2 | metals_dev | metals_dev.py | Gold, Silver, Platinum, Copper | 100/month | ✅ Built & tested |
| 3 | goldapi_io | goldapi_io.py | Gold, Silver, Platinum | 100/month | ✅ Built & tested |
| 4 | rapid_api_gold_silver | rapid_api_gold_silver.py | Gold + Silver city rates | 550k/month | ✅ Built & tested |
| 5 | goodreturns | goodreturns.py | Gold city rates (INR) | Unlimited | ❌ Disabled — AWS IPs blocked by Cloudflare |

### Disabled Sources
| Source | Reason |
|---|---|
| goodreturns | AWS Lambda IPs blocked by Cloudflare — replaced by RapidAPI |
| moneycontrol | MCX gold/silver data already captured in metals_dev extra{} — duplicate |
| rapaport | Paywalled — no public data to scrape |
| free_gold_api | Returns full dataset from 1258 AD — no date filtering, not useful |

### Current Metal Coverage
| Metal | Sources |
|---|---|
| Gold spot | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Silver spot | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Platinum spot | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Copper spot | gold_api_com ✅ metals_dev ✅ |
| Gold city rates (71 Indian + 6 international) | rapid_api_gold_silver ✅ |
| Silver city rates (71 Indian + 6 international) | rapid_api_gold_silver ✅ |

### Phase 4 Paid Sources (future)
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

### RapidAPI Gold Silver Rates India
- **API ID:** `gold_silver_rates_india`
- **Provider:** soralapps on RapidAPI
- **Base URL:** `https://gold-silver-live-prices.p.rapidapi.com`
- **Cost:** $1.50/month — 550,000 requests/month
- **Auth:** Header — `x-rapidapi-key` + `x-rapidapi-host`
- **Env key:** `RAPIDAPI_KEY`
- **Metals:** Gold + Silver
- **Coverage:** 77 locations (71 Indian cities + 6 international)

**Endpoints:**
- `/getAllPlaces` — list all available locations
- `/getGoldRate?place={city}` — current gold rate for a location
- `/getSilverRate?place={city}` — current silver rate for a location

**Parsing notes:**
- Gold: per 10gm in local currency → `unit = "gram_10"` → goes to `city_rates{}`
- Silver: per kg in local currency → `unit = "kg"` → goes to `city_rates{}`
- Prices come as strings with commas — strip commas, convert to float
- Dubai silver returns 0 from API — scraper correctly skips it (known data issue)
- Both units are excluded from trimmed mean consensus — city rates only

**77 Locations:**
Indian cities (71): puducherry, agra, raipur, srinagar, vijayawada, jodhpur, nashik, daman, noida, rajkot, aurangabad, guwahati, mysore, patna, jaipur, allahabad, ranchi, manipur, ludhiana, nagpur, silvassa, thane, visakhapatnam, gandhinagar, faridabad, ahmedabad, mumbai, meerut, chandigarh, kohima, varanasi, panaji, hubli, kolkata, kalyan, kanpur, dhanbad, bhopal, vadodara, indore, amritsar, lucknow, itanagar, imphal, coimbatore, madurai, thiruvananthapuram, shillong, agartala, dehradun, gangtok, new-delhi, pune, gwalior, chennai, jabalpur, lakshadweep, solapur, bengaluru, port-blair, surat, dispur, aizawl, ghaziabad, kota, hyderabad, bhubaneswar, howrah, gurgaon, bangalore, bareilly

International (6): united-states, united-kingdom, australia, dubai, saudi-arabia, singapore

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

Stored in DynamoDB `gold-agent-source-health` table — `consecutive_failures` field increments on each failure.

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

Stored in DynamoDB `gold-agent-quota-tracker` table.

---

### 4. Price Consensus Logic (Trimmed Mean)

**Step by step:**
```
Step 1  →  Collect all prices for a metal from all active sources
Step 2  →  Run anomaly detection — reject any price outside metals.json range
Step 3  →  Count VALIDATED sources only (sources that passed anomaly detection)
Step 4  →  Apply calculation based on validated source count
Step 5  →  Calculate spread across all validated prices
Step 6  →  Assign confidence level
Step 7  →  Store consensus + all raw source prices preserved
```

**Source count rules (based on VALIDATED sources, not total sources run):**
```
0 sources   →  No data — alert developer        →  confidence: "unavailable"
1 source    →  Use as-is, flag clearly           →  confidence: "low"
2 sources   →  Simple average                    →  confidence: "medium"
3+ sources  →  Drop highest + lowest, average rest  →  confidence: "high"
```

**Anomaly detection** — before including any price in the calculation:
- Check against `price_range_usd` in metals.json
- If price is outside range → reject that data point + log warning
- Other sources continue normally — one bad source never stops others

**Spread monitoring** — after calculating consensus:
```
spread_percent = (max - min) / consensus × 100

spread < 1%   →  Normal — log only
spread 1-2%   →  Log warning — sources diverging
spread > 2%   →  Log warning + flag in snapshot
```

**INR conversion** — Metals.Dev only (single source of truth):
```
inr_rate = currencies.INR from Metals.Dev response
usd_to_inr = 1 / inr_rate
price_inr = price_usd / inr_rate

If Metals.Dev fails → price_inr = null across entire snapshot
Never guess the exchange rate
```

**Raw source prices always preserved:**
```json
"source_prices": {
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00,
    "goldapi_io":   3106.50
}
```

---

### 5. INR Conversion Logic

```
Source provides USD only (all API sources)  →  Convert using exchange rate
Exchange rate source                        →  Metals.Dev only (single source of truth)
Exchange rate field                         →  currencies.INR from Metals.Dev response
Exchange rate formula                       →  usd_to_inr = 1 / currencies.INR
Exchange rate storage                       →  scraper.inr_rate on MetalsDevScraper
                                               → passed to merger explicitly by consolidator
```

INR conversion happens in the **consolidator via DataNormaliser** — never in individual scrapers.

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
      "price_usd": 3101.50,
      "price_inr": 282120.0,
      "unit": "troy_ounce",
      "confidence": "high",
      "sources_used": ["gold_api_com", "metals_dev", "goldapi_io"],
      "sources_count": 3,
      "source_prices": {
        "gold_api_com": 3100.00,
        "metals_dev":   3098.00,
        "goldapi_io":   3106.50
      },
      "spread_percent": 0.27,
      "spread_flagged": false,
      "karats": {
        "24K": { "price_usd": 3101.19, "price_inr": 281890.0 },
        "22K": { "price_usd": 2842.26, "price_inr": 258400.0 },
        "18K": { "price_usd": 2326.13, "price_inr": 211590.0 }
      },
      "city_rates": {
        "mumbai":  { "Gold 24 Karat (Rs ₹)": 139720.0, "Gold 22 Karat (Rs ₹)": 128077.0 },
        "delhi":   { "Gold 24 Karat (Rs ₹)": 139500.0, "Gold 22 Karat (Rs ₹)": 127900.0 }
      },
      "extra": {
        "mcx_gold":     3250.00,
        "ibja_gold":    3210.00,
        "lbma_gold_am": 3088.50,
        "lbma_gold_pm": 3092.75
      }
    },
    "silver": { },
    "platinum": { },
    "copper": { }
  }
}
```

---

### 7. Jeweller Rate Priority Logic

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

### 8. Community Rate Validation Logic

A rate must pass ALL 6 guardrails — fail any one → rate not shown:

```
Guardrail 1  →  Minimum 3 unique phone numbers reported
Guardrail 2  →  Spread between all reports must be < 2%
Guardrail 3  →  Rate must be within ±5% of official market rate
Guardrail 4  →  All reports must be less than 24 hours old
Guardrail 5  →  Weight by reporter reputation score
Guardrail 6  →  One report per phone number per jeweller
```

---

### 9. Community Rate Confidence Logic

```
3+ reports AND spread < 0.5%   →  ⭐⭐⭐ High confidence — show to user
3–5 reports AND spread < 1%    →  ⭐⭐ Medium confidence — show to user
Anything else                  →  Don't show — fall back to market rate
```

---

### 10. User Reputation Logic

Every user who submits jeweller rates has a hidden score (0–100):

```
Starting score     →  50 (neutral — new, unknown reporter)
Accurate report    →  Score increases
Outlier report     →  Score decreases
Consistent reports →  Score grows over time
```

---

### 11. Alert Logic

```
User sets price threshold  →  e.g. "Tell me when gold hits ₹55,000"
Alert checker runs         →  Every hour via EventBridge
Threshold breached         →  Send WhatsApp message immediately
Cooldown                   →  4 hours before alerting same user again
```

---

### 12. Festival Advisory Logic

```
EventBridge checks festival calendar  →  Daily
7 days before any festival            →  Trigger advisory Lambda
Advisory Lambda fetches               →  Current price + trend + historical context
Sends proactive WhatsApp to           →  All opted-in users in relevant region
Language                              →  User's saved preference (Hindi/Tamil/Telugu)
```

---

### 13. Language Detection Logic

```
First message from user     →  Auto-detect language
Save to DynamoDB            →  All future messages in same language
User can override           →  "Switch to Hindi" / "Hindi mein bolo"
Default if detection fails  →  English
```

---

### 14. WhatsApp 24-Hour Window Logic

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
PRIORITY 1 — Partner Rate (Phase 4)
→ Verified rate from paying jeweller partner

PRIORITY 2 — Community Rate (Phase 3)
→ Crowdsourced from users
→ Show WITH market rate alongside

PRIORITY 3 — Market Rate + Education (Phase 2)
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

### Phase 1 — The Engine ✅ COMPLETE
Fully automated data pipeline running in AWS Lambda. EventBridge fires daily at 6AM IST. Prices collected from 4 sources, consensus calculated, written to DynamoDB + S3.

### Phase 2 — The Product ← NEXT
WhatsApp chatbot with real users. Receive messages, answer price questions, set alerts.

### Phase 3 — The Community
Crowdsourced jeweller rates, location services, gamification.

### Phase 4 — The Business
Revenue, web dashboard, scale.

---

## 📁 Project Folder Structure

```
gold-agent/
├── config/
│   ├── alerts.json
│   ├── badges.json
│   ├── cities.json                         (empty placeholder — city data in sources.json)
│   ├── festivals.json
│   ├── languages.json
│   ├── metals.json                         ✅ finalised — price ranges for anomaly detection
│   └── sources.json                        ✅ finalised — all scraper config
├── docs/
│   ├── api/
│   ├── architecture/
│   │   └── consensus-logic.md              ✅ documented
│   ├── phases/
│   └── runbooks/
├── infra/
│   ├── terraform/                          ← DynamoDB, S3, IAM modules (stubs)
│   └── template.yaml                       ← SAM template (stubs for future Lambdas)
├── scripts/
│   ├── deploy/
│   ├── maintenance/
│   ├── seed/
│   └── setup/
├── src/
│   ├── lambdas/
│   │   ├── consolidator/                   ✅ COMPLETE — deployed to AWS
│   │   │   ├── anomaly_detector.py         ✅ unit tested
│   │   │   ├── consolidator.py             ✅ unit tested + end-to-end tested
│   │   │   ├── dynamo_writer.py            ✅ real boto3 — writes gold-agent-live-prices
│   │   │   ├── handler.py                  ✅ Lambda entry point
│   │   │   ├── merger.py                   ✅ unit tested — handles RapidAPI city rates
│   │   │   ├── s3_writer.py                ✅ real boto3 — writes gold-agent-prices
│   │   │   ├── trimmed_mean.py             ✅ unit tested
│   │   │   └── validator.py                ✅ unit tested
│   │   ├── agent-brain/                    ← Phase 2 (stubs)
│   │   ├── alert-checker/                  ← Phase 2 (stubs)
│   │   ├── conversation/                   ← Phase 2 (stubs)
│   │   ├── data-api/                       ← Phase 2 (stubs)
│   │   ├── festival-advisory/              ← Phase 2 (stubs)
│   │   ├── gamification/                   ← Phase 3 (stubs)
│   │   ├── location/                       ← Phase 3 (stubs)
│   │   ├── rate-validator/                 ← Phase 3 (stubs)
│   │   ├── report/                         ← Phase 4 (stubs)
│   │   ├── scraper/                        ← Phase 2 (stubs)
│   │   ├── web-chat/                       ← Phase 4 (stubs)
│   │   ├── weekly-digest/                  ← Phase 2 (stubs)
│   │   └── whatsapp-handler/               ← Phase 2 (stubs)
│   ├── scrapers/
│   │   ├── engine/
│   │   │   ├── api_fetcher.py              ✅ built
│   │   │   ├── base_scraper.py             ✅ built
│   │   │   ├── data_normaliser.py          ✅ built
│   │   │   ├── html_scraper.py             ✅ built — curl_cffi Cloudflare bypass
│   │   │   └── secrets_manager.py          ✅ built — fetches from AWS Secrets Manager
│   │   └── sites/
│   │       ├── gold_api_com.py             ✅ built and tested
│   │       ├── goldapi_io.py               ✅ built and tested
│   │       ├── goodreturns.py              ✅ built — disabled (AWS IPs Cloudflare blocked)
│   │       ├── metals_dev.py               ✅ built and tested
│   │       └── rapid_api_gold_silver.py    ✅ built and tested — 77 locations
│   └── shared/
│       ├── db/                             ← Phase 2 (stubs)
│       ├── models/                         ← Phase 2 (stubs)
│       ├── notifications/                  ← Phase 2 (stubs)
│       └── utils/                          ← Phase 2 (stubs)
├── tests/
│   ├── fixtures/
│   │   ├── mock_dynamo_tables.json         ✅ DynamoDB table reference
│   │   └── mock_goldapi_response.json      ✅ realistic GoldAPI.io response
│   ├── integration/                        ← Phase 2
│   └── unit/
│       ├── lambdas/
│       │   ├── test_anomaly_detector.py    ✅ 15 tests passing
│       │   ├── test_consolidator.py        ✅ 16 tests passing
│       │   ├── test_merger.py              ✅ 13 tests passing
│       │   ├── test_trimmed_mean.py        ✅ 11 tests passing
│       │   ├── test_validator.py           ✅ 14 tests passing
│       │   └── test_writers.py             ✅ 12 tests passing (boto3 mocked)
│       └── scrapers/
│           ├── test_gold_api_com.py        ✅ passing
│           ├── test_goldapi_io.py          ✅ passing
│           ├── test_goodreturns.py         ✅ passing (disabled in prod)
│           ├── test_metals_dev.py          ✅ passing
│           └── test_rapid_api_gold_silver.py ✅ 15 tests passing (live API)
├── .env                                    ← not committed — all API keys
├── .env.example
├── .gitignore
├── requirements.txt                        ✅ Phase 1 only
├── requirements-all.txt                    ← all phases (anthropic etc)
├── samconfig.toml                          ← not committed — SAM deploy config
├── setup.py
└── template.yml                            ✅ SAM template — ConsolidatorFunction
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| AI Brain (Phase 2) | Anthropic Claude API (claude-sonnet-4-5) |
| Infrastructure | AWS SAM (Lambda) + Terraform (infra) |
| Primary Channel | Meta WhatsApp Business Cloud API |
| Scraping | curl_cffi + BeautifulSoup |
| Frontend (Phase 4) | React |
| Package Manager | pip + venv |
| Version Control | GitHub (SSH keys) |
| Region | ap-south-1 (Mumbai) |
| AWS CLI | v2 — installed and configured |
| Terraform | Installed via Homebrew |
| SAM CLI | Installed via Homebrew |

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
RAPIDAPI_KEY=...
S3_BUCKET_NAME=gold-agent-prices
DYNAMO_LIVE_PRICES_TABLE=gold-agent-live-prices
AWS_REGION=ap-south-1
```

Phase 2+:
```
ANTHROPIC_API_KEY=...
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_ID=...
GOOGLE_PLACES_KEY=...
```

In Lambda, all keys come from AWS Secrets Manager (fetched by `secrets_manager.py` at startup).
Locally, all keys come from `.env` via `load_dotenv()`.

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

    def fetch(self) -> list:
        # implement this — return list of price records
```

### 3. Standard price record format (from build_price_record)
```json
{
    "metal": "gold",
    "price_usd": 3100.00,
    "currency": "USD",
    "price_inr": null,
    "unit": "troy_ounce",
    "source_id": "gold_api_com",
    "source_name": "GoldAPI.com",
    "timestamp": "2026-04-08T10:00:00Z",
    "extra": {}
}
```

### 4. price_inr is always null from API scrapers
INR conversion happens in consolidator via DataNormaliser — NOT in individual scrapers.

### 5. One metal/city failure never stops others
Always wrap per-metal or per-city logic in try/except and continue on failure.

### 6. HTML scraper uses curl_cffi — not requests
`html_scraper.py` uses `from curl_cffi import requests` with `impersonate="chrome120"`.
Never revert to standard `requests` — Indian finance sites are heavily Cloudflare-protected.

### 7. os.environ.get with blank env values
Use `or` fallback pattern — not default arg:
```python
S3_BUCKET = os.environ.get("S3_BUCKET_NAME") or "gold-agent-prices"
```
Reason: `get("KEY", default)` returns `""` if the var is set to blank in `.env`. The `or` fallback treats empty string as falsy.

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

### goldapi_io.py
- Auth: header — `x-access-token: KEY`
- 3 metals: gold, silver, platinum (NO copper)
- One API call per metal (3 calls total)
- **Unique: karat-wise gram prices** — no other source gives this
- Standard karats (24K, 22K, 18K) → `extra.karats{}`

### rapid_api_gold_silver.py
- Auth: headers — `x-rapidapi-key` + `x-rapidapi-host`
- Gold + Silver city rates for 77 locations
- Gold: per 10gm INR → `unit = "gram_10"` → merger routes to `city_rates{}`
- Silver: per kg INR → `unit = "kg"` → merger routes to `city_rates{}`
- 3 retries with 2 second wait (some locations timeout intermittently)
- Dubai silver returns 0 from API — scraper skips it (correct behaviour)
- Active locations driven by `sources.json locations.active` — no code change needed

### goodreturns.py
- No auth — unlimited HTML scraping via curl_cffi (Cloudflare bypass)
- Gold only — 28 cities — one HTTP request per city
- **Disabled in production** — AWS Lambda IPs are blocked by Cloudflare IP reputation
- `price_usd` = None, `price_inr` = 22K price, `unit` = "gram"
- Still kept in codebase — can re-enable if IP situation changes

### consolidator/ (Phase 1 — COMPLETE)

**Build order and responsibility:**

| File | Responsibility |
|---|---|
| trimmed_mean.py | Consensus math — trimmed mean algorithm |
| anomaly_detector.py | Price range validation against metals.json |
| validator.py | Scraper result structure validation |
| merger.py | Orchestrates anomaly detection + trimmed mean, builds metals dict |
| dynamo_writer.py | Writes snapshot to DynamoDB gold-agent-live-prices |
| s3_writer.py | Writes snapshot to S3 gold-agent-prices |
| consolidator.py | Main pipeline orchestrator |
| handler.py | Thin Lambda entry point |

**INR rate flow:**
```
MetalsDevScraper.run() → scraper.inr_rate stored on instance
→ consolidator._run_scrapers() extracts it via getattr()
→ passed explicitly to merger.merge(results, inr_rate=x)
→ merger calculates usd_to_inr = 1 / inr_rate
→ applied to all metal price_inr calculations
```

**RapidAPI city rate routing:**
```
unit == "gram_10" (gold)  →  merger._extract_city_rates()  →  gold city_rates{}
unit == "kg" (silver)     →  merger._extract_silver_city_rates()  →  silver city_rates{}
Both units                →  NEVER enter trimmed mean
```

**Karat price priority:**
```
GoldAPI.io provides karats → use directly (per gram USD)
GoldAPI.io missing/failed → calculate from purity ratios
    24K = consensus_price × 0.9999
    22K = consensus_price × 0.9166
    18K = consensus_price × 0.7500
```

---

## 🌐 html_scraper.py — Cloudflare Bypass

**Problem:** GoodReturns.in is behind Cloudflare Bot Management. Standard `requests` sends a Python TLS fingerprint — blocked with 403.

**Solution:** `curl_cffi` with `impersonate="chrome120"` — mimics Chrome's exact TLS handshake. Cloudflare passes it through.

**Note:** Even with curl_cffi, AWS Lambda IPs are blocked at the IP reputation level (not TLS level). GoodReturns works locally but not from Lambda.

---

## 📌 Key Decisions Log

| Decision | What We Chose | Why |
|---|---|---|
| Deployment | AWS Serverless Lambda | Cost effective, scales, no idle cost |
| Database | DynamoDB + S3 + Athena | No RDS needed, fully serverless |
| Primary channel | WhatsApp | 500M+ Indian users, no app needed |
| Languages | Hindi, Tamil, Telugu | Largest underserved vernacular markets |
| Repo type | Monorepo | One developer, simpler to manage |
| Infra as code | AWS SAM + Terraform | SAM for Lambda, Terraform for infrastructure |
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
| HTML scraper library | curl_cffi instead of requests | Bypasses Cloudflare TLS fingerprinting |
| GoodReturns unit | "gram" not "troy_ounce" | Retail per-gram city rates — not spot |
| GoodReturns in consensus | Excluded from trimmed mean | Different unit and price type — goes to city_rates{} only |
| GoodReturns in Lambda | Disabled — AWS IPs blocked | Replaced by RapidAPI gold-silver-rates-india |
| Raw source prices | Always stored in snapshot | Never throw data away — source_prices{} preserved |
| Spread monitoring | Calculated and stored | Large spread = signal of unusual market activity |
| Alert cooldown | 4 hours | Prevents spam when price fluctuates near threshold |
| Festival advisory | 7 days before | Enough lead time for users to plan purchases |
| Trimmed mean for 3 sources | Same trim rule as 4+ | One consistent rule — math is identical to median |
| Validated source count | Count post-anomaly-detection only | Prevents false high confidence from rejected prices |
| Spread thresholds | <1% normal, 1-2% warn, >2% flag | Catches diverging sources without false positives |
| Consolidator testing | Standalone script + thin Lambda wrapper | No Docker needed — same pattern as scrapers |
| AnomalyDetector independence | Standalone — reads metals.json directly | No circular dependency between scraper and consolidator layers |
| TrimmedMean class | Class not standalone function | Consistent OOP pattern across entire project |
| INR rate passing | Caller passes explicitly to merger | Consolidator owns orchestration, merger owns merging |
| Fixtures | mock_goldapi_response.json in consolidator tests | Large realistic responses in fixtures — not inline |
| os.environ.get blank env | Use `or` fallback, not default arg | `.env` blank value returns `""` not the default |
| RapidAPI city rate routing | unit field determines routing in merger | gram_10 = gold city rates, kg = silver city rates |
| test_writers.py boto3 | Mocked with MagicMock | Unit tests must run without AWS credentials |
| EventBridge schedule | Daily 6AM IST (cron 30 0 * * ? *) | Once daily — conserves API quota for Phase 1 |
| NAT Gateway | Skipped for Phase 1 | Costs $32/month — Lambdas don't need VPC for Phase 1 |
| VPC | Skipped for Phase 1 | Add in Phase 2 when real traffic starts |
| DynamoDB billing | PAY_PER_REQUEST | Free at our scale — no idle cost |
| Terraform state | S3 backend (gold-agent-terraform-state) | Safe, survives laptop loss |
| AWS Bedrock | Not needed | Will use Anthropic API directly via ANTHROPIC_API_KEY |

---

## 🧑‍💻 Developer Info

- Name: Manikanta
- OS: Mac (Mac Mini, 16GB RAM)
- Python: 3.12
- Python level: Intermediate
- AWS: IAM user gold-agent-dev under wife's root account
- AWS Region: ap-south-1 (Mumbai)
- AWS credits: ~$220 available, expiry August 2026
- GitHub: Account exists, SSH keys configured
- Branch: claude/laughing-banzai (Phase 1 work)
- VS Code: Installed, configured to use venv

---

## ✅ Phase 1 — What Is Complete

**All code deployed and running in production.**

### AWS Infrastructure
- ✅ IAM role — gold-agent-consolidator-role
- ✅ S3 bucket — gold-agent-prices
- ✅ S3 bucket — gold-agent-terraform-state
- ✅ DynamoDB tables — gold-agent-live-prices, gold-agent-source-health, gold-agent-quota-tracker
- ✅ Secrets Manager — METALS_DEV_API_KEY, GOLDAPI_IO_KEY, RAPIDAPI_KEY
- ✅ Lambda deployed — gold-agent-consolidator (ap-south-1, Python 3.12)
- ✅ EventBridge rule — gold-agent-daily-consolidator → fires daily 6AM IST

### Lambda Test Results (post-deploy)
```
rapid_api_gold_silver ✅ — 19 records (10 gold, 9 silver, Dubai silver skipped)
gold_api_com          ✅ — 4 metals
metals_dev            ✅ — 4 metals + INR rate 1 USD = ₹92.61
goldapi_io            ✅ — 3 metals + karat prices

GOLD:     $4,717.20 — ₹4,36,843 — confidence: high  — spread: 0.07%
SILVER:   $73.66    — ₹6,821    — confidence: high  — spread: 0.16%
PLATINUM: $2,023.82 — ₹1,87,419 — confidence: high  — spread: 0.16%
COPPER:   $5.70     — ₹528      — confidence: medium — spread: 2.29% ⚠️ flagged

DynamoDB: 4/4 metals written to gold-agent-live-prices ✅
S3:       prices/2026/04/09/01:10.json + prices/latest.json ✅
Duration: ~42 seconds
```

### All Unit Tests Passing (pytest format — 2026-04-12)
Run: `pytest tests/` — 83 passed, 41 skipped, 0 failed

- ✅ tests/unit/lambdas/test_trimmed_mean.py — 11 tests
- ✅ tests/unit/lambdas/test_anomaly_detector.py — 16 tests
- ✅ tests/unit/lambdas/test_validator.py — 14 tests
- ✅ tests/unit/lambdas/test_merger.py — 13 tests
- ✅ tests/unit/lambdas/test_writers.py — 12 tests (boto3 mocked)
- ✅ tests/unit/lambdas/test_consolidator.py — 17 tests
- ⏭️ tests/unit/scrapers/test_gold_api_com.py — 6 tests (skipped: live API)
- ⏭️ tests/unit/scrapers/test_goldapi_io.py — 9 tests (skipped: requires GOLDAPI_IO_KEY)
- ⏭️ tests/unit/scrapers/test_metals_dev.py — 11 tests (skipped: requires METALS_DEV_API_KEY)
- ⏭️ tests/unit/scrapers/test_rapid_api_gold_silver.py — 13 tests (skipped: requires RAPIDAPI_KEY)
- 🗑️ tests/unit/scrapers/test_goodreturns.py — deleted (retired scraper)

All test files converted from script format (if/else + sys.exit) to proper pytest format
(def test_* functions + assert statements). conftest.py added at project root for sys.path setup.

---

## 🚀 Next Steps — Phase 2

**Goal:** Build the WhatsApp chatbot so real users can ask price questions.

### Step 1 — WhatsApp Business API Setup
- Create Meta Business account
- Get a dedicated phone number
- Get `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_ID`
- Store both in AWS Secrets Manager

### Step 2 — Submit WhatsApp Templates
Submit all 7 templates for Meta approval (takes 24-48 hours):
1. welcome_message
2. price_alert
3. weekly_digest
4. festival_advisory
5. daily_morning_rate
6. price_drop_alert
7. price_rise_alert

### Step 3 — whatsapp-handler Lambda
Receives webhooks from Meta, validates signature, parses messages, routes to correct intent handler.

### Step 4 — agent-brain Lambda
Calls Anthropic Claude API. Builds context from DynamoDB live prices. Generates response in user's language.

### Step 5 — conversation Lambda
Handles: price queries, trend explanations, calculator (how much gold for X rupees), festival advice, alert setup.

### Step 6 — alert-checker Lambda
Runs hourly via EventBridge. Reads all user alert preferences from DynamoDB. Checks against current live prices. Sends WhatsApp alert if threshold breached.

### Step 7 — Wire Up API Gateway
Point Meta webhook URL → API Gateway → whatsapp-handler Lambda.

---

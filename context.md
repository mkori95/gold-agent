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

## 📊 Data Sources — FINAL ACTIVE LIST

> ⚠️ These are the ONLY active sources. yahoo_finance.py, ibja.py, kitco.py were removed — they were placeholder files not in sources.json.

### Active Sources (in build order)
| # | Source ID | File | Metals | Limit | Status |
|---|---|---|---|---|---|
| 1 | gold_api_com | gold_api_com.py | Gold, Silver, Platinum, Copper | Unlimited | ✅ Built & tested |
| 2 | metals_dev | metals_dev.py | Gold, Silver, Platinum, Copper | 100/month | ✅ Built & tested |
| 3 | goldapi_io | goldapi_io.py | Gold, Silver, Platinum | 100/month | ✅ Built & tested |
| 4 | free_gold_api | free_gold_api.py | Gold (historical) | Unlimited | ❌ Disabled permanently |
| 5 | goodreturns | goodreturns.py | Gold (city-wise INR) | Unlimited | ← BUILD NEXT |
| 6 | moneycontrol | moneycontrol.py | Gold, Silver (MCX backup) | Unlimited | Pending |
| 7 | rapaport | rapaport.py | Diamond (index only) | Unlimited | Pending |

### Why free_gold_api is Disabled
- Returns full dataset from 1258 AD — no date filtering supported
- No query params like `?limit=30` or `?from=2026-01-01` work
- Prices in GBP not USD
- Downloading entire dataset to grab last 30 days is wasteful and slow
- Our own S3 history will serve this need organically by Phase 2
- sources.json updated: `enabled: false`, `health_status: disabled`

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

### Community Rate Guardrails (6 rules)
1. Minimum 3 unique users before showing
2. Spread % must be < 2%
3. Reject if outside ±5% of official market rate
4. Reports expire after 24 hours
5. Reputation weighting — proven reporters get more weight
6. One report per person per jeweller

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

Status: Scraper engine complete. Building individual site scrapers now.

### Phase 2 — The Product (Months 2-3)
WhatsApp chatbot with real users.

### Phase 3 — The Community (Months 3-4)
Crowdsourced jeweller rates, location, gamification.

### Phase 4 — The Business (Months 5-6)
Revenue, web dashboard, scale.

---

## 📁 Correct Project Folder Structure

> ⚠️ Files NOT in this list have been removed: yahoo_finance.py, ibja.py, kitco.py

```
gold-agent/
├── config/
│   ├── sources.json
│   ├── festivals.json
│   ├── metals.json
│   ├── cities.json
│   ├── alerts.json
│   ├── badges.json
│   └── languages.json
├── src/
│   ├── __init__.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── base_scraper.py
│   │   │   ├── api_fetcher.py
│   │   │   ├── html_scraper.py
│   │   │   ├── data_normaliser.py
│   │   │   └── rate_limiter.py
│   │   └── sites/
│   │       ├── __init__.py
│   │       ├── gold_api_com.py      ✅ built and tested
│   │       ├── metals_dev.py        ✅ built and tested
│   │       ├── goldapi_io.py        ✅ built and tested
│   │       ├── free_gold_api.py     ❌ disabled
│   │       ├── goodreturns.py       ← build next
│   │       ├── moneycontrol.py      pending
│   │       └── rapaport.py          pending
│   ├── lambdas/
│   │   ├── scraper/
│   │   ├── consolidator/
│   │   ├── agent-brain/           ← Phase 2
│   │   ├── whatsapp-handler/      ← Phase 2
│   │   └── ...
│   └── shared/
│       ├── db/
│       ├── models/
│       ├── notifications/
│       └── utils/
├── tests/
│   └── unit/
│       └── scrapers/
│           ├── test_gold_api_com.py    ✅
│           ├── test_metals_dev.py      ✅
│           ├── test_goldapi_io.py      ✅
│           ├── test_goodreturns.py     ← build next
│           ├── test_moneycontrol.py    pending
│           └── test_rapaport.py       pending
├── setup.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore                     (includes .DS_Store)
├── CONTEXT.md
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 (Mac) |
| AI Brain | Anthropic Claude API (claude-sonnet-4-6) |
| Infrastructure | AWS SAM |
| Primary Channel | Meta WhatsApp Business Cloud API |
| Scraping | requests + BeautifulSoup |
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
python tests/unit/scrapers/test_gold_api_com.py

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

All API keys are in `.env` at project root. Every scraper and test file loads this automatically.

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

### 1. Every scraper and test file starts with
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

### 4. price_inr is always null from scrapers
INR conversion happens in data_normaliser / consolidator — NOT in individual scrapers. Never calculate INR inside a scraper.

### 5. One metal failure never stops others
Always wrap per-metal logic in try/except and continue on failure.

### 6. Test files always follow this structure
- TEST 1 — Load sources.json
- TEST 2 — Find source config block
- TEST 3 — Check API key is set (if applicable)
- TEST 4 — Initialise scraper
- TEST 5 — Run scraper (live API call)
- TEST 6 — Check all metals returned
- TEST 7+ — Source-specific validations
- Final TEST — Print full JSON output for visual inspection

### 7. Always run tests from project root
```bash
python tests/unit/scrapers/test_xyz.py
```

---

## 🔍 What Each Built Scraper Does

### gold_api_com.py
- No auth — unlimited calls
- 4 metals: gold, silver, platinum, copper
- Symbols: XAU, XAG, XPT, HG
- One API call per metal (4 calls total per run)
- No extra fields beyond price

### metals_dev.py
- Auth: query param — `?api_key=KEY`
- 4 metals: gold, silver, platinum, copper
- **ONE API call for all metals** — most efficient source
- Provides INR exchange rate — stored in `scraper.inr_rate`
- INR rate formula: `currencies.INR = 0.011` means `1 USD = 1/0.011 = ₹91`
- Copper price is per POUND in API — converted to troy ounce
  - Conversion: `price_per_toz = price_per_lb / 0.0685714`
  - Both stored: `price_usd` = converted toz, `extra.price_per_pound` = original
  - `extra.conversion_factor` = 0.0685714 (makes math transparent)
- Gold extra{}: mcx_gold, mcx_gold_am, mcx_gold_pm, ibja_gold, lbma_gold_am, lbma_gold_pm
- Silver extra{}: mcx_silver, mcx_silver_am, mcx_silver_pm, lbma_silver
- Platinum extra{}: lbma_platinum_am, lbma_platinum_pm

### goldapi_io.py
- Auth: header — `x-access-token: KEY`
- 3 metals: gold, silver, platinum (NO copper)
- One API call per metal (3 calls total per run)
- **Unique value: karat-wise gram prices** — no other source gives this
- Standard karats (24K, 22K, 18K) → stored in `extra.karats{}`
- Extended karats (21K, 20K, 16K, 14K, 10K) → stored in `extra.extended_karats{}`
- Market data in extra{}: ask, bid, change, change_percent, prev_close, open, high, low

---

## 🌆 goodreturns.py — What Next Chat Must Build

### What GoodReturns Gives Us
City-wise gold rates in INR for 8 Indian cities:
- Mumbai, Delhi, Chennai, Hyderabad, Bangalore, Kolkata, Ahmedabad, Pune
- 22K and 24K prices per 10 grams
- This is the most important Indian-specific data source

### How It's Different From API Scrapers
GoodReturns is an HTML scraper — not an API. It works like this:
```
Call URL → Get full HTML page → Find price table → 
Extract row → Extract cell → Clean text → Build record
```

### Key Facts
- Uses `HTMLScraper` from engine (not APIFetcher)
- One URL per city — 8 calls total per run
- URL pattern: `https://www.goodreturns.in/gold-rates-in-{city}.html`
- Auth: none needed
- Returns prices in INR directly — no USD conversion needed
- HTML scraping is fragile — if site redesigns, scraper breaks (handled by circuit breaker)

### What New Chat Must Do First
Before writing any code:
1. Open `https://www.goodreturns.in/gold-rates-in-mumbai.html` in browser
2. Right-click on price table → Inspect Element
3. Find the HTML tag and class/id of the price table
4. Find what a row looks like inside it
5. Share the HTML structure with Claude
6. Then Claude writes the scraper around real structure

### cities.json
Check `config/cities.json` for the exact city IDs and URL slugs we use. The URL slug may differ from our internal city ID (e.g. internal: `bengaluru`, URL: `bangalore`).

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
| Project structure | All placeholder files created upfront | See full shape from day one |
| Metals list | Gold, Silver, Platinum, Copper, Diamond | Copper added for Indian festival context |
| Yahoo Finance | Dropped | No clean REST API, redundant |
| ibja.py | Dropped placeholder | Was a scraper placeholder — Phase 4 has paid IBJA API |
| kitco.py | Dropped | Removed — not in sources.json |
| MetalpriceAPI.com | Dropped | Free tier = 24hr delay |
| Metals-API.com | Future Phase 4 | Paid only — add when revenue starts |
| GoldAPI.io schedule | Twice daily | Stay within 100/month free limit |
| Metals.Dev schedule | Twice daily | Stay within 100/month free limit |
| Price ranges | Stored in metals.json | Not hardcoded — change without code edits |
| INR conversion | From Metals.Dev only | Single source of truth for exchange rate |
| Timestamp formats | Normalised to ISO 8601 UTC | Consistent across all sources |
| Python package | setup.py + pip install -e . | Clean imports, no sys.path hacks |
| dotenv loading | load_dotenv() in every file | No manual export needed — works automatically |
| Copper unit | Convert to troy ounce | System-wide consistency |
| Copper original price | Stored in extra{} | Never throw data away |
| LBMA prices | Stored in extra{} | Valuable for Phase 2 agent brain |
| Karat prices | Standard 3 at top, extended 5 in extra{} | Consistency without losing data |
| free_gold_api | Disabled permanently | No date filtering — 1258 AD dataset not practical |

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

**Phase:** Phase 1 — Building individual site scrapers

**Scrapers Complete:**
- ✅ gold_api_com.py — built, tested, committed
- ✅ metals_dev.py — built, tested, committed
- ✅ goldapi_io.py — built, tested, committed
- ❌ free_gold_api.py — disabled permanently (see reason above)

**Next Immediate Task:**
Build `goodreturns.py` — HTML scraper for city-wise INR gold rates.

**Before writing goodreturns.py:**
Must inspect the live HTML of `https://www.goodreturns.in/gold-rates-in-mumbai.html` first and share the table HTML structure. Do NOT write any code until the real HTML structure is confirmed.

**After goodreturns.py:**
- moneycontrol.py — HTML scraper, MCX backup
- rapaport.py — HTML scraper, diamond index, weekly only

---

*Last updated: Session 5 — gold_api_com, metals_dev, goldapi_io all complete. free_gold_api disabled. goodreturns.py is next.*
*Update this file at the end of every working session*
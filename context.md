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
city_rates             ← per 10g INR per city from RapidAPI (gold) or per kg for silver
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
| 4 | rapid_api_gold_silver | rapid_api_gold_silver.py | Gold + Silver city rates | 550k/month | ✅ Built & tested |
| 5 | free_gold_api | free_gold_api.py | Gold (historical) | Unlimited | ❌ Disabled permanently |
| 6 | goodreturns | goodreturns.py | Gold (city-wise INR) | Unlimited | ❌ Disabled — AWS IPs blocked by Cloudflare |
| 7 | moneycontrol | — | MCX backup | Unlimited | ❌ Disabled — MCX data already in Metals.Dev |
| 8 | rapaport | — | Diamond index | Unlimited | ❌ Disabled — paywalled |

### Why Sources Were Skipped
- **moneycontrol** — MCX gold/silver data is already captured in `metals_dev.py` extra{} fields. Duplicate data, scraping risk not worth it.
- **rapaport** — Actual price list is behind a paid subscription. No public HTML to scrape. Diamond data deferred to Phase 2.
- **free_gold_api** — Returns full dataset from 1258 AD — no date filtering supported. Disabled permanently.

### Current Metal Coverage
| Metal | Sources |
|---|---|
| Gold spot | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Silver spot | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Platinum spot | gold_api_com ✅ metals_dev ✅ goldapi_io ✅ |
| Copper spot | gold_api_com ✅ metals_dev ✅ |
| Gold city rates (India + International) | rapid_api_gold_silver ✅ |
| Silver city rates (India + International) | rapid_api_gold_silver ✅ |

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

### Retired Sources
| Source | Reason |
|---|---|
| GoodReturns.in (goodreturns.py) | AWS IPs blocked by Cloudflare — replaced by RapidAPI source |

### New Source — RapidAPI Gold Silver Rates India
- **API ID:** `gold_silver_rates_india`
- **Provider:** soralapps on RapidAPI
- **Base URL:** `https://gold-silver-live-prices.p.rapidapi.com`
- **Cost:** $1.50/month — 550,000 requests/month
- **Auth:** Header — `x-rapidapi-key` + `x-rapidapi-host`
- **Env key:** `RAPIDAPI_KEY`
- **Schedule:** Every 2 hours
- **Metals:** Gold + Silver
- **Coverage:** 77 locations (71 Indian cities + 6 international)

**Endpoints:**
- `/getAllPlaces` — list all available locations
- `/getGoldRate?place={city}` — current gold rate for a location
- `/getSilverRate?place={city}` — current silver rate for a location
- `/getGoldPriceHistory?place={city}&no_of_days={n}` — gold history up to 300 days
- `/getSilverPriceHistory?place={city}&no_of_days={n}` — silver history up to 300 days

**Response format — Gold (Indian cities):**
```json
{
    "location": "MUMBAI",
    "variations per 10g": {
        "Gold 24 Karat (Rs ₹)": "139,720",
        "Gold 22 Karat (Rs ₹)": "128,077",
        "Gold 18 Karat (Rs ₹)": "104,790"
    },
    "GOLD": {
        "price": "139,720.00",
        "change": "+0.00 (+0.000%)",
        "per value": "Rs ₹ / 10gm"
    }
}
```

**Response format — Gold (International):**
```json
{
    "location": "DUBAI",
    "variations per 10g": {
        "Gold 24 Karat (AED د.إ)": "467",
        "Gold 22 Karat (AED د.إ)": "428"
    },
    "GOLD": {
        "price": "466.75",
        "change": "+5.75 (+1.250%)",
        "per value": "AED د.إ / 10gm"
    }
}
```

**Response format — Silver (Indian cities):**
```json
{
    "location": "MUMBAI",
    "variations per Kg": {
        "Silver 999 Fine (Rs ₹)": "225,530",
        "Silver 925 Sterling (Rs ₹)": "208,615"
    },
    "SILVER": {
        "price": "225,530.00",
        "change": "+0.00 (+0.000%)",
        "per value": "Rs ₹ / 1kg"
    }
}
```

**Parsing notes:**
- Prices come as strings with commas — strip commas, convert to float
- Currency and karat embedded in key names — parse carefully
- Gold unit: per 10gm (Indian standard)
- Silver unit: per kg

**77 Locations to scrape:**

Indian cities (71):
```
puducherry, agra, raipur, srinagar, vijayawada, jodhpur,
nashik, daman, noida, rajkot, aurangabad, guwahati, mysore,
patna, jaipur, allahabad, ranchi, manipur, ludhiana, nagpur,
silvassa, thane, visakhapatnam, gandhinagar, faridabad,
ahmedabad, mumbai, meerut, chandigarh, kohima, varanasi,
panaji, hubli, kolkata, kalyan, kanpur, dhanbad, bhopal,
vadodara, indore, amritsar, lucknow, itanagar, imphal,
coimbatore, madurai, thiruvananthapuram, shillong, agartala,
dehradun, gangtok, new-delhi, pune, gwalior, chennai,
jabalpur, lakshadweep, solapur, bengaluru, port-blair,
surat, dispur, aizawl, ghaziabad, kota, hyderabad,
bhubaneswar, howrah, gurgaon, bangalore, bareilly
```

International (6):
```
united-states, united-kingdom, australia, dubai,
saudi-arabia, singapore
```


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
 
**Why 3+ uses same rule as 4+ (revised from Session 8):**
Previous logic used median for exactly 3 sources and trimmed mean for 4+.
Simplified to one consistent rule: always trim highest + lowest for 3+ sources.
For exactly 3 sources, trimming highest + lowest leaves 1 — same as median.
One rule is simpler to reason about, test, and maintain.
 
**Why validated source count matters (revised from Session 8):**
If 3 sources run but anomaly detection rejects one, you have 2 trusted prices.
Counting total sources run would give false "high" confidence with only "medium"
quality data. Always count sources that PASSED validation.
 
**Anomaly detection** — before including any price in the calculation:
- Check against `price_range_usd` in metals.json
- If price is outside range → reject that data point + log warning
- Example: gold at $500 or $50,000 → rejected immediately
- Other sources continue normally — one bad source never stops others
 
**Spread monitoring** — after calculating consensus:
```
spread_percent = (max - min) / consensus × 100
 
spread < 1%   →  Normal — log only
spread 1-2%   →  Log warning — sources diverging
spread > 2%   →  Log warning + flag in snapshot
```
 
**GoodReturns is NOT included in trimmed mean** — different unit (gram vs troy
ounce), different currency (INR vs USD), different price type (retail vs spot).
Feeds directly into `city_rates{}` on the snapshot only.
 
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
| AWS CLI        | v2.17.49 — installed |
| Terraform      | Installed via Homebrew |
| SAM CLI        | Installed via Homebrew |

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

| RAPIDAPI_KEY | 1 | RapidAPI dashboard | gold-silver-rates-india API key — $1.50/month |

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

### consolidator/ (Phase 1 — COMPLETE)
 
**Build order and responsibility:**
 
| File | Responsibility | Dependencies |
|---|---|---|
| trimmed_mean.py | Consensus math — trimmed mean algorithm | None — pure math |
| anomaly_detector.py | Price range validation against metals.json | metals.json only — no scraper engine |
| validator.py | Scraper result structure validation | None |
| merger.py | Orchestrates anomaly detection + trimmed mean, builds metals dict | AnomalyDetector, TrimmedMean |
| dynamo_writer.py | Writes snapshot to DynamoDB (stub) | None |
| s3_writer.py | Writes snapshot to S3 (stub) | None |
| consolidator.py | Main pipeline orchestrator | All of the above + all scrapers |
| handler.py | Thin Lambda entry point | Consolidator |
 
**INR rate flow:**
```
MetalsDevScraper.run() → scraper.inr_rate stored on instance
→ consolidator._run_scrapers() extracts it via getattr()
→ passed explicitly to merger.merge(results, inr_rate=x)
→ merger calculates usd_to_inr = 1 / inr_rate
→ applied to all metal price_inr calculations
```
 
**GoodReturns routing:**
```
GoodReturns records (unit == "gram")
→ merger._extract_city_rates() picks them up
→ go directly into city_rates{} on the snapshot
→ NEVER enter trimmed mean calculation
→ NEVER in source_prices{}
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
| Trimmed mean for 3 sources | Same trim rule as 4+ | Simpler — one consistent rule, math is identical to median |
| Validated source count | Count post-anomaly-detection only | Prevents false high confidence from rejected prices |
| Spread thresholds | <1% normal, 1-2% warn, >2% flag | Catches diverging sources without false positives |
| Claude Code | Not using — requires paid plan ($20/month Pro minimum) | Free plan has no Claude Code access. Will revisit when Phase 2 starts and iteration loops become intense enough to justify cost. |
| OpenClaw | Not using for Gold Agent development | OpenClaw is a personal assistant tool — not a dev tool. Not relevant to building Gold Agent. Claude Code is the right tool when needed. |
| VS Code + Claude | No official free integration available | Official Claude VS Code extension requires paid plan. Gemini workaround exists but Gemini is not Claude — not worth it for this project. |
| Development workflow | Claude.ai chat + manual copy to VS Code | Working well. Session by session, explain → decide → code. Better for learning and understanding every decision. |
| Consolidator build order | trimmed_mean → anomaly_detector → validator → merger → writers → consolidator → handler | Each file depends on the previous. Build small, test small, integrate at the end. |
| Consolidator test strategy | Unit tests with mock data first, end-to-end after all files done | Avoids API calls during development. Faster feedback loop. End-to-end only when all pieces are ready. |
| AnomalyDetector independence | Standalone — reads metals.json directly, no dependency on BaseScraper | Consolidator layer must not depend on scraper engine layer. Clean separation. Easier to test. No circular dependencies. |
| TrimmedMean class | Class (Option B) not standalone function | Consistent with OOP pattern used across entire project — BaseScraper, APIFetcher, HTMLScraper, DataNormaliser all classes. |
| INR rate passing to Merger | Caller passes explicitly: merger.merge(results, inr_rate=x) | Cleaner than merger extracting from results. Consolidator owns orchestration, merger owns merging. Easier to test with mock data. |
| Fixture usage | mock_goldapi_response.json used in consolidator test | Large realistic API responses stored in fixtures rather than cluttering test files with inline data. |
| mock_kitco_html.html | Deleted | Kitco dropped as source. Empty fixture referencing unused source. |
| consolidator/README.md | Deleted | Empty placeholder. Real docs live in docs/architecture/consensus-logic.md. |
| Project cleanliness | rate_limiter.py + response_parser.py kept empty | Intentional placeholders. Rate limiting in sources.json config. Response parsing in individual scrapers. |
| urllib3 warning | Ignored for now | RequestsDependencyWarning from requests library — harmless, everything works. Fix later with pip install urllib3==2.2.3 if needed. |
| GoodReturns price_usd | Always null — expected and correct | GoodReturns gives INR only. price_usd=None by design. These records go to city_rates{} not consensus. |
| AWS infrastructure tool | Terraform for infra + SAM for Lambda deploy | Terraform handles all 18+ AWS services cleanly. SAM handles Lambda packaging, zip, layers, dependencies. Industry standard split used by real teams. |
| Terraform scope | VPC, DynamoDB, S3, IAM, EventBridge, SNS, SES | Long-lived infrastructure resources that rarely change |
| SAM scope | Lambda function packaging and deployment only | SAM is simpler for Python Lambda with dependencies |
| Terraform experience | Manikanta is a beginner with Terraform | Will be guided step by step in AWS setup session |
| AWS CLI | Not yet installed on Mac | First step in AWS setup session |
| AWS setup timing | After Phase 1 local complete, before Phase 2 | Need live data pipeline before building WhatsApp bot |
| IAM user | gold-agent-dev created in wife's AWS account | Separate from old s3-user account — clean start |
| AWS credentials | Configured on Mac via aws configure | Points to wife's account — account ID confirmed |
| Terraform install | Via Homebrew | Simplest install on Mac |
| SAM CLI install | Via Homebrew | Needed for Lambda packaging and deployment |
| Old AWS account | s3-user in account 340752829103 — not used | Wrong account — only had S3 access |
| Terraform state | S3 backend (gold-agent-terraform-state) | Safe, survives laptop loss, industry standard |
| Terraform structure | Separate modules per service | Cleaner, scalable, one responsibility per module |
| DynamoDB billing | PAY_PER_REQUEST | Free at our scale — no idle cost |
| NAT Gateway | Skipped for Phase 1 | Costs $32/month — Lambdas don't need VPC for Phase 1 |
| VPC | Skipped for Phase 1 | Add in Phase 2 when real traffic starts |
| .terraform/ | Added to .gitignore | Contains 725MB provider binary — never commit |
| src/config/ removed | Deleted — config/ at root is included in SAM package automatically | Redundant duplication — .samignore does not exclude config/ |
| RapidAPI retry logic | 3 retries with 2 second wait | Some locations timeout intermittently — retry is cleaner than delay |
| Dubai silver | Warn not fail in test | API returns 0 for Dubai silver — known API data issue, correctly skipped by scraper |
| Active locations | Driven by sources.json locations.active | To enable all 77 locations — update sources.json only, no code change |
| APIFetcher timeout | Increased from 10s to 30s | RapidAPI endpoints occasionally slow to respond |
| RapidAPI city rate routing | unit == "gram_10" → gold city_rates, unit == "kg" → silver city_rates | Merger identifies city-rate records by unit field — not source_id |
| dynamo_writer.py | Real boto3 wired — table gold-agent-live-prices | Moved from stub to production — Decimal/str conversion required for DynamoDB |
| s3_writer.py | Real boto3 wired — bucket gold-agent-prices | Moved from stub to production — put_object with ContentType application/json |
| test_writers.py | boto3 mocked with MagicMock | Unit tests must run without AWS credentials — mock boto3.resource and boto3.client |
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

**Phase 1 — 100% COMPLETE ✅**
**AWS Setup — COMPLETE ✅**
**sam build + sam deploy — COMPLETE ✅**
**EventBridge schedule — COMPLETE ✅ (daily 6AM IST)**
**Next: Phase 2 — WhatsApp Bot**

### AWS Infrastructure — All Done
- ✅ AWS CLI installed and configured (gold-agent-dev IAM user)
- ✅ IAM role — gold-agent-consolidator-role
- ✅ Terraform + SAM CLI installed via Homebrew
- ✅ S3 state bucket — gold-agent-terraform-state
- ✅ S3 prices bucket — gold-agent-prices
- ✅ DynamoDB tables — gold-agent-live-prices, gold-agent-source-health, gold-agent-quota-tracker
- ✅ Secrets Manager — gold-agent/metals-dev-api-key, gold-agent/goldapi-io-key, gold-agent/rapidapi-key
- ✅ secrets_manager.py — fetches and caches secrets at Lambda startup
- ✅ config_loader.py — handles config paths for local and Lambda
- ✅ Lambda deployed — gold-agent-consolidator live in ap-south-1 (previous version)

### Code Review + Fixes (Session 14) — All Done
Full code review was done. All issues found and fixed:

- ✅ consolidator.py — `rapid_api_gold_silver` added to SCRAPER_REGISTRY, `goodreturns` removed
- ✅ sources.json — `goodreturns` disabled (Cloudflare blocks AWS IPs), `moneycontrol` disabled (empty file, MCX in Metals.Dev), `rapaport` disabled (empty file, paywalled)
- ✅ merger.py — RapidAPI city rates now routed correctly to `city_rates{}`
  - `unit == "gram_10"` (gold) → gold city_rates via `extra.location`
  - `unit == "kg"` (silver) → new `_extract_silver_city_rates()` via `extra.location`
  - Previously: all RapidAPI records were silently dropped (no USD price, non-troy-ounce unit)
- ✅ dynamo_writer.py — real boto3 wired (was logging stub) — writes to `gold-agent-live-prices`
- ✅ s3_writer.py — real boto3 wired (was logging stub) — writes to `gold-agent-prices`
  - Bug fixed: `os.environ.get("S3_BUCKET_NAME", default)` returns `""` if var set to blank in `.env` — changed to `or` fallback
- ✅ test_writers.py — boto3 mocked with MagicMock, checks `success` status (not `stub`)
- ✅ test_rapid_api_gold_silver.py — TEST 7 warns on Dubai silver instead of crashing (API returns 0)

### End-to-End Test Results (Session 14) — PASSING ✅
Run locally with real scrapers + real AWS writes:

```
Scrapers initialised: [rapid_api_gold_silver, gold_api_com, metals_dev, goldapi_io]
goodreturns / moneycontrol / rapaport — Disabled in sources.json — skipping

RapidAPI:  19 records — 10 gold locations ✅, 9 silver locations ✅, Dubai silver skipped (0 from API)
gold_api_com:  4 metals ✅
metals_dev:    4 metals ✅ — INR rate: 1 USD = ₹92.39
goldapi_io:    3 metals ✅ — karat prices included

GOLD consensus:     $4,719.80 — ₹4,35,609 — confidence: high  — spread: 0.03%
SILVER consensus:   $74.15    — ₹6,843    — confidence: high  — spread: 0.23%
PLATINUM consensus: $2,032.94 — ₹1,87,628 — confidence: high  — spread: 0.38%
COPPER consensus:   $5.72     — ₹528      — confidence: medium — spread: 2.31% (flagged)

DynamoDB: 4/4 metals written to gold-agent-live-prices ✅
S3:       prices/2026/04/08/22:56.json (6995 bytes) + prices/latest.json ✅

Status: success — Duration: 50s
```

### All Tests Passing
- ✅ tests/unit/lambdas/test_trimmed_mean.py
- ✅ tests/unit/lambdas/test_anomaly_detector.py
- ✅ tests/unit/lambdas/test_validator.py
- ✅ tests/unit/lambdas/test_merger.py
- ✅ tests/unit/lambdas/test_writers.py — boto3 mocked, success status
- ✅ tests/unit/lambdas/test_consolidator.py
- ✅ tests/unit/scrapers/test_rapid_api_gold_silver.py — all 15 tests passing (live API)
- ✅ tests/unit/scrapers/test_gold_api_com.py
- ✅ tests/unit/scrapers/test_metals_dev.py
- ✅ tests/unit/scrapers/test_goldapi_io.py

### Git — Branch: claude/laughing-banzai
- ✅ All changes committed and pushed
- ✅ PR open at https://github.com/mkori95/gold-agent/pull/new/claude/laughing-banzai
- ⏳ PR not yet merged

### sam build + sam deploy — COMPLETE ✅
- Rebuilt Lambda with Python 3.12 venv (upgraded from 3.9)
- All dependencies packaged: boto3, curl_cffi, beautifulsoup4, requests, python-dotenv, lxml
- `sam deploy --guided` — updated stack `gold-agent` in ap-south-1
- Lambda invoked and tested — status 200, 42 seconds, all 4 metals written

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
```

### EventBridge Schedule — COMPLETE ✅
- Rule: `gold-agent-daily-consolidator`
- Schedule: `cron(30 0 * * ? *)` — every day at 6:00 AM IST (00:30 UTC)
- State: ENABLED
- Target: gold-agent-consolidator Lambda
- Decision: once daily (not every 2 hours) — conserves API quota for Phase 1

### Next Immediate Tasks — Phase 2
1. **WhatsApp Business API setup** — create Meta Business account, get phone number, get WHATSAPP_TOKEN + WHATSAPP_PHONE_ID
2. **Submit 7 WhatsApp templates** for approval (welcome, price_alert, weekly_digest, festival_advisory, daily_morning_rate, price_drop_alert, price_rise_alert)
3. **whatsapp-handler Lambda** — receives webhooks, parses messages, routes intents
4. **agent-brain Lambda** — calls Claude API, builds context from DynamoDB, generates response
5. **conversation Lambda** — price queries, trend explanations, festival advice
6. **alert-checker Lambda** — hourly threshold check, sends alerts via WhatsApp
 
---

### Scrapers — ALL COMPLETE
- ✅ gold_api_com.py — built, tested
- ✅ metals_dev.py — built, tested
- ✅ goldapi_io.py — built, tested
- ✅ rapid_api_gold_silver.py — built, tested (77 locations, retry, zero-price rejection)
- ❌ goodreturns.py — disabled (AWS IPs blocked by Cloudflare)
- ❌ free_gold_api.py — disabled permanently
- ❌ moneycontrol.py — disabled (MCX covered by Metals.Dev)
- ❌ rapaport.py — disabled (paywalled)
 
### Engine — COMPLETE
- ✅ base_scraper.py
- ✅ api_fetcher.py
- ✅ html_scraper.py — curl_cffi Cloudflare bypass
- ✅ data_normaliser.py
 
### Consolidator — ALL COMPLETE
- ✅ trimmed_mean.py — unit tested (11 tests passing)
- ✅ anomaly_detector.py — unit tested (15 tests passing)
- ✅ validator.py — unit tested (14 tests passing)
- ✅ merger.py — unit tested (13 tests passing) — handles RapidAPI city rates
- ✅ dynamo_writer.py — real boto3 wired (table: gold-agent-live-prices)
- ✅ s3_writer.py — real boto3 wired (bucket: gold-agent-prices)
- ✅ consolidator.py — unit tested (16 tests passing)
- ✅ handler.py — thin Lambda wrapper
 
### Tests — ALL PASSING
- ✅ tests/unit/lambdas/test_trimmed_mean.py
- ✅ tests/unit/lambdas/test_anomaly_detector.py
- ✅ tests/unit/lambdas/test_validator.py
- ✅ tests/unit/lambdas/test_merger.py
- ✅ tests/unit/lambdas/test_writers.py — boto3 mocked, checks success status
- ✅ tests/unit/lambdas/test_consolidator.py
- ✅ tests/unit/scrapers/test_rapid_api_gold_silver.py — all 15 tests passing
- ✅ End-to-end: python src/lambdas/consolidator/consolidator.py — status 200
 
### Fixtures — FILLED
- ✅ tests/fixtures/mock_goldapi_response.json — realistic GoldAPI.io response
- ✅ tests/fixtures/mock_dynamo_tables.json — DynamoDB table structures reference
 
### Documentation — Session 9
- ✅ docs/architecture/consensus-logic.md — full consensus logic documented
 

## 🔑 Key Technical Decisions Made in Session 9
 
### Consolidator Architecture
- Built file by file — each with its own unit test before moving to next
- AnomalyDetector is completely standalone — no scraper engine dependency
- TrimmedMean is a class — consistent with rest of project OOP pattern
- INR rate passed explicitly from consolidator to merger — not extracted inside merger
- Merger orchestrates AnomalyDetector + TrimmedMean — does not duplicate their logic
 
### Testing Strategy
- Unit tests use patch.object to mock _run_scrapers — zero live API calls
- Fixtures used for large realistic responses (GoldAPI.io)
- End-to-end test runs all live scrapers — used only after all unit tests pass
- End-to-end returned status 200 with real prices ✅
 
### Consensus Logic Finalised
- 3+ sources: always trim highest + lowest, average rest (same rule as 4+)
- Source count = validated sources after anomaly detection — not total sources run
- Spread thresholds: <1% normal, 1-2% warn, >2% flag in snapshot
- GoodReturns excluded from consensus — different unit, currency, price type
 
### Tools & Workflow
- Claude Code (Pro plan) — active, installed on Mac
- Claude.ai chat + VS Code workflow — working well for development
- AWS CLI configured, Terraform + SAM CLI installed via Homebrew

## 🔑 Key Technical Decisions — Sessions 9–14

### Consolidator Architecture
- Built file by file — each with its own unit test before moving to next
- AnomalyDetector standalone — no scraper engine dependency
- TrimmedMean is a class — consistent with project OOP pattern
- INR rate passed explicitly from consolidator to merger — not extracted inside merger
- Merger orchestrates AnomalyDetector + TrimmedMean

### Testing Strategy
- Unit tests use patch.object to mock `_run_scrapers` — zero live API calls
- Fixtures used for large realistic responses (GoldAPI.io)
- End-to-end test runs all live scrapers — only after all unit tests pass
- test_writers.py mocks boto3 — runs without AWS credentials

### AWS Infrastructure
- Terraform for infrastructure (DynamoDB, S3, IAM, EventBridge, SNS, SES)
- SAM for Lambda packaging and deployment only
- CodeUri = project root (`.`) — keeps import paths consistent
- `.terraform/` never committed — causes 692MB Lambda package bloat
- `requirements.txt` slimmed to Phase 1 only — anthropic etc in requirements-all.txt

### Secrets Management
- All API keys in AWS Secrets Manager
- `secrets_manager.py` fetches and caches at Lambda startup (class-level cache)
- `load_dotenv()` kept in all files — works locally, does nothing in Lambda

### RapidAPI Replacing GoodReturns
- GoodReturns retired — Cloudflare blocks AWS IPs (IP reputation, not TLS)
- RapidAPI gold-silver-rates-india — $1.50/month, 550k requests, 77 locations
- Gold: per 10gm in local currency — `unit = "gram_10"`
- Silver: per kg in local currency — `unit = "kg"`
- Both routed to `city_rates{}` in snapshot, never enter trimmed mean
- Dubai silver returns 0 from API — scraper correctly skips it

### S3Writer Bucket Name Bug (Session 14)
- `os.environ.get("S3_BUCKET_NAME", default)` returns `""` when var is set to blank in `.env`
- Fixed with `or` fallback: `os.environ.get("S3_BUCKET_NAME") or "gold-agent-prices"`
| AWS Bedrock | ❌ Not needed | Claude Pro covers agent brain |

# ============================================================
# ADD to Key Decisions table:
# ============================================================

| Claude Pro | Subscribed | Unlocks Claude Code, covers OpenClaw brain, no Bedrock needed |
| OpenClaw vs Hermes | OpenClaw chosen | Simpler, works with Claude Pro natively, Claude Code integration built in |
| Hermes deferred | Not using now | Revisit in 1 month if OpenClaw memory insufficient |
| Bedrock for agents | Not needed | Claude Pro subscription used by OpenClaw via OAuth |
| Agent architecture | OpenClaw + Claude Code only | No separate dev/test/git agents — Claude Code handles all coding natively |
| Mac Mini | 16GB RAM — ready | OpenClaw runs 24/7 as system service |
| AWS credits expiry | August 2026 | $220 available, ~12 months runway at $18/month burn rate |
| Mission Control | builderz-labs/mission-control | Dashboard for agent ops, task approvals, cost monitoring |

# ============================================================
# ADD new section — Agent OS:
# ============================================================

### 9. Agent OS — Personal AI Development Studio

**Status:** Architecture finalised. Setup in next session.
**Full details:** See AGENT_OS.md in repo root.

**Stack:**
- OpenClaw on Mac Mini (orchestrator, 24/7)
- Claude Pro as brain (via existing subscription, no extra cost)
- Claude Code as coding hands (writes, tests, pushes)
- Mission Control as dashboard (localhost:3000)
- WhatsApp as communication interface

**How it works:**
```
You (WhatsApp) → OpenClaw → Claude Code → GitHub branch → You approve
```

**Setup time:** ~2.5 hours, same day.

**Rules:**
- OpenClaw reads CONTEXT.md before every task
- Never deploys to AWS without Manikanta approval
- Never commits to main — always feature branch
- Daily 8AM IST briefing via WhatsApp

# ============================================================
# UPDATE Next Immediate Tasks:
# ============================================================

## 📋 Next Session Tasks (Priority Order)

1. **OpenClaw setup on Mac Mini** (2.5 hours)
   - Install + WhatsApp gateway
   - Feed CONTEXT.md as skill
   - Install Mission Control
   - Test: "run all tests in gold-agent"

2. **AWS Setup** (parallel track)
   - Install AWS CLI on Mac
   - Terraform for infrastructure
   - Deploy consolidator Lambda
   - Wire dynamo_writer + s3_writer with real boto3
   - EventBridge schedule (hourly)

3. **Phase 2 WhatsApp bot** (after AWS live)
   - agent-brain Lambda
   - whatsapp-handler Lambda
   - alert-checker Lambda

# ============================================================
# Final status line:
# ============================================================

*Last updated: Session 9 FINAL*
*Phase 1 complete locally. Claude Pro active. Mac Mini ready.*
*Next: OpenClaw setup + AWS deployment in parallel.*
*Agent OS architecture finalised in AGENT_OS.md.*

*Last updated: Session 13 — RapidAPI scraper built and partially tested. src/config/ deleted — single config/ at root. secrets_manager.py updated with RAPIDAPI_KEY. Tests 1-7 passing for all 10 locations. Dubai silver skipped — API data issue. Tests 8-15 crashing — fix next session. Next session: fix remaining tests, update SCRAPER_REGISTRY, disable goodreturns, wire real boto3 calls for DynamoDB and S3, sam build + sam deploy.*
 
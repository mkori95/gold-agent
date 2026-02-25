# 🥇 Gold Agent

> A WhatsApp-first precious metals advisor for Indian families.
> Real-time gold, silver, platinum and copper prices — in Hindi, Tamil and Telugu —
> for your city, before every festival.

---

## Table of Contents

- [What We Are Building](#what-we-are-building)
- [Why This Exists](#why-this-exists)
- [Metals Covered](#metals-covered)
- [Languages Supported](#languages-supported)
- [Architecture Overview](#architecture-overview)
- [AWS Services](#aws-services)
- [Data Sources](#data-sources)
- [API Response Formats](#api-response-formats)
- [Scraper Engine](#scraper-engine)
- [Config Files](#config-files)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Key Decisions](#key-decisions)

---

## What We Are Building

A WhatsApp chatbot that tells Indian families the right time to buy gold,
silver, platinum and copper — in their language — for their city.

Users save a phone number and chat naturally in WhatsApp.
No app download. No account creation. Phone number is identity.

**The one line vision:**
> "A personal gold buying advisor that lives in WhatsApp —
> tells you the right time to buy gold, silver and platinum —
> in your language, for your city, before every festival."

---

## Why This Exists

- Indian housewives check gold prices by calling their jeweller
  (conflict of interest) or asking their husband
- No app or service serves this audience in Hindi, Tamil or Telugu
- WhatsApp is already on every phone — no download needed
- General AI (ChatGPT, Claude, Gemini) cannot do proactive alerts,
  persistent memory, or city-specific Indian rates reliably
- The India-specific angle (IBJA rates, city-wise INR, MCX,
  festival calendar) is our strongest differentiator

---

## Metals Covered

| Metal | Symbol | Live Price | Karats | Notes |
|---|---|---|---|---|
| Gold | XAU | ✅ | 24K, 22K, 18K | Primary metal |
| Silver | XAG | ✅ | None | Widely bought at Dhanteras |
| Platinum | XPT | ✅ | None | Growing interest in India |
| Copper | HG | ✅ | None | Festival buying — vessels, idols |
| Diamond | — | ❌ | None | Education only — Rapaport index |

---

## Languages Supported

| Language | Auto-detected |
|---|---|
| Hindi | ✅ |
| Tamil | ✅ |
| Telugu | ✅ |

Language is auto-detected from the user's message.
User never has to select a language manually.

---

## Architecture Overview

- Fully serverless on AWS — no EC2, everything is Lambda
- Primary channel: WhatsApp Business API (Meta Cloud API)
- AI brain: Anthropic Claude API (claude-sonnet-4-6)
- Database: DynamoDB + S3 + Athena
- Infrastructure as code: AWS SAM
- Region: ap-south-1 (Mumbai) — closest to India, Indian IP address

**Why Mumbai region:**
When our Lambda runs in Mumbai it has an Indian IP address.
GoodReturns.in and Moneycontrol naturally serve Indian prices.
Latency to Indian servers is 20-50ms vs 180-230ms from US regions.

---

## AWS Services

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

## Data Sources

### Active API Sources

#### 1. Gold-API.com
- **Type:** API
- **Cost:** Free — unlimited requests
- **Auth:** None required
- **Metals:** Gold, Silver, Platinum, Copper
- **Schedule:** Every 60 minutes
- **Role:** Primary live price source — runs every hour
- **Base URL:** `https://api.gold-api.com`

#### 2. Metals.Dev
- **Type:** API
- **Cost:** Free — 100 requests/month
- **Auth:** API key as query param (`?api_key=xxx`)
- **Metals:** Gold, Silver, Platinum, Copper
- **Schedule:** Twice daily (every 720 minutes)
- **Role:** MCX rates + IBJA rates + INR conversion rate
- **Base URL:** `https://api.metals.dev/v1`
- **Env key:** `METALS_DEV_API_KEY`
- **Why twice daily:** Stays within 100/month free limit (60/month used)

#### 3. GoldAPI.io
- **Type:** API
- **Cost:** Free — 100 requests/month
- **Auth:** API key in header (`x-access-token: YOUR_KEY`)
- **Metals:** Gold, Silver, Platinum
- **Schedule:** Twice daily (every 720 minutes)
- **Role:** Karat-wise gram prices (24K, 22K, 18K) — unique value
- **Base URL:** `https://www.goldapi.io/api`
- **Env key:** `GOLDAPI_IO_KEY`
- **Why twice daily:** Stays within 100/month free limit (60/month used)

#### 4. FreeGoldAPI.com
- **Type:** API
- **Cost:** Free — unlimited
- **Auth:** None required
- **Metals:** Gold only
- **Schedule:** Once weekly
- **Role:** Historical data only — 768 years of gold prices
- **Base URL:** `https://freegoldapi.com`
- **Important:** NOT a live price source — updated once daily at 6AM UTC

### Active Scraper Sources

#### 5. GoodReturns.in
- **Type:** Scraper (HTML)
- **Cost:** Free
- **Metals:** Gold, Silver
- **Schedule:** Every 120 minutes
- **Role:** City-wise INR rates — primary India city source
- **Cities:** Mumbai, Delhi, Chennai, Hyderabad, Bangalore, Kolkata, Ahmedabad, Pune
- **Delay:** 5 seconds between city requests + random 0-2s extra

#### 6. Moneycontrol
- **Type:** Scraper (HTML)
- **Cost:** Free
- **Metals:** Gold, Silver
- **Schedule:** Every 120 minutes during MCX hours only (9AM-11:30PM IST)
- **Role:** MCX India rates — backup source for Metals.Dev

#### 7. Rapaport
- **Type:** Scraper (HTML)
- **Cost:** Free
- **Metals:** Diamond only
- **Schedule:** Once weekly
- **Role:** Diamond index — no single price — used for education

### Dropped Sources

| Source | Reason Dropped |
|---|---|
| Yahoo Finance | No clean REST API — Python library only, redundant with Gold-API.com |
| MetalpriceAPI.com | Free tier = 24hr delayed data — not suitable for live prices |
| Metals-API.com | Paid only — no free tier available |
| Kitco.com | Redundant — Gold-API.com covers same data better |
| APMEX.com | US retail platform only — no API — not India relevant |

### Future Paid Sources

| Source | Cost | What it adds | When |
|---|---|---|---|
| Metals-API.com | $4.99/month | Indian city prices as clean API — replaces GoodReturns scraper | Phase 4 |
| IBJA Official API | Contact for pricing | RBI approved benchmark — used by HDFC, ICICI, Muthoot | Phase 4 |

---

## API Response Formats

### Gold-API.com

**Endpoints verified in Postman: ✅**

**Get all symbols:**
```
GET https://api.gold-api.com/symbols
```
```json
[
    { "name": "Gold",     "symbol": "XAU" },
    { "name": "Silver",   "symbol": "XAG" },
    { "name": "Platinum", "symbol": "XPT" },
    { "name": "Copper",   "symbol": "HG"  }
]
```

**Get current price:**
```
GET https://api.gold-api.com/price/{symbol}
```
Example: `GET https://api.gold-api.com/price/XAU`
```json
{
    "name": "Gold",
    "price": 5215.60,
    "symbol": "XAU",
    "updatedAt": "2026-02-25T17:19:42Z",
    "updatedAtReadable": "a few seconds ago"
}
```

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Metal name |
| `price` | float | Current USD spot price per troy ounce |
| `symbol` | string | Trading symbol XAU / XAG / XPT / HG |
| `updatedAt` | string | ISO 8601 timestamp in UTC |
| `updatedAtReadable` | string | Human readable — "a few seconds ago" |

**Symbols to use:**
- Gold → `XAU`
- Silver → `XAG`
- Platinum → `XPT`
- Copper → `HG`

---

### Metals.Dev

**Endpoints verified in Postman: ✅**

**Get latest prices:**
```
GET https://api.metals.dev/v1/latest?api_key={key}&currency=USD&unit=toz
```
```json
{
    "status": "success",
    "currency": "USD",
    "unit": "toz",
    "metals": {
        "gold": 5213.67,
        "silver": 90.775,
        "platinum": 2329.98,
        "copper": 0.414,
        "palladium": 1816.892,
        "mcx_gold": 5521.0088,
        "mcx_gold_am": 5454.2097,
        "mcx_gold_pm": 5437.7839,
        "mcx_silver": 91.7206,
        "mcx_silver_am": 91.7493,
        "mcx_silver_pm": 91.273,
        "ibja_gold": 5441.4523,
        "lbma_gold_am": 5171.75,
        "lbma_gold_pm": 5191.55,
        "lbma_silver": 90.70,
        "lbma_platinum_am": 2293.00,
        "lbma_platinum_pm": 2323.00,
        "lbma_palladium_am": 1829.00,
        "lbma_palladium_pm": 1832.00
    },
    "currencies": {
        "INR": 0.0110022345,
        "USD": 1,
        "EUR": 1.1810916991,
        "GBP": 1.3563069397
    },
    "timestamps": {
        "metal": "2026-02-25T17:30:03.605Z",
        "currency": "2026-02-25T17:29:16.538Z"
    }
}
```

| Field | Type | Meaning |
|---|---|---|
| `metals.gold` | float | USD spot price per troy ounce |
| `metals.silver` | float | USD spot price per troy ounce |
| `metals.platinum` | float | USD spot price per troy ounce |
| `metals.copper` | float | USD spot price per troy ounce |
| `metals.mcx_gold` | float | MCX India gold price |
| `metals.mcx_gold_am` | float | MCX morning session gold price |
| `metals.mcx_gold_pm` | float | MCX evening session gold price |
| `metals.mcx_silver` | float | MCX India silver price |
| `metals.mcx_silver_am` | float | MCX morning session silver price |
| `metals.mcx_silver_pm` | float | MCX evening session silver price |
| `metals.ibja_gold` | float | IBJA benchmark gold price |
| `metals.lbma_gold_am` | float | London gold morning fix |
| `metals.lbma_gold_pm` | float | London gold evening fix |
| `metals.lbma_silver` | float | London silver fix |
| `metals.lbma_platinum_am` | float | London platinum morning fix |
| `metals.lbma_platinum_pm` | float | London platinum evening fix |
| `currencies.INR` | float | Value of 1 INR expressed in USD |
| `timestamps.metal` | string | When metal prices were last updated |
| `timestamps.currency` | string | When currency rates were last updated |

**Critical — INR conversion formula:**
```
currencies.INR = 0.0110022345
This means: 1 INR = 0.011 USD
Therefore:  1 USD = 1 / 0.011 = 90.89 INR

Gold price in INR = gold_usd / currencies.INR
Example: 5213.67 / 0.0110022345 = ₹473,878
```

**Query parameters:**
- `currency=USD` — prices returned in USD
- `unit=toz` — troy ounce (standard for precious metals)

---

### GoldAPI.io

**Endpoints verified in Postman: ✅**

**Auth:** Add header `x-access-token: YOUR_API_KEY` to every request

**Get current price:**
```
GET https://www.goldapi.io/api/{symbol}/USD
```
Example: `GET https://www.goldapi.io/api/XAU/USD`
```json
{
    "timestamp": 1772041039,
    "metal": "XAU",
    "currency": "USD",
    "exchange": "FOREXCOM",
    "symbol": "FOREXCOM:XAUUSD",
    "prev_close_price": 5142.845,
    "open_price": 5142.845,
    "low_price": 5121.57,
    "high_price": 5217.73,
    "open_time": 1771977600,
    "price": 5211.43,
    "ch": 68.59,
    "chp": 1.33,
    "ask": 5212.05,
    "bid": 5211.33,
    "price_gram_24k": 167.5514,
    "price_gram_22k": 153.5888,
    "price_gram_21k": 146.6074,
    "price_gram_20k": 139.6261,
    "price_gram_18k": 125.6635,
    "price_gram_16k": 111.7009,
    "price_gram_14k": 97.7383,
    "price_gram_10k": 69.8131
}
```

| Field | Type | Meaning |
|---|---|---|
| `timestamp` | int | Unix timestamp — seconds since Jan 1 1970 UTC |
| `price` | float | Current USD spot price per troy ounce |
| `ch` | float | Price change today in USD |
| `chp` | float | Price change today as percentage |
| `ask` | float | Price to buy at — slightly higher than spot |
| `bid` | float | Price to sell at — slightly lower than spot |
| `price_gram_24k` | float | Price per gram for 24K gold in USD |
| `price_gram_22k` | float | Price per gram for 22K gold in USD |
| `price_gram_18k` | float | Price per gram for 18K gold in USD |
| `open_price` | float | Price at market open today |
| `low_price` | float | Lowest price today |
| `high_price` | float | Highest price today |
| `prev_close_price` | float | Yesterday's closing price |

**Converting Unix timestamp to readable date:**
```python
from datetime import datetime, timezone
datetime.fromtimestamp(1772041039, tz=timezone.utc)
# → 2026-02-25 17:17:19+00:00
```

**Symbols to use:**
- Gold → `XAU`
- Silver → `XAG`
- Platinum → `XPT`

---

### FreeGoldAPI.com

**Endpoints verified in Postman: ✅**

**Get full historical dataset:**
```
GET https://freegoldapi.com/data/latest.json
```
Returns an array — oldest record first, newest record last:
```json
[
    {
        "date": "1258-01-01",
        "price": 0.89,
        "source": "measuringworth_british (GBP)"
    },
    {
        "date": "1960-01-01",
        "price": 35.17,
        "source": "world_bank"
    },
    {
        "date": "2025-12-31",
        "price": 2650.00,
        "source": "yahoo_finance"
    }
]
```

| Field | Type | Meaning |
|---|---|---|
| `date` | string | Date in YYYY-MM-DD format |
| `price` | float | Gold price in USD (GBP for pre-1791 records) |
| `source` | string | Which underlying data source this record came from |

**To get the latest price:**
```python
data = response.json()
latest = data[-1]  # Last item in array = most recent
```

**Important notes:**
- Returns entire 768-year history in one API call (~1678 records)
- Updated once daily at 6AM UTC via GitHub Actions
- Pre-1791 prices are in GBP not USD
- Last record in array is the most recent price
- **NOT suitable for live price tracking**
- Used for trend context — "has gold gone up over 5 years?"

---

## Scraper Engine

The scraper engine lives in `src/scrapers/engine/`.
It has 4 files. Every individual site scraper builds on top of these.

---

### base_scraper.py

**What it is:**
Abstract base class. Every scraper inherits from this.
Cannot be used directly — must be inherited.

**Why it exists:**
Defines common behaviour all scrapers share — logging, error handling,
standard result format, price validation. Write once, use everywhere.

**Key methods:**

| Method | Arguments | Returns | What it does |
|---|---|---|---|
| `__init__` | `source_config: dict` | — | Loads config from sources.json — sets source_id, name, url, metals, fields_map |
| `fetch` | — | `list` | Abstract — every child class MUST implement this — returns list of price records |
| `run` | — | `dict` | Safely runs fetch() — catches all errors — returns standard result object |
| `build_result` | `status, data, error, duration` | `dict` | Builds standard result object — same structure for every scraper |
| `build_price_record` | `metal, price_usd, currency, price_inr, unit, extra` | `dict` | Builds standard price record — same structure for every metal |
| `is_valid_price` | `price: float, metal: str` | `bool` | Sanity checks price against min/max ranges from metals.json |
| `_load_metals_config` | — | `dict` | Loads metals.json — returns dict keyed by metal id |

**Standard result format (returned by run()):**
```json
{
    "source_id": "gold_api_com",
    "source_name": "Gold-API.com",
    "status": "success",
    "data": [...],
    "error": null,
    "duration_seconds": 0.84,
    "scraped_at": "2026-02-25T17:19:42+00:00",
    "records_count": 4
}
```

**Status values:**
- `success` — fetch() ran and returned data
- `failed` — fetch() threw an exception
- `skipped` — source is disabled in sources.json

**Price validation ranges (from metals.json — not hardcoded):**

| Metal | Min USD | Max USD |
|---|---|---|
| Gold | 500 | 15,000 |
| Silver | 5 | 500 |
| Platinum | 200 | 10,000 |
| Copper | 0.05 | 50 |
| Diamond | 1,000 | 50,000 |

Prices outside these ranges are flagged as suspicious and logged as warnings.
Ranges are stored in `config/metals.json` — change them there without touching code.

---

### api_fetcher.py

**What it is:**
Handles all HTTP REST API calls.
Used by API-type scrapers — Gold-API.com, Metals.Dev, GoldAPI.io.

**Why it exists:**
Every API source needs HTTP calls, auth handling, error handling.
Write the logic once here instead of repeating in every site scraper.

**Key methods:**

| Method | Arguments | Returns | What it does |
|---|---|---|---|
| `__init__` | `source_config: dict` | — | Loads config — sets base_url, auth_config, timeout |
| `fetch` | `endpoint: str, params: dict, headers: dict` | `dict` | Makes GET request to API — returns parsed JSON response |
| `_build_headers` | `extra_headers: dict` | `dict` | Builds standard request headers including User-Agent |
| `_apply_auth` | `headers: dict, params: dict` | `tuple` | Adds API key to header or query param based on auth config |
| `_handle_http_errors` | `response: Response` | `None` | Raises clear error messages for each HTTP error code |

**Auth types supported:**

| Auth type | How it works | Example source |
|---|---|---|
| `none` | No auth needed — open API | Gold-API.com |
| `header` | API key added as request header | GoldAPI.io — uses `x-access-token` |
| `query_param` | API key added as URL parameter `?api_key=xxx` | Metals.Dev |

Auth type is read from `sources.json` — no code changes needed to change auth method.

**HTTP errors handled:**

| Status Code | Meaning | Error message raised |
|---|---|---|
| 200 | Success | No error — returns normally |
| 401 | Unauthorized | Check your API key in .env file |
| 403 | Forbidden | API key may not have access to this endpoint |
| 429 | Rate limit exceeded | Quota may be exhausted for this month |
| 404 | Endpoint not found | Check the URL in sources.json |
| 500+ | Server error | Source may be down temporarily |

**Default settings:**
- Timeout: 10 seconds per request
- User-Agent: `GoldAgent/1.0`

---

### html_scraper.py

**What it is:**
Handles all HTML page scraping.
Used by scraper-type sources — GoodReturns.in, Moneycontrol, Rapaport.

**Why it exists:**
Some sources have no API — we have to download their web pages
and extract price data from HTML. This handles the downloading part.
Individual site scrapers handle the extraction part.

**How HTML scraping works:**
1. Download raw HTML page using requests library
2. Parse HTML using BeautifulSoup + lxml
3. Return BeautifulSoup object to site scraper
4. Site scraper uses `soup.find("div", class_="gold-rate")` to extract data

**Key methods:**

| Method | Arguments | Returns | What it does |
|---|---|---|---|
| `__init__` | `source_config: dict` | — | Loads config — sets base_url, delay from sources.json |
| `fetch` | `endpoint: str, params: dict, extra_headers: dict` | `BeautifulSoup` | Downloads one page — returns parsed HTML object |
| `fetch_multiple` | `endpoints: list, extra_headers: dict` | `list` | Downloads multiple pages with polite delay between each |
| `_build_headers` | `extra_headers: dict` | `dict` | Builds browser-like headers to avoid being blocked |
| `_polite_delay` | — | `None` | Waits configured seconds + random 0-2 extra seconds |
| `_handle_http_errors` | `response: Response` | `None` | Raises clear errors for each HTTP error code |

**Anti-blocking measures:**

| Measure | What it does | Why |
|---|---|---|
| Chrome User-Agent | Pretends to be Chrome browser on Mac | Websites block requests with bot-like user agents |
| `Accept-Language: en-IN` | Tells website we're browsing from India | Gets Indian content and prices naturally |
| Polite delay | Waits 5+ seconds between requests | Too many fast requests = detected as bot |
| Random extra delay | Adds 0-2 random seconds on top of configured delay | Fixed timing looks like a bot — random looks human |

**fetch_multiple() — how it handles failures:**
If one city page fails — it logs the error and continues with the next city.
Returns list of `(endpoint, BeautifulSoup or None)` tuples.
`None` means that page failed — the site scraper skips it.

**HTTP errors handled:**

| Status Code | Meaning | Error message raised |
|---|---|---|
| 200 | Success | No error — returns normally |
| 403 | Website blocking us | Update User-Agent or add more delay |
| 404 | Page not found | URL may have changed — check endpoint in sources.json |
| 429 | Too many requests | Increase delay_between_requests_seconds in sources.json |
| 500+ | Server error | Source may be down temporarily |

---

### data_normaliser.py

**What it is:**
Converts raw price data from any source into one standard format.
Every scraper calls this before returning data.

**Why it exists:**
Every source returns data differently — different field names,
different timestamp formats, some have karat prices some don't,
some have INR some don't. The consolidator needs one consistent format.

**Key methods:**

| Method | Arguments | Returns | What it does |
|---|---|---|---|
| `__init__` | — | — | Loads metals config — purity ratios and price ranges |
| `normalise` | `metal, price_usd, source_id, source_name, timestamp, price_inr, inr_rate, karat_prices_usd, extra` | `dict` | Main method — converts raw data to standard format |
| `_normalise_timestamp` | `timestamp` | `str` | Converts any timestamp format to ISO 8601 UTC string |
| `_convert_to_inr` | `price_usd: float` | `float` | Converts USD price to INR using stored rate |
| `_normalise_karats` | `metal, price_usd, price_inr, karat_prices_usd` | `dict` | Calculates or maps karat prices for gold |
| `update_inr_rate` | `inr_rate: float` | `None` | Updates stored INR rate — called by Metals.Dev scraper |
| `_load_metals_config` | — | `dict` | Loads metals.json — returns dict keyed by metal id |

**Timestamp formats handled:**

| Format | Example | Source that uses it | How we handle it |
|---|---|---|---|
| ISO string with Z | `"2026-02-25T17:19:42Z"` | Gold-API.com | Replace Z with +00:00, parse as datetime |
| Unix integer | `1772041039` | GoldAPI.io | `datetime.fromtimestamp(ts, tz=UTC)` |
| None | `null` | GoodReturns.in | Use `datetime.now(UTC)` |

All converted to: `"2026-02-25T17:19:42+00:00"`

**Karat price logic:**
```
If source provides karat prices directly → use them as-is
    Example: GoldAPI.io gives price_gram_24k = 167.55 → use directly

If source only provides spot price → calculate from purity ratios in metals.json
    24K = spot_price × 0.9999
    22K = spot_price × 0.9166
    18K = spot_price × 0.7500
```

Purity ratios come from `config/metals.json` — not hardcoded.
Only gold has karat prices — silver, platinum, copper return empty dict.

**INR conversion formula:**
```
Metals.Dev returns: currencies.INR = 0.0110022345
This means: 1 INR = 0.011 USD

To get USD → INR rate:
usd_to_inr = 1 / 0.0110022345 = 90.89

Gold in INR = gold_usd × usd_to_inr
Example: 5213.67 × 90.89 = ₹473,878
```

INR rate is stored in memory after Metals.Dev runs.
All other scrapers use this stored rate to convert their USD prices.

**Standard normalised price record:**
```json
{
    "metal": "gold",
    "price_usd": 5213.67,
    "price_inr": 473878.0,
    "unit": "troy_ounce",
    "source_id": "gold_api_com",
    "source_name": "Gold-API.com",
    "timestamp": "2026-02-25T17:19:42+00:00",
    "karats": {
        "24K": { "price_usd": 5212.49, "price_inr": 473771.0 },
        "22K": { "price_usd": 4778.78, "price_inr": 434407.0 },
        "18K": { "price_usd": 3910.25, "price_inr": 355583.0 }
    },
    "extra": {}
}
```

---

## Config Files

### config/metals.json

Defines all metals the system knows about.
`data_normaliser.py` and `base_scraper.py` read from this file.

**Key fields per metal:**

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Internal identifier — used everywhere in code |
| `name` | string | English display name |
| `name_hindi` | string | Hindi display name |
| `name_tamil` | string | Tamil display name |
| `name_telugu` | string | Telugu display name |
| `symbol` | string | International trading symbol (XAU, XAG etc) |
| `unit` | string | troy_ounce for metals, carat for diamond |
| `live_price` | bool | false for diamond — no single live price |
| `karats` | array | Karat definitions with purity ratios — gold only |
| `price_range_usd` | object | min/max for price sanity validation |
| `sources` | array | Which source ids cover this metal |

### config/sources.json

Master config for every data source.
The entire scraper system is driven by this file.
Add or disable sources here — no code changes needed.

**Key fields per source:**

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Internal source identifier |
| `type` | string | `api` or `scraper` |
| `priority` | int | 1=free API, 2=paid API, 3=scraper |
| `enabled` | bool | Toggle source on/off without code changes |
| `health_status` | string | healthy / warning / disabled |
| `consecutive_failures` | int | Tracked by circuit breaker |
| `metals` | array | Which metals this source covers |
| `endpoints` | object | URL paths for each operation |
| `auth` | object | Auth type, header name, env variable name |
| `rate_limit` | object | Monthly limit, current count, strategy |
| `schedule` | object | Frequency in minutes, active hours IST, timezone |
| `failure_handling` | object | Max failures, retry delay, circuit breaker reset, fallback source |
| `fields_map` | object | Maps source field names to our standard field names |

---

## Circuit Breaker Pattern

Every source has automatic failure handling built in.

```
Fail 1 → consecutive_failures = 1 → WARNING  → retry in 15 min
Fail 2 → consecutive_failures = 2 → WARNING  → retry in 15 min
Fail 3 → consecutive_failures = 3 → CRITICAL → CIRCUIT BREAKER TRIPS
       → health_status = "disabled"
       → enabled = false
       → SNS + SES alert sent to developer immediately
       → Auto recovery attempt after 60 minutes
       → If recovered → re-enable + send recovery notification ✅
       → If still broken → stay disabled + send failure notification ❌
```

**Notification severity levels:**

| Level | Trigger | Alert method |
|---|---|---|
| ⚠️ WARNING | 1-2 failures | CloudWatch log only |
| 🔶 ALERT | 2 failures | Email via SES |
| 🔴 CRITICAL | 3 failures — circuit breaker trips | Email + SNS immediately |
| ✅ RECOVERY | Source comes back up | Email — "source is back" |

**Fallback sources (from sources.json):**
- Gold-API.com fails → fallback to Metals.Dev
- Metals.Dev fails → fallback to Gold-API.com
- GoldAPI.io fails → fallback to Gold-API.com
- GoodReturns.in fails → fallback to Moneycontrol
- Moneycontrol fails → fallback to GoodReturns.in

---

## Project Structure

```
gold-agent/
├── config/
│   ├── sources.json          ← master source config — scraper reads this
│   ├── metals.json           ← metal definitions, karats, price ranges
│   ├── festivals.json        ← festival calendar
│   ├── cities.json           ← supported Indian cities
│   ├── alerts.json           ← default alert thresholds
│   ├── badges.json           ← gamification badge definitions
│   └── languages.json        ← supported languages
├── src/
│   ├── scrapers/
│   │   ├── engine/           ← base classes — built in session 4
│   │   │   ├── base_scraper.py
│   │   │   ├── api_fetcher.py
│   │   │   ├── html_scraper.py
│   │   │   └── data_normaliser.py
│   │   └── sites/            ← individual site scrapers — next to build
│   │       ├── gold_api_com.py
│   │       ├── metals_dev.py
│   │       ├── goldapi_io.py
│   │       ├── free_gold_api.py
│   │       ├── goodreturns.py
│   │       ├── moneycontrol.py
│   │       └── rapaport.py
│   ├── lambdas/
│   │   ├── scraper/          ← Phase 1 — orchestrates all scrapers
│   │   ├── consolidator/     ← Phase 1 — merges and validates data
│   │   ├── agent-brain/      ← Phase 2 — Claude AI integration
│   │   ├── whatsapp-handler/ ← Phase 2 — WhatsApp webhook receiver
│   │   ├── conversation/     ← Phase 2 — conversation types
│   │   ├── alert-checker/    ← Phase 2 — price threshold alerts
│   │   ├── weekly-digest/    ← Phase 2 — weekly summaries
│   │   ├── festival-advisory/← Phase 2 — festival buying alerts
│   │   ├── rate-validator/   ← Phase 3 — community rate validation
│   │   ├── location/         ← Phase 3 — nearby jeweller search
│   │   ├── gamification/     ← Phase 3 — badges and leaderboard
│   │   ├── report/           ← Phase 4 — PDF reports
│   │   ├── data-api/         ← Phase 4 — web dashboard API
│   │   └── web-chat/         ← Phase 4 — web chat interface
│   ├── shared/
│   │   ├── db/               ← DynamoDB and S3 clients
│   │   ├── models/           ← data models
│   │   ├── notifications/    ← SNS, SES, WhatsApp clients
│   │   └── utils/            ← logger, date helper, formatters
│   └── frontend/             ← Phase 4 — React web dashboard
├── infra/                    ← AWS SAM infrastructure as code
├── tests/                    ← unit and integration tests
├── scripts/                  ← setup, deploy, maintenance scripts
├── .env                      ← real API keys — NEVER commit to GitHub
├── .env.example              ← placeholder keys — safe to commit
├── requirements.txt          ← Python dependencies
└── CONTEXT.md                ← session context — read at start of every session
```

---

## Local Setup

```bash
# Clone the repo
git clone git@github.com:mkori95/gold-agent.git
cd gold-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Copy env file and fill in your real keys
cp .env.example .env
# Edit .env and add your API keys
```

**VS Code setup:**
1. Press `Cmd + Shift + P`
2. Type `Python: Select Interpreter`
3. Select the one showing `venv` in the path

---

## Environment Variables

| Variable | Phase | Where to get it | Notes |
|---|---|---|---|
| `METALS_DEV_API_KEY` | 1 | metals.dev — free signup | 100 requests/month |
| `GOLDAPI_IO_KEY` | 1 | goldapi.io — free signup | 100 requests/month |
| `AWS_ACCESS_KEY_ID` | 1 | AWS IAM console | IAM user credentials |
| `AWS_SECRET_ACCESS_KEY` | 1 | AWS IAM console | IAM user credentials |
| `AWS_REGION` | 1 | — | Always `ap-south-1` |
| `S3_BUCKET_NAME` | 1 | Created during infra setup | — |
| `SNS_TOPIC_ARN` | 1 | Created during infra setup | — |
| `DEVELOPER_EMAIL` | 1 | Your email | Receives failure alerts |
| `WHATSAPP_TOKEN` | 2 | Meta developer console | WhatsApp Business API |
| `WHATSAPP_PHONE_NUMBER_ID` | 2 | Meta developer console | — |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | 2 | Meta developer console | — |
| `WHATSAPP_VERIFY_TOKEN` | 2 | You create this | Webhook verification |
| `ANTHROPIC_API_KEY` | 2 | console.anthropic.com | Claude API |
| `GOOGLE_PLACES_API_KEY` | 3 | console.cloud.google.com | Nearby jeweller search |
| `METALS_API_COM_KEY` | 4 | metals-api.com | Paid — $4.99/month |
| `IBJA_API_KEY` | 4 | Email nagaraj.iyer@ibja.in | Paid — RBI approved |

---

## Key Decisions

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
| AWS Region | ap-south-1 Mumbai | Indian IP, lowest latency to Indian servers |
| Metals list | Gold, Silver, Platinum, Copper, Diamond | Copper added for Indian festival context |
| Yahoo Finance | Dropped | No clean REST API — Python library only |
| MetalpriceAPI.com | Dropped | Free tier = 24hr delay — not suitable |
| Metals-API.com | Phase 4 only | Paid only — add when revenue starts |
| APMEX.com | Dropped | US retail only — no API — not India relevant |
| Price ranges | Stored in metals.json | Not hardcoded — change without code edits |
| Karat prices | Calculate from purity if not provided | Works for all sources automatically |
| INR conversion | Stored from Metals.Dev | Single source of truth for exchange rate |
| Timestamp formats | Normalised to ISO 8601 UTC | Consistent across all sources |
| GoldAPI.io schedule | Twice daily | Stay within 100/month free limit |
| Metals.Dev schedule | Twice daily | Stay within 100/month free limit |
| Python interpreter | venv | Isolated from system Python |

---

*Last updated: Session 4 — Scraper engine complete (base_scraper, api_fetcher, html_scraper, data_normaliser)*
*This README is updated at the end of every working session*

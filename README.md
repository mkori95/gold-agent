# Gold Agent

> A personal gold buying advisor that lives in WhatsApp — tells you the right time to buy gold, silver and platinum — in your language, for your city, before every festival.

A WhatsApp chatbot that tells Indian families the current gold, silver, and platinum prices — in their language, for their city — and notifies them when a price crosses a threshold they've set.

No app to download. No account creation. Phone number is identity. Users chat naturally in Hindi, Tamil, Telugu, or English.

---

## Why This Exists

Indian housewives check gold prices by calling their jeweller — a source with an obvious conflict of interest — or by asking their husband. No app or service serves this audience in Hindi, Tamil, or Telugu. WhatsApp is already on every phone in India. The India-specific angle (city-wise INR rates, IBJA benchmark, festival calendar, MCX prices) is something general AI models cannot replicate reliably.

**The gap this fills:**

| What exists today | What's missing |
|---|---|
| Jeweller quotes — biased, verbal, no record | Neutral, verified daily price |
| English-only finance apps | Hindi, Tamil, Telugu — first class |
| International spot price (USD/troy oz) | Indian retail price per gram for your city |
| Reactive — check when you remember | Proactive — alert when price hits your target |
| No memory between queries | Conversational — follows up, remembers context |

---

## What Users Can Do

| Message | Language | What happens |
|---|---|---|
| "What is gold price today?" | English | Live 22K/24K per-gram price for their city |
| "सोने का भाव क्या है?" | Hindi | Same, replied in Hindi |
| "தங்கம் விலை என்ன?" | Tamil | Same, replied in Tamil |
| "బంగారం ధర ఎంత?" | Telugu | Same, replied in Telugu |
| Voice note (any language) | Any | Transcribed with Whisper, answered same as text |
| "How much gold for ₹50,000?" | Any | Calculator with live price |
| "Alert me when gold drops below ₹14,000" | Any | Alert saved — WhatsApp notification fires when threshold crossed |
| "சோன ₹14,000 கீழே போனா சொல்லு" | Tamil | Same, from Tamil message |
| "Show my alerts" | Any | Lists all active alerts |
| "Remove my gold alert" | Any | Deactivates the alert |
| "Should I buy before Dhanteras?" | Any | Festival context with today's price |
| "Is gold rising or falling?" | Any | Trend explanation from today's data |

---

## Metals Covered

| Metal | Live Price | City Rates | Notes |
|---|---|---|---|
| Gold | ✅ | ✅ 71 Indian cities | Primary — 22K and 24K per gram |
| Silver | ✅ | ✅ 71 Indian cities | Widely bought at Dhanteras |
| Platinum | ✅ | — | Growing interest in India |
| Copper | ✅ | — | Festival buying — vessels, idols |

---

## Languages

Auto-detected from the user's first message. No language selection step. If detection fails, defaults to English.

| Language | Script detection |
|---|---|
| Hindi | Devanagari Unicode range |
| Tamil | Tamil Unicode range |
| Telugu | Telugu Unicode range |
| English | Default fallback |

---

## Why a Backend Exists

This is the first question worth answering, because the obvious shortcut — just ask Claude — doesn't work here.

General AI models (Claude, ChatGPT, Gemini) know gold prices from their training data. That data is months old. Gold prices move daily by hundreds of rupees per gram. More importantly, the price a buyer pays in Chennai is not the international spot price — it is the spot price converted at today's USD/INR rate, adjusted for purity, plus 3% GST, plus import duty, plus city-level variation. A model that uses training knowledge returns a plausible-sounding number that is structurally wrong.

The backend solves three things the model cannot:

1. **Fresh Indian retail prices** — a scraper pipeline runs daily, collects from 4 sources, calculates a consensus, and writes city-wise gram prices to DynamoDB. Claude reads from this — it never reads from training knowledge for prices.

2. **Context injection** — the agent-brain Lambda builds a structured price block from DynamoDB and injects it into Claude's system prompt. The prompt explicitly says: *"Use ONLY the numbers below. Never use your training knowledge for prices — it is outdated and incorrect for Indian markets."* If the DynamoDB row is ever unavailable, the system prompt says so and Claude says "live data unavailable" rather than guessing.

3. **Price alerts** — "notify me when gold drops below ₹14,000/gram" requires a scheduled process that reads a stored threshold and compares it to a fresh price. That is not something a chat model can do. It requires DynamoDB rows per user per threshold, and a Lambda running hourly via EventBridge.

---

## How a Message Travels Through the System

```
WhatsApp user sends text message
        ↓
Meta Cloud API → API Gateway (ap-south-1)
        ↓
whatsapp-handler Lambda
  ├── Validates HMAC-SHA256 signature
  ├── Parses message (text or audio)
  ├── Detects language (Unicode range — Hindi/Tamil/Telugu/English)
  ├── Classifies intent (regex — price_query / alert_setup / alert_remove / alert_list / calculator / ...)
  ├── Loads/saves conversation history (DynamoDB — 10-turn window, 30min timeout)
  └── Invokes agent-brain Lambda async (returns 200 to Meta immediately)
        ↓
agent-brain Lambda
  ├── alert_setup  → conversation/alert_setup.py (Claude extracts params → writes DynamoDB → confirms)
  ├── alert_remove → conversation/alert_manager.py (deactivates row → confirms)
  ├── alert_list   → conversation/alert_manager.py (reads rows → formats list)
  └── everything else → Claude (Sonnet 4.6) with live price context
        ↓
Claude response → whatsapp_client → Meta Cloud API → WhatsApp user


WhatsApp user sends voice note
        ↓
whatsapp-handler Lambda
  ├── Detects audio message type
  ├── Downloads OGG from Meta Graph API (two-step: GET media_id → GET URL with Bearer token)
  ├── Uploads to S3: gold-agent-prices/voice-temp/{message_id}.ogg
  └── Invokes whisper-transcriber Lambda async (returns 200 to Meta immediately)
        ↓
whisper-transcriber Lambda (container image, 3008MB)
  ├── Downloads OGG from S3
  ├── Transcribes with Whisper base model (pre-baked in image)
  ├── Deletes OGG from S3 immediately after transcription
  └── Invokes agent-brain async with transcript as text
        ↓
agent-brain Lambda → Claude → WhatsApp reply (same path as text)
```

Separately, running on EventBridge:
```
alert-checker Lambda (hourly)
  ├── Scans all active alert rows in DynamoDB
  ├── Compares threshold against today's per-gram price
  ├── 12-hour cooldown per user per alert (prevents spam on fluctuating prices)
  └── Fires WhatsApp notification if threshold breached

consolidator Lambda (daily, 6AM IST)
  ├── Runs 4 scrapers in parallel (gold_api_com, metals_dev, goldapi_io, rapid_api_gold_silver)
  ├── Anomaly detection → trimmed mean consensus per metal
  ├── Averages Indian city 22K prices for correct retail INR values
  └── Writes to DynamoDB gold-agent-live-prices + S3
```

---

## AI Integration

Claude is the conversational layer, not the data source.

**Model selection:**
- All chat intents use `claude-sonnet-4-6`. Haiku 4.5 was tested on price queries and returned ₹895/gram instead of ₹14,558/gram — it does not reliably follow context-grounded instructions when the system prompt contains Indian number formatting (₹4,29,897 lakhs notation). Haiku is used only in `alert_setup.py` for pure JSON extraction (no price data in context).
- `_HAIKU_INTENTS` in `claude_client.py` is an empty set. Only add an intent there if it has zero live price data in context.

**Context injection:**
`context_builder.py` builds a structured block from DynamoDB every time agent-brain is invoked:
```
Price snapshot date: 2026-05-22

=== GOLD ===
  Price (USD/troy oz): $3,287.00
  22K gold per gram (INR): ₹14,558
  24K gold per gram (INR): ₹15,876
  Indian city rates (22K per 10g):
    Chennai: ₹1,45,580
    Mumbai:  ₹1,45,100
    ...
  Confidence: high (3 sources)
```

This block is injected into Claude's system prompt under the header `## Live price data`. The prompt explicitly forbids using training knowledge for any price or rate. If DynamoDB returns nothing, the block says `"Live price data is currently unavailable."` — Claude responds accordingly rather than filling in a number.

**Price caching:**
`context_builder.py` has a module-level 1-hour TTL cache. Warm Lambda containers skip the DynamoDB scan entirely. Cold starts always fetch fresh data. Prices update once daily — 1 hour is a safe window.

**Prompt caching:**
The system prompt is sent with `"cache_control": {"type": "ephemeral"}`. Anthropic caches it for 5 minutes — reduces token cost on back-to-back messages from the same user within a session.

---

## Daily Price Summary

Users can opt in to receive a WhatsApp message every morning at 11:45 AM IST with the day's gold, silver, and platinum prices for their city.

**Opt-in/out:**
- User says "send me daily update" → `summary_subscribe` intent → `daily_summary = true` on their DynamoDB row → confirmation sent
- User says "stop summary" → `summary_unsubscribe` intent → flag cleared → confirmation sent
- Both intents handled directly in `whatsapp-handler` — no Claude call needed

**Schedule:**
- Consolidator runs at 11:15 AM IST (`cron(45 5 * * ? *)`) — after Indian jewellers update prices (10AM-12PM window)
- Daily digest Lambda fires at 11:45 AM IST (`cron(15 6 * * ? *)`) — 30 minutes after fresh data is guaranteed

**Summary content:**
- 24K, 22K, 18K gold per gram for user's city (falls back to national average if city not in data)
- Silver and platinum per gram
- Price change vs yesterday and vs last week, both with explicit dates
- Timestamp of when prices were last updated

**Price diff fallback:**
`s3_reader.py` walks back up to 14 days to find the nearest available S3 snapshot when the exact target date has no data. The actual date used for comparison is always shown in the message — users always know what they're comparing against.

**WhatsApp template:**
The daily summary is sent as a regular message (not a template) because users opted in via WhatsApp — this keeps the 24-hour window open. The message ends with an unsubscribe instruction.

---

## Alert System Design

Three operations: set, list, remove.

**Setting an alert:**
1. `intent_classifier.py` routes to `alert_setup` before regex can match `alert_remove` (order matters in the classifier)
2. `alert_setup.py` calls Claude (Haiku) to extract: `{ "metal": "gold", "direction": "below", "threshold_inr": 14000, "karat": "22K" }`
3. If extraction succeeds → `put_alert()` writes to DynamoDB → confirmation sent to user
4. If extraction fails → clarification message sent, no write attempted, no false confirmation

Confirmation is sent *after* the DynamoDB write succeeds. The system never claims to have set an alert it didn't actually write.

**Alert table key schema:**
`gold-agent-alert-preferences` uses a composite key: `phone_number` (HASH) + `alert_id` (RANGE). The `alert_id` is computed as `{phone}#{metal}#{direction}` — one active alert per metal per direction per user.

This was wrong initially — the table was created with only `alert_id` as partition key. `put_item` silently succeeded (it only requires the partition key to be in the item). `get_user_alerts` (query by phone_number) and `deactivate_alert` (update_item with composite key) both failed with DynamoDB exceptions. Table was deleted and recreated with the correct schema.

**Checking thresholds:**
`alert-checker` Lambda runs hourly. It reads `price_22k_inr` from the live-prices table (the Indian retail per-gram price, not international spot). 12-hour cooldown prevents repeated notifications when a price oscillates near a threshold.

---

## Data Pipeline

**Why Indian retail prices differ from international spot:**

International spot (USD/troy oz) → convert to INR at today's USD/INR rate → divide by 31.1 grams per troy oz → apply purity ratio → this gives the London equivalent per gram. It is not what a buyer pays.

Indian retail = London equivalent + import duty (~15%) + 3% GST + city-level variation + making charges.

The RapidAPI gold-silver-rates-india source provides actual retail prices from 71 Indian cities. The consolidator averages these into `price_22k_inr` and `price_24k_inr` fields in DynamoDB. These are what the agent reads and shows users.

`price_inr` (international spot converted) is also stored but is never shown to users.

**Source reliability:**

| Source | Type | Metals | Limit | Schedule | Status |
|---|---|---|---|---|---|
| gold_api_com | API | Gold, Silver, Platinum, Copper | Unlimited | Hourly | ✅ Active |
| metals_dev | API | All + MCX/IBJA/LBMA | 100/month | Twice daily | ✅ Active |
| goldapi_io | API | Gold, Silver, Platinum | 100/month | Twice daily | ✅ Active |
| rapid_api_gold_silver | API | Gold, Silver — 77 locations | 550k/month | Daily | ✅ Active |
| goodreturns | Scraper | Gold city rates | Unlimited | — | ❌ Disabled |
| moneycontrol | Scraper | MCX gold/silver | Unlimited | — | ❌ Disabled |
| rapaport | Scraper | Diamond | — | — | ❌ Disabled |

Consensus algorithm: collect all sources, anomaly-detect against metals.json price ranges, trimmed mean on validated sources. Spread > 2% gets flagged in the snapshot. Raw source prices always preserved in the snapshot.

### 1. Gold-API.com

No auth, unlimited. The primary spot price source — runs every hour.

```
GET https://api.gold-api.com/price/{symbol}
Symbols: XAU (Gold) · XAG (Silver) · XPT (Platinum) · HG (Copper)
```

```json
{
    "name": "Gold",
    "price": 3287.60,
    "symbol": "XAU",
    "updatedAt": "2026-05-22T06:30:00Z"
}
```

`price` is USD per troy ounce.

---

### 2. Metals.Dev

Auth: `?api_key=KEY` query param. 100 requests/month — scheduled twice daily to stay within 60/month.

This is the **single source of truth for USD/INR exchange rate**. All other sources use the rate extracted from this response. If Metals.Dev fails, `price_inr` is null across the entire snapshot — the system never guesses exchange rates.

```
GET https://api.metals.dev/v1/latest?api_key={key}&currency=USD&unit=toz
```

Key fields used:

| Field | What it gives |
|---|---|
| `metals.gold/silver/platinum/copper` | USD spot per troy oz |
| `metals.mcx_gold`, `mcx_gold_am`, `mcx_gold_pm` | MCX India gold prices |
| `metals.ibja_gold` | IBJA benchmark (used by Indian banks) |
| `metals.lbma_gold_am/pm` | London morning/evening fix |
| `currencies.INR` | Value of 1 INR in USD — e.g. `0.01100` |

**INR conversion formula:**
```
currencies.INR = 0.01100  →  1 INR = 0.011 USD
usd_to_inr = 1 / 0.01100 = 90.91
price_inr  = price_usd / currencies.INR
```

Copper comes from Metals.Dev as USD per pound → converted: `price_per_toz = price_per_lb / 0.0685714`

---

### 3. GoldAPI.io

Auth: `x-access-token: KEY` header. 100 requests/month — scheduled twice daily. Covers Gold, Silver, Platinum (no Copper).

```
GET https://www.goldapi.io/api/{symbol}/USD
Symbols: XAU · XAG · XPT
```

**Unique value:** provides karat-wise gram prices directly — no other active source does this.

```json
{
    "price": 3287.00,
    "price_gram_24k": 105.70,
    "price_gram_22k":  96.89,
    "price_gram_18k":  79.28,
    "ch":  12.50,
    "chp":  0.38
}
```

Karat prices come in USD per gram. They are used as-is by the consolidator — no purity-ratio calculation needed when this source is available.

---

### 4. RapidAPI — Gold Silver Rates India

Auth: `x-rapidapi-key` + `x-rapidapi-host` headers. $1.50/month for 550k requests.

**This is the source of correct Indian retail prices.** Returns per-city rates that already include import duty and GST — not derivable from international spot.

```
GET https://gold-silver-live-prices.p.rapidapi.com/getGoldRate?place={city}
GET https://gold-silver-live-prices.p.rapidapi.com/getSilverRate?place={city}
```

- Gold: per 10g in INR → `unit = "gram_10"` → routed to `city_rates{}` in the snapshot
- Silver: per kg in INR → `unit = "kg"` → routed to `city_rates{}`
- Prices come as comma-formatted strings — strip commas, parse to float
- Dubai silver returns 0 — scraper skips it (known upstream data issue)
- Neither unit enters the trimmed mean — city rates are stored separately

**77 locations:** 71 Indian cities + 6 international (US, UK, Australia, Dubai, Saudi Arabia, Singapore).

The consolidator averages the Indian city 22K rates (excluding international locations) into `price_22k_inr` per gram and stores it in DynamoDB. This is what users see.

---

### 5. GoodReturns.in (Disabled)

Was the original Indian city price source. HTML scraper using `curl_cffi` with `impersonate="chrome120"` to bypass Cloudflare TLS fingerprinting. Works perfectly locally.

**Disabled reason:** AWS Lambda IP addresses are blocked at Cloudflare's IP reputation layer — not the TLS layer. `curl_cffi` bypasses TLS fingerprinting but can't bypass IP bans. Returns 403 from Lambda regardless of browser impersonation.

Replaced by RapidAPI. Code is kept in case IP situation changes.

---

### Disabled Sources

| Source | Reason |
|---|---|
| goodreturns | AWS Lambda IPs blocked by Cloudflare IP reputation — not TLS |
| moneycontrol | MCX gold/silver data already comes from Metals.Dev `extra{}` — duplicate |
| rapaport | Paywalled — no public data available to scrape |
| free_gold_api | Returns full dataset from 1258 AD with no date filter — not suitable for live prices |

---

### Future Sources (Phase 4)

| Source | Cost | What it adds |
|---|---|---|
| Metals-API.com | $4.99/month | Indian city prices as a clean API — would replace RapidAPI |
| IBJA Official API | Contact pricing | RBI-approved benchmark used by HDFC, ICICI, Muthoot — most authoritative India source |

---

## Deployed Lambdas

| Lambda | Status | Trigger | Runtime | What it does |
|---|---|---|---|---|
| `gold-agent-consolidator` | ✅ Live | EventBridge daily 11:15AM IST | python3.12 zip | Scrapes prices, writes DynamoDB + S3 |
| `gold-agent-whatsapp-handler` | ✅ Live | API Gateway POST /webhook | python3.12 zip | Receives Meta webhook, classifies intent, invokes agent-brain |
| `gold-agent-brain` | ✅ Live | Invoked by whatsapp-handler | python3.12 zip | Calls Claude with price context, handles alert writes |
| `gold-agent-alert-checker` | ✅ Live | EventBridge hourly | python3.12 zip | Checks thresholds, sends WhatsApp notifications |
| `gold-agent-daily-digest` | ✅ Live | EventBridge 11:45AM IST | python3.12 zip | Sends morning price summary to opted-in subscribers |
| `gold-agent-whisper-transcriber` | ✅ Live | Invoked by whatsapp-handler | Container image (ECR) | Transcribes WhatsApp voice notes using Whisper base model |
| `gold-agent-scraper` | Code ready, not deployed | EventBridge | — | Orchestrates scrapers with circuit breaker + quota management |
| `gold-agent-festival-advisory` | Code ready, not deployed | EventBridge | — | Proactive pre-festival WhatsApp messages |
| `gold-agent-weekly-digest` | Code ready, not deployed | EventBridge weekly | — | Weekly price summary per user |

---

## Project Structure

```
gold-agent/
├── config/
│   ├── sources.json          ← scraper config — type, schedule, auth, rate limits, fallback sources
│   ├── metals.json           ← metal definitions, purity ratios, price sanity ranges
│   ├── festivals.json        ← Indian festival calendar
│   ├── cities.json           ← supported Indian cities
│   ├── alerts.json           ← default alert thresholds
│   ├── badges.json           ← gamification badge definitions
│   └── languages.json        ← supported languages and detection patterns
├── src/
│   ├── scrapers/
│   │   ├── engine/
│   │   │   ├── base_scraper.py       ← abstract base, run(), build_result(), is_valid_price()
│   │   │   ├── api_fetcher.py        ← HTTP + auth handling (none / header / query_param)
│   │   │   ├── html_scraper.py       ← curl_cffi with Chrome impersonation (Cloudflare bypass)
│   │   │   ├── data_normaliser.py    ← normalises timestamps, units, INR conversion, karat prices
│   │   │   ├── rate_limiter.py       ← monthly quota tracking
│   │   │   ├── response_parser.py    ← JSON/HTML parsing helpers
│   │   │   └── secrets_manager.py    ← fetches API keys from AWS Secrets Manager
│   │   └── sites/
│   │       ├── gold_api_com.py       ← 4 metals, unlimited, no auth
│   │       ├── metals_dev.py         ← 4 metals + MCX/IBJA/LBMA, provides USD/INR rate
│   │       ├── goldapi_io.py         ← 3 metals + karat-wise gram prices
│   │       ├── rapid_api_gold_silver.py  ← 71 Indian + 6 international city rates
│   │       ├── goodreturns.py        ← disabled (AWS IPs blocked by Cloudflare)
│   │       ├── moneycontrol.py       ← disabled (MCX data already in metals_dev)
│   │       ├── rapaport.py           ← disabled (paywalled)
│   │       └── free_gold_api.py      ← disabled (no date filtering — full 768yr dataset)
│   ├── lambdas/
│   │   ├── consolidator/             ← Phase 1 ✅ deployed
│   │   │   ├── handler.py
│   │   │   ├── consolidator.py       ← pipeline orchestrator
│   │   │   ├── merger.py             ← anomaly detection + trimmed mean + city rate routing
│   │   │   ├── trimmed_mean.py
│   │   │   ├── anomaly_detector.py
│   │   │   ├── validator.py
│   │   │   ├── dynamo_writer.py      ← writes price_22k_inr/price_24k_inr from city averages
│   │   │   └── s3_writer.py
│   │   ├── whatsapp-handler/         ← Phase 2 ✅ deployed
│   │   │   ├── handler.py            ← GET (verify) + POST (messages + audio), async invoke
│   │   │   ├── signature_validator.py
│   │   │   ├── message_parser.py     ← parses text + audio message types
│   │   │   ├── language_detector.py  ← Unicode range detection
│   │   │   ├── intent_classifier.py  ← regex routing (alert_remove before alert_setup — order matters)
│   │   │   ├── session_manager.py    ← 10-turn history, 30min timeout
│   │   │   ├── user_manager.py
│   │   │   ├── response_formatter.py
│   │   │   ├── response_sender.py
│   │   │   ├── template_sender.py
│   │   │   └── window_checker.py     ← WhatsApp 24-hour window enforcement
│   │   ├── whisper-transcriber/      ← Enhancement 2 ✅ deployed (container image)
│   │   │   ├── handler.py            ← standalone — no shared imports, Whisper + S3 + invoke
│   │   │   └── Dockerfile            ← CPU torch + imageio-ffmpeg (bundled ffmpeg binary)
│   │   ├── agent-brain/              ← Phase 2 ✅ deployed
│   │   │   ├── handler.py            ← routes alert_* to conversation/, rest to Claude
│   │   │   ├── claude_client.py      ← model selection, prompt caching, token logging
│   │   │   ├── context_builder.py    ← DynamoDB → structured price block, 1hr in-memory cache
│   │   │   ├── prompt_builder.py     ← system prompt with explicit CAN/CANNOT list
│   │   │   ├── language_handler.py
│   │   │   ├── market_analyser.py
│   │   │   ├── summary_writer.py
│   │   │   └── trend_detector.py
│   │   ├── conversation/             ← Phase 2 ✅ deployed
│   │   │   ├── alert_setup.py        ← Haiku extracts params → DynamoDB write → confirmation
│   │   │   ├── alert_manager.py      ← alert_list and alert_remove handlers
│   │   │   ├── calculator.py
│   │   │   ├── festival_advisor.py
│   │   │   ├── price_query.py
│   │   │   ├── trend_explainer.py
│   │   │   ├── comparison.py
│   │   │   ├── education.py
│   │   │   └── handler.py
│   │   ├── alert-checker/            ← Phase 2 ✅ deployed
│   │   │   ├── handler.py
│   │   │   ├── threshold_checker.py  ← uses price_22k_inr (Indian retail), not spot
│   │   │   ├── cooldown_manager.py   ← 12-hour cooldown per user per alert
│   │   │   ├── alert_formatter.py    ← 4-language alert messages
│   │   │   └── alert_trigger.py
│   │   ├── scraper/                  ← Phase 1 code, not yet deployed as Lambda
│   │   │   ├── handler.py
│   │   │   ├── circuit_breaker.py
│   │   │   ├── health_tracker.py
│   │   │   ├── notifier.py
│   │   │   ├── parallel_runner.py
│   │   │   ├── quota_manager.py
│   │   │   ├── scheduler.py
│   │   │   └── source_selector.py
│   │   ├── festival-advisory/        ← Phase 2 code, not yet deployed
│   │   ├── weekly-digest/            ← Phase 2 code, not yet deployed
│   │   ├── rate-validator/           ← Phase 3 — community rate guardrails (6 checks)
│   │   ├── gamification/             ← Phase 3 — badge engine, streak tracker, leaderboard
│   │   ├── location/                 ← Phase 3 — Google Places jeweller search
│   │   ├── data-api/                 ← Phase 4 — REST API for web dashboard
│   │   ├── report/                   ← Phase 4 — PDF report generation
│   │   └── web-chat/                 ← Phase 4 — web chat interface
│   └── shared/
│       ├── db/
│       │   ├── dynamo_client.py
│       │   ├── dynamo_reader.py      ← get_latest_snapshot (scan per-metal rows), get_user_alerts
│       │   ├── dynamo_writer.py      ← put_alert, deactivate_alert, put_conversation_turn
│       │   ├── s3_client.py
│       │   ├── s3_reader.py
│       │   └── s3_writer.py
│       ├── models/
│       │   ├── user.py
│       │   ├── price.py              ← PriceSnapshot.from_dynamo_rows() reads price_22k_inr directly
│       │   ├── alert.py              ← alert_id = f"{phone}#{metal}#{direction}"
│       │   ├── badge.py
│       │   ├── community_rate.py
│       │   ├── jeweller.py
│       │   └── source.py
│       ├── notifications/
│       │   ├── whatsapp_client.py    ← send_text, send_template, mark_read, download_media (urllib, no extra deps)
│       │   ├── ses_client.py
│       │   ├── sns_client.py
│       │   └── notification_formatter.py
│       └── utils/
│           ├── logger.py
│           ├── currency_formatter.py
│           ├── date_helper.py
│           ├── config_loader.py
│           ├── error_handler.py
│           └── metal_helper.py
├── tests/
│   ├── unit/
│   │   ├── lambdas/                  ← 134 tests passing (pytest), 41 skipped (live API)
│   │   ├── scrapers/
│   │   └── shared/
│   └── integration/
├── infra/
│   ├── template.yaml                 ← SAM — Lambdas + API Gateway + EventBridge
│   ├── dynamodb/                     ← table definitions
│   ├── iam/                          ← role and policy definitions
│   ├── lambda/                       ← Lambda config
│   ├── api-gateway/
│   ├── eventbridge/
│   ├── s3/ sns/ ses/ cloudwatch/ vpc/ secrets/
│   └── terraform/                    ← infra state backend (S3)
├── scripts/
├── docs/
├── .env                              ← real API keys — never commit
├── .env.example
├── requirements.txt
├── requirements-all.txt
├── template.yml                      ← SAM template (deployed)
├── conftest.py
└── context.md                        ← living session context — read at start of every session
```

---

## DynamoDB Tables

| Table | Key Schema | Purpose |
|---|---|---|
| `gold-agent-live-prices` | `metal` (HASH) | One row per metal — current consensus price, city rates, confidence |
| `gold-agent-source-health` | `source_id` (HASH) | Circuit breaker state per scraper source |
| `gold-agent-quota-tracker` | `source_id` (HASH) | Monthly API call counts |
| `gold-agent-users` | `phone_number` (HASH) | User profile — language, city, joined date |
| `gold-agent-alert-preferences` | `phone_number` (HASH) + `alert_id` (RANGE) | Active price alerts per user |
| `gold-agent-conversation-history` | `phone_number` (HASH) + `timestamp` (RANGE) | Last 10 turns per user |

`alert_id` format: `{phone_number}#{metal}#{direction}` — enforces one active alert per metal per direction per user.

The live-prices table stores one row per metal (not one row per date). `get_latest_snapshot()` scans all rows and builds a `PriceSnapshot` object. `price_22k_inr` and `price_24k_inr` are Indian city averages written by the consolidator — these are the correct retail prices used by the agent and the alert checker.

---

## Infrastructure

- **Region:** ap-south-1 (Mumbai). Lambda runs with an Indian IP — GoodReturns and Moneycontrol serve Indian prices naturally, and latency to Indian financial APIs is 20-50ms vs 180-230ms from US regions.
- **Deployment:** AWS SAM. `sam build && sam deploy --region ap-south-1 --no-confirm-changeset`
- **IAM:** `gold-agent-phase2-role` — execution role for all Phase 2 Lambdas. `boto3` is not in `requirements.txt` — the Lambda runtime provides it.
- **Secrets:** All API keys in AWS Secrets Manager (`gold-agent/whatsapp`, `gold-agent/anthropic`). Locally, from `.env` via `load_dotenv()`.
- **SAM build note:** Delete `infra/terraform/.terraform/` before `sam build` if it exists — it's 692MB and will exceed the 262MB Lambda size limit.

---

## Environment Variables

| Variable | Used by | Source |
|---|---|---|
| `ANTHROPIC_API_KEY` | agent-brain | Secrets Manager: `gold-agent/anthropic` |
| `WHATSAPP_TOKEN` | whatsapp-handler, whatsapp_client | Secrets Manager: `gold-agent/whatsapp` |
| `WHATSAPP_PHONE_NUMBER_ID` | whatsapp_client | Secrets Manager: `gold-agent/whatsapp` |
| `WHATSAPP_VERIFY_TOKEN` | whatsapp-handler | Secrets Manager: `gold-agent/whatsapp` |
| `METALS_DEV_API_KEY` | metals_dev scraper | Secrets Manager |
| `GOLDAPI_IO_KEY` | goldapi_io scraper | Secrets Manager |
| `RAPIDAPI_KEY` | rapid_api_gold_silver | Secrets Manager |
| `AWS_REGION` | all Lambdas | Always `ap-south-1` |
| `GOOGLE_PLACES_API_KEY` | location Lambda (Phase 3) | — |

---

## Key Design Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| AI model for chat | Sonnet 4.6 (all intents) | Haiku 4.5 fails on price data — returns ₹895/gram vs actual ₹14,558/gram. Indian number formatting (₹4,29,897 lakhs notation) breaks its context-following. |
| AI model for extraction | Haiku 4.5 (alert_setup only) | Pure JSON extraction with no price data in context — Haiku is safe here and cheaper. |
| Price shown to users | `price_22k_inr` from DynamoDB | Indian retail price (includes import duty, GST, city variation). International spot converted to INR is ~35% lower and wrong. |
| DynamoDB price cache | 1-hour module-level TTL | Prices refresh daily. Warm Lambda containers skip DynamoDB entirely. Safe and cheap. |
| Alert confirmation timing | After DynamoDB write | Never confirm before the write succeeds. Learned from Phase 2 Issue 1 — Claude was replying "I've set your alert" with nothing written. |
| Alert table key | Composite: phone_number + alert_id | phone_number alone prevents querying by user; alert_id alone prevents querying user's alerts. Both are needed. Table was recreated after initial wrong schema. |
| Intent classifier order | alert_remove / alert_list before alert_setup | "remove my gold alert" contains "alert" — if alert_setup matched first, it would try to set a new alert instead of removing one. |
| Unknown intent routing | Goes to agent-brain | Often a follow-up to a prior message. A static fallback breaks multi-turn conversations. |
| Session timeout | 30 minutes | Stale history confuses Claude — it tries to continue a conversation from hours ago. |
| Context injection | Explicit structured block in system prompt | Claude's training prices are months old and use wrong unit (USD/troy oz). Explicit injection with "use ONLY these numbers" is the only reliable approach. |
| WhatsApp client | urllib (no requests library) | Reduces Lambda package size. The WhatsApp API calls are simple POSTs. |
| AWS region | ap-south-1 Mumbai | Indian IP address — financial sites serve Indian content naturally. Cloudflare also has lower suspicion of Mumbai IPs than us-east-1. |
| INR conversion source | Metals.Dev only | Single source of truth for USD/INR rate. Other sources use this shared rate via DataNormaliser. |
| Scraper fallback logic | Config-driven in sources.json | Circuit breaker state and fallback sources defined in config — no code changes to switch sources. |

---

## Local Setup

```bash
git clone git@github.com:mkori95/gold-agent.git
cd gold-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
# fill in .env with real API keys
```

Run tests:
```bash
pytest tests/unit/
```

Trigger consolidator manually (refreshes DynamoDB prices):
```bash
aws lambda invoke --function-name gold-agent-consolidator --region ap-south-1 --payload '{}' /tmp/out.json
```

Deploy (zip Lambdas only):
```bash
sam build && sam deploy --region ap-south-1 --no-confirm-changeset --resolve-image-repos
```

Deploy including Whisper container image (first time or after Dockerfile change):
```bash
./deploy_whisper.sh
```

---

## Phase Status

| Phase | What | Status |
|---|---|---|
| Phase 1 | Automated price pipeline — 4 scrapers, consensus, DynamoDB + S3 | ✅ Live |
| Phase 2 | WhatsApp chatbot — prices, alerts (set/list/remove), 4 languages | ✅ Live (2026-05-22) |
| Enhancement 2 | Voice note support — Whisper base model transcription via ECR container Lambda | ✅ Live (2026-05-22) |
| Phase 3 | Crowdsourced jeweller rates, location search, gamification | Code scaffolded, not deployed |
| Phase 4 | Web dashboard, PDF reports, paid API access | Code scaffolded, not deployed |

*Last updated: 2026-05-22*

# Price Consensus Logic — Gold Agent

> This document defines how the consolidator calculates a single trusted price
> from multiple data sources. Every decision here is intentional and documented.
> Last updated: Session 9

---

## Why Consensus Matters

We collect gold prices from 3 different API sources simultaneously:
- gold_api_com
- metals_dev
- goldapi_io

Each source may return a slightly different price due to feed timing, rounding,
or data provider differences. The consolidator's job is to produce one trusted
price from all of them — and to know when to trust it and when to be suspicious.

---

## Step-by-Step Consensus Calculation

```
Step 1 → Collect all prices for a metal from all active sources
Step 2 → Run anomaly detection — reject any price outside metals.json range
Step 3 → Count only sources that PASSED validation (not total sources run)
Step 4 → Apply the right calculation based on validated source count
Step 5 → Calculate spread across all validated prices
Step 6 → Assign confidence level
Step 7 → Store everything — consensus price + all individual prices preserved
```

---

## Calculation Rules by Source Count

Source count = number of sources that **passed anomaly detection**, not total sources run.

```
0 sources → No data — alert developer
            confidence: "unavailable"

1 source  → Use price as-is — flag clearly
            confidence: "low"

2 sources → Simple average of both prices
            confidence: "medium"

3+ sources → Drop the single highest price
             Drop the single lowest price
             Average the remaining prices
             confidence: "high"
```

### Why Always Trim for 3+ (Not Just 4+)

Previous versions of this logic used median for exactly 3 sources and trimmed
mean for 4+. We simplified to a single rule: always trim highest and lowest for
3+ sources.

For 3 sources, trimming highest + lowest leaves 1 price — which is just the
median. The math is the same. But having one consistent rule is simpler to
reason about, test, and maintain.

### Why Count Validated Sources Not Total Sources

If 3 sources run but anomaly detection rejects one price as out of range, you
effectively have 2 trusted data points — not 3. Counting total sources would
give you a false "high" confidence when you only have "medium" quality data.

---

## Anomaly Detection

Before any price enters the consensus calculation, it must pass a range check
against `config/metals.json`.

```
Gold:     min $500    max $15,000
Silver:   min $5      max $500
Platinum: min $200    max $10,000
Copper:   min $0.05   max $50
```

If a price falls outside these bounds:
- Reject it from the consensus calculation
- Log a warning with source name and price
- Do NOT crash — other sources continue normally

These ranges are intentionally wide — they catch obviously broken data
(e.g. gold at $50 or $99,999) without false positives during normal volatility.

---

## Spread Monitoring

After calculating the consensus price, we measure how far apart the sources were.

```
spread_percent = (max_price - min_price) / consensus_price × 100
```

### Thresholds

```
spread < 1%   → Normal — sources agree closely
spread 1-2%   → Log warning — sources diverging slightly
spread > 2%   → Log warning + flag in snapshot — something unusual happening
```

### Why This Matters

A spread > 2% between reputable sources is a signal that:
- One source may have a stale feed
- Market is moving fast and sources are updating at different times
- One source may have a data quality issue

The snapshot stores `spread_percent` so the agent brain can factor this into
its confidence when answering user questions.

---

## GoodReturns — Excluded From Consensus

GoodReturns is NOT included in the trimmed mean calculation. Here's why:

| Property | API Sources | GoodReturns |
|---|---|---|
| Unit | Troy ounce | Per gram |
| Currency | USD | INR |
| Price type | Spot price | Retail city rate |
| Geography | Global | India-specific |

GoodReturns data feeds directly into `city_rates{}` on the snapshot only.
It is never mixed with USD spot prices in the consensus calculation.

---

## Confidence Levels — What They Mean

| Level | When | What the agent brain should do |
|---|---|---|
| `high` | 3+ validated sources | Quote price confidently |
| `medium` | 2 validated sources | Quote price, mention it's based on 2 sources |
| `low` | 1 validated source | Quote price, flag uncertainty clearly |
| `unavailable` | 0 validated sources | Do not quote — alert developer, tell user data unavailable |

---

## Final Snapshot Structure — Consensus Fields

```json
{
  "metals": {
    "gold": {
      "price_usd": 3101.50,
      "price_inr": 281946.0,
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
      "karats": {
        "24K": { "price_usd": 3101.19, "price_inr": 281918.0 },
        "22K": { "price_usd": 2842.26, "price_inr": 258291.0 },
        "18K": { "price_usd": 2326.13, "price_inr": 211459.0 }
      },
      "city_rates": {
        "mumbai":    { "24K": 9780.0, "22K": 8950.0, "18K": 7340.0 },
        "delhi":     { "24K": 9760.0, "22K": 8930.0, "18K": 7320.0 },
        "chennai":   { "24K": 9790.0, "22K": 8960.0, "18K": 7350.0 }
      },
      "extra": {
        "mcx_gold":      3250.00,
        "ibja_gold":     3210.00,
        "lbma_gold_am":  3088.50,
        "lbma_gold_pm":  3092.75
      }
    }
  }
}
```

---

## INR Conversion — Single Source of Truth

INR conversion uses **Metals.Dev only** as the exchange rate source.

```
Metals.Dev returns: currencies.INR = 0.0110022345
This means:         1 INR = 0.011 USD
Therefore:          1 USD = 1 / 0.011 = ₹90.89

price_inr = price_usd / currencies.INR
```

This rate is extracted by `MetalsDevScraper` and stored as `scraper.inr_rate`.
The consolidator passes it to `DataNormaliser` which applies it to all records.

If Metals.Dev fails and no INR rate is available, `price_inr` is set to `null`
across the entire snapshot. We never guess the exchange rate.

---

## Raw Data Preservation

We never throw away raw source data. Every snapshot stores all individual
source prices in `source_prices{}` alongside the consensus price.

This means:
- We can audit why a particular consensus was reached
- The agent brain can see if sources are diverging
- Historical analysis can compare source accuracy over time
- If our consensus logic improves, we can re-derive prices from raw data

---

## What Gets Stored Where

| Data | Storage | Table/Path |
|---|---|---|
| Latest consensus price | DynamoDB | `live_prices` table |
| Full snapshot with all fields | S3 | `/prices/gold/YYYY/MM/DD/HH:MM.json` |
| Historical queries | Athena | Sits on top of S3 `/prices/` folder |

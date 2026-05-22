# Price Fix Analysis — Indian Market Rates

## Root Cause
The RapidAPI scraper IS running and IS fetching correct Indian market prices.
The consolidator IS routing them correctly. The **dynamo_writer is dropping them** — it never writes `price_22k_inr`, `price_24k_inr`, or `city_rates` to DynamoDB.

So the bot reads only `price_inr` (international spot, per troy oz) and calculates
22K/24K from that — giving wrong/low Indian prices.

## What the API actually returns (verified live)
| City       | 24K / 10g   | 22K / 10g   | 22K / gram |
|------------|-------------|-------------|------------|
| New Delhi  | ₹1,59,850   | ₹1,46,529   | ₹14,653    |
| Mumbai     | ₹1,60,120   | ₹1,46,777   | ₹14,678    |
| Chennai    | ₹1,60,590   | ₹1,47,208   | ₹14,721    |

This is what the bot should show — NOT the international spot conversion (~₹9,000).

## Three Files to Change (tomorrow)

### 1. `src/lambdas/consolidator/dynamo_writer.py` — `_write_metal_record()`
Add to the `item` dict being written:
```python
# Calculate 22K/24K per gram from RapidAPI city averages
city_rates = metal_data.get("city_rates", {})  # {location: {karat: price_per_10g}}

price_22k_inr = None
price_24k_inr = None
if metal == "gold" and city_rates:
    prices_22k = [v.get("22K") for v in city_rates.values() if isinstance(v, dict) and v.get("22K")]
    prices_24k = [v.get("24K") for v in city_rates.values() if isinstance(v, dict) and v.get("24K")]
    if prices_22k:
        price_22k_inr = str(round(sum(prices_22k) / len(prices_22k) / 10, 2))  # per gram
    if prices_24k:
        price_24k_inr = str(round(sum(prices_24k) / len(prices_24k) / 10, 2))  # per gram

# Also store city_rates as a simplified {city: 22K_price_per_10g} map
city_rates_simple = {
    loc: rates.get("22K") for loc, rates in city_rates.items()
    if isinstance(rates, dict) and rates.get("22K")
} if city_rates else {}

# Add to item:
item["price_22k_inr"] = price_22k_inr or ""
item["price_24k_inr"] = price_24k_inr or ""
item["city_rates"]    = city_rates_simple  # DynamoDB stores dicts natively
```

### 2. `src/shared/models/price.py` — `from_dynamo_rows()`
Replace the hardcoded calculation block with:
```python
# Read from DynamoDB directly if available (from RapidAPI city average)
price_22k_inr = float(row["price_22k_inr"]) if row.get("price_22k_inr") else None
price_24k_inr = float(row["price_24k_inr"]) if row.get("price_24k_inr") else None

# Fallback: calculate from international spot (only if RapidAPI data missing)
if metal_id == "gold" and price_inr and not price_22k_inr:
    price_24k_per_gram = price_inr / TROY_OZ_TO_GRAMS
    price_22k_inr = round(price_24k_per_gram * 22 / 24, 2)
    price_24k_inr = round(price_24k_per_gram, 2)

# Read city_rates from DynamoDB
city_rates = row.get("city_rates")  # {city: price_per_10g} or None
```

### 3. No change to `context_builder.py` needed
It already reads `metal.price_22k_inr`, `metal.price_24k_inr`, and `metal.city_rates`.
Just need to make sure `MetalPrice.city_rates` is populated from the row.

## After the fix, bot will show
- 22K gold per gram: ₹14,653 ← correct Indian market price
- City rate (Chennai): ₹1,47,208/10g ← correct city-specific rate
- 24K gold per gram: ₹15,985 ← correct

## Steps to deploy tomorrow
1. Edit dynamo_writer.py (add price_22k_inr, price_24k_inr, city_rates)
2. Edit price.py / from_dynamo_rows() (read from DB first, calculate as fallback)
3. sam build && sam deploy
4. Trigger consolidator manually once to refresh DynamoDB with correct prices:
   aws lambda invoke --function-name gold-agent-consolidator --region ap-south-1 /tmp/out.json
5. Test the bot

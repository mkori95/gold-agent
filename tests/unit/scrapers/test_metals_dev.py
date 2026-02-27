"""
test_metals_dev.py

Test script for the Metals.Dev scraper.

IMPORTANT — Always run this from project root:
    python tests/unit/scrapers/test_metals_dev.py

What this tests:
1. sources.json loads correctly
2. metals_dev config block is found
3. METALS_DEV_API_KEY is set in environment
4. Scraper initialises without errors
5. All 4 metals return a price
6. Copper unit conversion is correct
7. INR rate is extracted correctly
8. MCX and IBJA prices captured for gold
9. MCX prices captured for silver
10. LBMA prices captured correctly
11. All records have correct standard format
"""

from dotenv import load_dotenv
load_dotenv()

import json
import os
import sys
import logging
from src.scrapers.sites.metals_dev import MetalsDevScraper

# ============================================================
# Set up logging so we can see what the scraper is doing
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)

# ============================================================
# Helpers — print pass/fail clearly
# ============================================================
def passed(msg):
    print(f"  ✅  {msg}")

def failed(msg):
    print(f"  ❌  {msg}")
    sys.exit(1)

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ============================================================
# Required fields every price record must have
# ============================================================
REQUIRED_FIELDS = [
    "metal",
    "price_usd",
    "currency",
    "price_inr",
    "unit",
    "source_id",
    "source_name",
    "timestamp"
]

# ============================================================
# TEST 1 — Load sources.json
# ============================================================
section("TEST 1 — Load sources.json")

try:
    with open("config/sources.json", "r") as f:
        sources_data = json.load(f)
    passed("sources.json loaded")
except FileNotFoundError:
    failed("sources.json not found — are you running from project root?")
except json.JSONDecodeError as e:
    failed(f"sources.json is not valid JSON — {e}")

# ============================================================
# TEST 2 — Find metals_dev config
# ============================================================
section("TEST 2 — Find metals_dev config block")

source_config = None
for source in sources_data["sources"]:
    if source["id"] == "metals_dev":
        source_config = source
        break

if source_config:
    passed("metals_dev config found")
    passed(f"Metals in config: {source_config['metals']}")
    passed(f"Enabled: {source_config['enabled']}")
    passed(f"Auth type: {source_config['auth']['type']}")
    passed(f"Auth env key: {source_config['auth']['env_key']}")
else:
    failed("metals_dev not found in sources.json")

# ============================================================
# TEST 3 — Check API key is set
# ============================================================
section("TEST 3 — Check METALS_DEV_API_KEY is set")

api_key = os.environ.get("METALS_DEV_API_KEY")

if api_key:
    passed(f"METALS_DEV_API_KEY found — {api_key[:6]}...")
else:
    failed(
        "METALS_DEV_API_KEY not set — "
        "add it to your .env file"
    )

# ============================================================
# TEST 4 — Initialise the scraper
# ============================================================
section("TEST 4 — Initialise scraper")

try:
    scraper = MetalsDevScraper(source_config)
    passed(f"Scraper initialised — source_id: {scraper.source_id}")
    passed(f"Metals to fetch: {scraper.metals}")
    passed(f"Metals config loaded: {list(scraper.metals_config.keys())}")
    passed(f"Copper conversion factor: {scraper.COPPER_LB_TO_TOZ}")
except Exception as e:
    failed(f"Scraper failed to initialise — {e}")

# ============================================================
# TEST 5 — Run the scraper
# ============================================================
section("TEST 5 — Run scraper (live API call)")

print("\n  Calling Metals.Dev now — this uses 1 of your 100 monthly calls...")
print()

result = scraper.run()

if result["status"] == "success":
    passed(f"Scrape status: {result['status']}")
    passed(f"Records returned: {result['records_count']}")
    passed(f"Duration: {result['duration_seconds']}s")
elif result["status"] == "failed":
    failed(f"Scrape failed — {result['error']}")
else:
    failed(f"Unexpected status: {result['status']}")

# ============================================================
# TEST 6 — Check all 4 metals returned
# ============================================================
section("TEST 6 — Check all 4 metals returned")

metals_returned = [r["metal"] for r in result["data"]]
expected_metals = source_config["metals"]

for metal in expected_metals:
    if metal in metals_returned:
        passed(f"Metal returned: {metal}")
    else:
        failed(f"Metal MISSING: {metal}")

# ============================================================
# TEST 7 — Check INR rate was extracted
# ============================================================
section("TEST 7 — Check INR rate extracted")

if scraper.inr_rate is not None:
    usd_to_inr = round(1 / scraper.inr_rate, 2)
    passed(f"INR rate extracted: {scraper.inr_rate}")
    passed(f"Human readable: 1 USD = ₹{usd_to_inr}")

    if 80 <= usd_to_inr <= 100:
        passed(f"INR rate looks realistic: ₹{usd_to_inr}")
    else:
        failed(
            f"INR rate looks wrong: ₹{usd_to_inr} — "
            f"expected between ₹80 and ₹100"
        )
else:
    failed("INR rate was not extracted — check response")

# ============================================================
# TEST 8 — Check copper unit conversion
# ============================================================
section("TEST 8 — Check copper unit conversion")

copper_record = next(
    (r for r in result["data"] if r["metal"] == "copper"),
    None
)

if copper_record is None:
    failed("Copper record not found in results")

extra = copper_record.get("extra", {})

if "price_per_pound" in extra:
    passed(f"Original per_pound price stored: ${extra['price_per_pound']}")
else:
    failed("price_per_pound missing from copper extra{}")

if "price_per_toz" in extra:
    passed(f"Converted per_toz price stored: ${extra['price_per_toz']}")
else:
    failed("price_per_toz missing from copper extra{}")

if "conversion_factor" in extra:
    passed(f"Conversion factor stored: {extra['conversion_factor']}")
else:
    failed("conversion_factor missing from copper extra{}")

price_lb  = extra.get("price_per_pound")
price_toz = extra.get("price_per_toz")
conversion = extra.get("conversion_factor")

if price_lb and price_toz and conversion:
    expected_toz = round(price_lb / conversion, 6)
    if abs(expected_toz - price_toz) < 0.001:
        passed(
            f"Conversion math correct — "
            f"${price_lb}/lb ÷ {conversion} = ${price_toz}/toz"
        )
    else:
        failed(
            f"Conversion math wrong — "
            f"${price_lb}/lb ÷ {conversion} = ${expected_toz} "
            f"but got ${price_toz}"
        )

top_level_price = copper_record.get("price_usd")
if top_level_price == price_toz:
    passed(f"Top level price_usd is troy ounce price: ${top_level_price}")
else:
    failed(
        f"Top level price_usd should be ${price_toz} (toz) "
        f"but got ${top_level_price}"
    )

# ============================================================
# TEST 9 — Check gold has MCX and IBJA prices
# ============================================================
section("TEST 9 — Check gold MCX and IBJA prices")

gold_record = next(
    (r for r in result["data"] if r["metal"] == "gold"),
    None
)

if gold_record is None:
    failed("Gold record not found in results")

gold_extra = gold_record.get("extra", {})

for field in ["mcx_gold", "mcx_gold_am", "mcx_gold_pm",
              "ibja_gold", "lbma_gold_am", "lbma_gold_pm"]:
    if gold_extra.get(field) is not None:
        passed(f"Gold extra field present: {field} = {gold_extra[field]}")
    else:
        failed(f"Gold extra field MISSING: {field}")

# ============================================================
# TEST 10 — Check silver has MCX prices
# ============================================================
section("TEST 10 — Check silver MCX prices")

silver_record = next(
    (r for r in result["data"] if r["metal"] == "silver"),
    None
)

if silver_record is None:
    failed("Silver record not found in results")

silver_extra = silver_record.get("extra", {})

for field in ["mcx_silver", "mcx_silver_am", "mcx_silver_pm", "lbma_silver"]:
    if silver_extra.get(field) is not None:
        passed(f"Silver extra field present: {field} = {silver_extra[field]}")
    else:
        failed(f"Silver extra field MISSING: {field}")

# ============================================================
# TEST 11 — Validate record format for all metals
# ============================================================
section("TEST 11 — Validate record format for each metal")

for record in result["data"]:
    metal = record["metal"]
    print(f"\n  --- {metal.upper()} ---")

    for field in REQUIRED_FIELDS:
        if field in record:
            passed(f"Field present: {field} = {record[field]}")
        else:
            failed(f"Field MISSING: {field} in {metal} record")

    price = record["price_usd"]
    if isinstance(price, (int, float)) and price > 0:
        passed(f"Price is valid positive number: ${price:,.4f}")
    else:
        failed(f"Price is invalid: {price}")

    if record["source_id"] == "metals_dev":
        passed(f"source_id correct: {record['source_id']}")
    else:
        failed(f"source_id wrong: {record['source_id']}")

    if record["unit"] == "troy_ounce":
        passed(f"Unit correct: {record['unit']}")
    else:
        failed(f"Unit wrong: {record['unit']}")

# ============================================================
# TEST 12 — Print full output for visual inspection
# ============================================================
section("TEST 12 — Full result output")

print()
print(json.dumps(result, indent=2))

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  Metals.Dev scraper is working correctly.")
print(f"  INR rate captured: 1 USD = ₹{round(1 / scraper.inr_rate, 2)}")
print("  Safe to proceed to goldapi_io.py")
print()
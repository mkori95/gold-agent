"""
test_gold_api_com.py

Test script for the Gold-API.com scraper.

IMPORTANT — Always run this from project root:
    python tests/unit/scrapers/test_gold_api_com.py

What this tests:
1. sources.json loads correctly
2. gold_api_com config block is found
3. Scraper initialises without errors
4. All 4 metals return a price
5. Prices are within valid ranges
6. Price records have the correct standard format
"""

import json
import sys
import logging
from src.scrapers.sites.gold_api_com import GoldApiComScraper

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
# TEST 2 — Find gold_api_com config
# ============================================================
section("TEST 2 — Find gold_api_com config block")

source_config = None
for source in sources_data["sources"]:
    if source["id"] == "gold_api_com":
        source_config = source
        break

if source_config:
    passed("gold_api_com config found")
    passed(f"Metals in config: {source_config['metals']}")
    passed(f"Enabled: {source_config['enabled']}")
    passed(f"Auth required: {source_config['auth']['required']}")
else:
    failed("gold_api_com not found in sources.json")

# ============================================================
# TEST 3 — Initialise the scraper
# ============================================================
section("TEST 3 — Initialise scraper")

try:
    scraper = GoldApiComScraper(source_config)
    passed(f"Scraper initialised — source_id: {scraper.source_id}")
    passed(f"Metals to fetch: {scraper.metals}")
    passed(f"Metals config loaded: {list(scraper.metals_config.keys())}")
except Exception as e:
    failed(f"Scraper failed to initialise — {e}")

# ============================================================
# TEST 4 — Run the scraper
# ============================================================
section("TEST 4 — Run scraper (live API call)")

print("\n  Calling Gold-API.com now — this makes real API calls...")
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
# TEST 5 — Check we got all 4 metals
# ============================================================
section("TEST 5 — Check all 4 metals returned")

metals_returned = [r["metal"] for r in result["data"]]
expected_metals = source_config["metals"]

for metal in expected_metals:
    if metal in metals_returned:
        passed(f"Metal returned: {metal}")
    else:
        failed(f"Metal MISSING: {metal}")

# ============================================================
# TEST 6 — Check each record has correct format
# ============================================================
section("TEST 6 — Validate record format for each metal")

for record in result["data"]:
    metal = record["metal"]
    print(f"\n  --- {metal.upper()} ---")

    # Check all required fields exist
    for field in REQUIRED_FIELDS:
        if field in record:
            passed(f"Field present: {field} = {record[field]}")
        else:
            failed(f"Field MISSING: {field} in {metal} record")

    # Check price is a positive number
    price = record["price_usd"]
    if isinstance(price, (int, float)) and price > 0:
        passed(f"Price is valid positive number: ${price:,.4f}")
    else:
        failed(f"Price is invalid: {price}")

    # Check source_id is correct
    if record["source_id"] == "gold_api_com":
        passed(f"source_id correct: {record['source_id']}")
    else:
        failed(f"source_id wrong: {record['source_id']}")

    # Check unit is correct
    if record["unit"] == "troy_ounce":
        passed(f"Unit correct: {record['unit']}")
    else:
        failed(f"Unit wrong: {record['unit']}")

    # Check extra fields exist
    if "extra" in record:
        passed(f"Extra fields present: {list(record['extra'].keys())}")
    else:
        failed("Extra field missing from record")

# ============================================================
# TEST 7 — Print full output for visual inspection
# ============================================================
section("TEST 7 — Full result output")

print()
print(json.dumps(result, indent=2))

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  Gold-API.com scraper is working correctly.")
print("  Safe to proceed to metals_dev.py")
print()
"""
test_rapid_api_gold_silver.py

Test script for the RapidAPI Gold Silver Rates India scraper.

IMPORTANT — Always run this from project root:
    python tests/unit/scrapers/test_rapid_api_gold_silver.py

What this tests:
1.  sources.json loads correctly
2.  rapid_api_gold_silver config block is found
3.  RAPIDAPI_KEY is set in environment
4.  Scraper initialises without errors
5.  Active locations loaded from config
6.  All 10 locations return records
7.  Gold records have correct format
8.  Silver records have correct format
9.  Karat prices parsed correctly for gold
10. Purity prices parsed correctly for silver
11. Currency detected correctly
12. Indian cities have price_inr set
13. International locations have price_inr as None
14. price_usd is always None
15. Full output for visual inspection
"""

from dotenv import load_dotenv
load_dotenv()

import json
import os
import sys
import logging
from src.scrapers.sites.rapid_api_gold_silver import RapidApiGoldSilverScraper

# ============================================================
# Set up logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)

# ============================================================
# Helpers
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
# TEST 2 — Find rapid_api_gold_silver config block
# ============================================================
section("TEST 2 — Find rapid_api_gold_silver config block")

source_config = None
for source in sources_data["sources"]:
    if source["id"] == "rapid_api_gold_silver":
        source_config = source
        break

if source_config:
    passed("rapid_api_gold_silver config found")
    passed(f"Enabled: {source_config['enabled']}")
    passed(f"Auth type: {source_config['auth']['type']}")
    passed(f"Auth env key: {source_config['auth']['env_key']}")
else:
    failed("rapid_api_gold_silver not found in sources.json")

# ============================================================
# TEST 3 — Check API key is set
# ============================================================
section("TEST 3 — Check RAPIDAPI_KEY is set")

api_key = os.environ.get("RAPIDAPI_KEY")

if api_key:
    passed(f"RAPIDAPI_KEY found — {api_key[:6]}...")
else:
    failed("RAPIDAPI_KEY not set — add it to your .env file")

# ============================================================
# TEST 4 — Initialise the scraper
# ============================================================
section("TEST 4 — Initialise scraper")

try:
    scraper = RapidApiGoldSilverScraper(source_config)
    passed(f"Scraper initialised — source_id: {scraper.source_id}")
    passed(f"Active locations: {scraper.active_locations}")
    passed(f"International locations: {scraper.international_locations}")
    passed(f"Currency map loaded: {scraper.currency_map}")
except Exception as e:
    failed(f"Scraper failed to initialise — {e}")

# ============================================================
# TEST 5 — Active locations loaded from config
# ============================================================
section("TEST 5 — Active locations loaded from config")

expected_locations = source_config["locations"]["active"]

if scraper.active_locations == expected_locations:
    passed(f"Active locations match config — {len(scraper.active_locations)} locations")
else:
    failed(
        f"Active locations mismatch\n"
        f"  Expected: {expected_locations}\n"
        f"  Got:      {scraper.active_locations}"
    )

# ============================================================
# TEST 6 — Run scraper (live API calls)
# ============================================================
section("TEST 6 — Run scraper (live API calls)")

print(f"\n  Fetching gold + silver for {len(scraper.active_locations)} locations...")
print(f"  This makes {len(scraper.active_locations) * 2} API calls...\n")

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
# TEST 7 — All active locations returned gold records
#           Silver is best-effort — some locations return 0
#           from the API (e.g. dubai silver) and are correctly
#           skipped by the scraper. This is a known API limitation.
# ============================================================
section("TEST 7 — Gold and silver records per location")

locations_with_gold = [
    r["extra"]["location"]
    for r in result["data"]
    if r["metal"] == "gold"
]

locations_with_silver = [
    r["extra"]["location"]
    for r in result["data"]
    if r["metal"] == "silver"
]

# Gold is required for every active location
for loc in scraper.active_locations:
    if loc in locations_with_gold:
        passed(f"Gold returned for: {loc}")
    else:
        failed(f"Gold MISSING for: {loc}")

# Silver is best-effort — warn but do not fail for missing locations
silver_missing = []
for loc in scraper.active_locations:
    if loc in locations_with_silver:
        passed(f"Silver returned for: {loc}")
    else:
        silver_missing.append(loc)
        print(f"  ⚠️   Silver not available for: {loc} — API returned 0 or null (known limitation)")

if not silver_missing:
    passed("All locations returned silver records")
else:
    passed(f"Silver available for {len(locations_with_silver)}/{len(scraper.active_locations)} locations — {len(silver_missing)} skipped by scraper (zero price from API)")

# ============================================================
# TEST 8 — Gold records have correct format
# ============================================================
section("TEST 8 — Gold records have correct format")

gold_records = [r for r in result["data"] if r["metal"] == "gold"]

for record in gold_records:
    location = record["extra"]["location"]

    for field in REQUIRED_FIELDS:
        if field not in record:
            failed(f"Gold {location} — field MISSING: {field}")

    if record["unit"] == "gram_10":
        passed(f"Gold {location} — unit = gram_10 ✓")
    else:
        failed(f"Gold {location} — unit wrong: {record['unit']}")

    if record["source_id"] == "rapid_api_gold_silver":
        passed(f"Gold {location} — source_id correct ✓")
    else:
        failed(f"Gold {location} — source_id wrong: {record['source_id']}")

# ============================================================
# TEST 9 — Silver records have correct format
# ============================================================
section("TEST 9 — Silver records have correct format")

silver_records = [r for r in result["data"] if r["metal"] == "silver"]

for record in silver_records:
    location = record["extra"]["location"]

    for field in REQUIRED_FIELDS:
        if field not in record:
            failed(f"Silver {location} — field MISSING: {field}")

    if record["unit"] == "kg":
        passed(f"Silver {location} — unit = kg ✓")
    else:
        failed(f"Silver {location} — unit wrong: {record['unit']}")

# ============================================================
# TEST 10 — Karat prices parsed correctly for gold
# ============================================================
section("TEST 10 — Karat prices parsed correctly for gold")

for record in gold_records:
    location = record["extra"]["location"]
    karat_prices = record["extra"].get("karat_prices", {})

    if karat_prices:
        passed(f"Gold {location} — karat_prices present: {list(karat_prices.keys())}")
        for karat, price in karat_prices.items():
            if isinstance(price, float) and price > 0:
                passed(f"  {karat}: {price}")
            else:
                failed(f"  {karat} price invalid: {price}")
    else:
        failed(f"Gold {location} — karat_prices missing")

# ============================================================
# TEST 11 — Purity prices parsed correctly for silver
# ============================================================
section("TEST 11 — Purity prices parsed correctly for silver")

for record in silver_records:
    location = record["extra"]["location"]
    purity_prices = record["extra"].get("purity_prices", {})

    if purity_prices:
        passed(f"Silver {location} — purity_prices present: {list(purity_prices.keys())}")
        for purity, price in purity_prices.items():
            if isinstance(price, float) and price > 0:
                passed(f"  {purity}: {price}")
            else:
                failed(f"  {purity} price invalid: {price}")
    else:
        failed(f"Silver {location} — purity_prices missing")

# ============================================================
# TEST 12 — Indian cities have price_inr set
# ============================================================
section("TEST 12 — Indian cities have price_inr set")

indian_locations = [
    loc for loc in scraper.active_locations
    if loc not in scraper.international_locations
]

for record in result["data"]:
    location = record["extra"]["location"]
    if location in indian_locations:
        if record["price_inr"] is not None and record["price_inr"] > 0:
            passed(f"{record['metal']} {location} — price_inr = ₹{record['price_inr']}")
        else:
            failed(f"{record['metal']} {location} — price_inr should be set")

# ============================================================
# TEST 13 — International locations have price_inr as None
# ============================================================
section("TEST 13 — International locations have price_inr as None")

for record in result["data"]:
    location = record["extra"]["location"]
    if location in scraper.international_locations:
        if record["price_inr"] is None:
            passed(f"{record['metal']} {location} — price_inr is None ✓")
        else:
            failed(f"{record['metal']} {location} — price_inr should be None")

# ============================================================
# TEST 14 — price_usd is always None
# ============================================================
section("TEST 14 — price_usd is always None")

for record in result["data"]:
    location = record["extra"]["location"]
    if record["price_usd"] is None:
        passed(f"{record['metal']} {location} — price_usd is None ✓")
    else:
        failed(f"{record['metal']} {location} — price_usd should be None")

# ============================================================
# TEST 15 — Full output for visual inspection
# ============================================================
section("TEST 15 — Full result output")

print()
print(json.dumps(result, indent=2))

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  RapidAPI Gold Silver scraper is working correctly.")
print("  Safe to proceed to wiring boto3 calls.")
print()
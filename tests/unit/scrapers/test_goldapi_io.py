"""
test_goldapi_io.py

Test script for the GoldAPI.io scraper.

IMPORTANT — Always run this from project root:
    python tests/unit/scrapers/test_goldapi_io.py

What this tests:
1. sources.json loads correctly
2. goldapi_io config block is found
3. GOLDAPI_IO_KEY is set in environment
4. Scraper initialises without errors
5. All 3 metals return a price (gold, silver, platinum)
6. Standard karats (24K, 22K, 18K) are captured
7. Extended karats (21K, 20K, 16K, 14K, 10K) are in extra{}
8. Market data (ask, bid, change) is captured
9. All records have correct standard format
"""

from dotenv import load_dotenv
load_dotenv()

import json
import os
import sys
import logging
from src.scrapers.sites.goldapi_io import GoldApiIoScraper

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
# TEST 2 — Find goldapi_io config
# ============================================================
section("TEST 2 — Find goldapi_io config block")

source_config = None
for source in sources_data["sources"]:
    if source["id"] == "goldapi_io":
        source_config = source
        break

if source_config:
    passed("goldapi_io config found")
    passed(f"Metals in config: {source_config['metals']}")
    passed(f"Enabled: {source_config['enabled']}")
    passed(f"Auth type: {source_config['auth']['type']}")
    passed(f"Auth header: {source_config['auth']['header_name']}")
else:
    failed("goldapi_io not found in sources.json")

# ============================================================
# TEST 3 — Check API key is set
# ============================================================
section("TEST 3 — Check GOLDAPI_IO_KEY is set")

api_key = os.environ.get("GOLDAPI_IO_KEY")

if api_key:
    passed(f"GOLDAPI_IO_KEY found — {api_key[:6]}...")
else:
    failed(
        "GOLDAPI_IO_KEY not set — "
        "add it to your .env file"
    )

# ============================================================
# TEST 4 — Initialise the scraper
# ============================================================
section("TEST 4 — Initialise scraper")

try:
    scraper = GoldApiIoScraper(source_config)
    passed(f"Scraper initialised — source_id: {scraper.source_id}")
    passed(f"Metals to fetch: {scraper.metals}")
    passed(f"Standard karats: {scraper.STANDARD_KARATS}")
    passed(f"Extended karats: {scraper.EXTENDED_KARATS}")
except Exception as e:
    failed(f"Scraper failed to initialise — {e}")

# ============================================================
# TEST 5 — Run the scraper
# ============================================================
section("TEST 5 — Run scraper (live API call)")

print("\n  Calling GoldAPI.io now — this uses 3 of your 100 monthly calls...")
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
# TEST 6 — Check all 3 metals returned
# ============================================================
section("TEST 6 — Check all 3 metals returned")

metals_returned = [r["metal"] for r in result["data"]]
expected_metals = source_config["metals"]

for metal in expected_metals:
    if metal in metals_returned:
        passed(f"Metal returned: {metal}")
    else:
        failed(f"Metal MISSING: {metal}")

# ============================================================
# TEST 7 — Check standard karats for each metal
# ============================================================
section("TEST 7 — Check standard karats (24K, 22K, 18K)")

for record in result["data"]:
    metal = record["metal"]
    extra = record.get("extra", {})
    karats = extra.get("karats", {})

    print(f"\n  --- {metal.upper()} karats ---")

    for karat in ["24K", "22K", "18K"]:
        if karat in karats:
            passed(f"{karat} gram price: ${karats[karat]}")
        else:
            failed(f"{karat} gram price MISSING for {metal}")

# ============================================================
# TEST 8 — Check extended karats in extra{}
# ============================================================
section("TEST 8 — Check extended karats in extra{}")

for record in result["data"]:
    metal = record["metal"]
    extra = record.get("extra", {})
    extended = extra.get("extended_karats", {})

    print(f"\n  --- {metal.upper()} extended karats ---")

    for karat in ["21K", "20K", "16K", "14K", "10K"]:
        if karat in extended:
            passed(f"{karat} gram price preserved: ${extended[karat]}")
        else:
            failed(f"{karat} gram price MISSING from extended_karats for {metal}")

# ============================================================
# TEST 9 — Check market data in extra{}
# ============================================================
section("TEST 9 — Check market data (ask, bid, change)")

for record in result["data"]:
    metal = record["metal"]
    extra = record.get("extra", {})

    print(f"\n  --- {metal.upper()} market data ---")

    for field in ["ask", "bid", "change", "change_percent",
                  "prev_close_price", "high_price", "low_price"]:
        if extra.get(field) is not None:
            passed(f"{field}: {extra[field]}")
        else:
            failed(f"Market data field MISSING: {field} for {metal}")

# ============================================================
# TEST 10 — Validate standard record format
# ============================================================
section("TEST 10 — Validate record format for each metal")

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
        passed(f"Price is valid: ${price:,.4f}")
    else:
        failed(f"Price is invalid: {price}")

    if record["source_id"] == "goldapi_io":
        passed(f"source_id correct: {record['source_id']}")
    else:
        failed(f"source_id wrong: {record['source_id']}")

    if record["unit"] == "troy_ounce":
        passed(f"Unit correct: {record['unit']}")
    else:
        failed(f"Unit wrong: {record['unit']}")

# ============================================================
# TEST 11 — Print full output for visual inspection
# ============================================================
section("TEST 11 — Full result output")

print()
print(json.dumps(result, indent=2))

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  GoldAPI.io scraper is working correctly.")
print("  Safe to proceed to free_gold_api.py")
print()
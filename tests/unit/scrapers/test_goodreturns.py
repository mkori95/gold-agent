"""
test_goodreturns.py

Test script for the GoodReturns.in scraper.

IMPORTANT — Always run this from project root:
    python tests/unit/scrapers/test_goodreturns.py

What this tests:
1.  sources.json loads correctly
2.  goodreturns config block is found
3.  Scraper initialises without errors
4.  All 5 sample cities return a record
5.  price_usd is None for every record (GoodReturns gives INR only)
6.  price_inr is a valid positive number (22K price)
7.  unit is "gram" — not "troy_ounce"
8.  extra.karat_prices has all 3 karats (24K, 22K, 18K) per city
9.  All records have correct standard format
10. Price sanity check — between ₹1,000 and ₹1,00,000 per gram
11. Full JSON output for visual inspection

Why only 5 cities?
    GoodReturns has 28 cities with 5-second delays between each.
    Full run = ~3 minutes. This sample run = ~30 seconds.

    To run all 28 cities — remove SampleGoodReturnsScraper and use
    GoodReturnsScraper directly:
        scraper = GoodReturnsScraper(source_config)
"""

from dotenv import load_dotenv
load_dotenv()

import json
import sys
import logging
from src.scrapers.sites.goodreturns import GoodReturnsScraper

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
# Sample-only scraper — overrides CITIES class constant
#
# Why this approach?
# GoodReturnsScraper uses self.CITIES — a class-level constant
# hardcoded in the class. It does NOT read cities from sources.json.
# So overriding source_config["cities"] does nothing.
# The correct way is to subclass and override CITIES directly.
# ============================================================
class SampleGoodReturnsScraper(GoodReturnsScraper):
    CITIES = [
        "mumbai",       # Largest market, West India
        "chennai",      # South India — Tamil users
        "hyderabad",    # South India — Telugu users
        "delhi",        # North India
        "bangalore",    # South India — tech city
    ]

SAMPLE_CITIES = SampleGoodReturnsScraper.CITIES

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
    "timestamp",
]

# ============================================================
# Price sanity range — per gram INR
# ============================================================
MIN_PRICE_INR = 1_000
MAX_PRICE_INR = 1_00_000

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
# TEST 2 — Find goodreturns config block
# ============================================================
section("TEST 2 — Find goodreturns config block")

source_config = None
for source in sources_data["sources"]:
    if source["id"] == "goodreturns":
        source_config = source
        break

if source_config:
    passed("goodreturns config found")
    passed(f"Enabled: {source_config['enabled']}")
    passed(f"Auth required: {source_config['auth']['required']}")
    passed(f"Total cities in config: {len(source_config.get('cities', []))}")
    passed(f"Base URL: {source_config['url']}")
    passed(f"Type: {source_config['type']}")
else:
    failed("goodreturns not found in sources.json")

# ============================================================
# TEST 3 — Initialise the scraper
# ============================================================
section("TEST 3 — Initialise scraper")

print(f"\n  ℹ️   Using SampleGoodReturnsScraper — overrides CITIES to {SAMPLE_CITIES}")
print(f"  ℹ️   Full 28-city run: use GoodReturnsScraper directly\n")

try:
    scraper = SampleGoodReturnsScraper(source_config)
    passed(f"Scraper initialised — source_id: {scraper.source_id}")
    passed(f"Cities to scrape: {scraper.CITIES}")
    passed(f"Base URL: {scraper.base_url}")
    passed(f"Karat IDs: {scraper.KARAT_IDS}")
except Exception as e:
    failed(f"Scraper failed to initialise — {e}")

# ============================================================
# TEST 4 — Run the scraper (live HTTP calls)
# ============================================================
section("TEST 4 — Run scraper (live scrape — 5 cities)")

print(f"\n  Scraping {len(SAMPLE_CITIES)} cities from GoodReturns.in...")
print(f"  Expect ~{len(SAMPLE_CITIES) * 6} seconds with polite delays...\n")

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
# TEST 5 — Check all 5 sample cities returned a record
# ============================================================
section("TEST 5 — Check all 5 sample cities returned")

cities_returned = [
    r.get("extra", {}).get("city")
    for r in result["data"]
]

for city in SAMPLE_CITIES:
    if city in cities_returned:
        passed(f"City returned: {city}")
    else:
        failed(f"City MISSING from results: {city}")

# ============================================================
# TEST 6 — price_usd must be None for every record
# ============================================================
section("TEST 6 — price_usd is None (GoodReturns gives INR only)")

for record in result["data"]:
    city = record.get("extra", {}).get("city", "unknown")
    price_usd = record.get("price_usd")

    if price_usd is None:
        passed(f"{city} — price_usd is None ✓")
    else:
        failed(
            f"{city} — price_usd should be None but got: {price_usd} — "
            f"consolidator does USD back-calculation, not the scraper"
        )

# ============================================================
# TEST 7 — price_inr must be a valid positive number (22K price)
# ============================================================
section("TEST 7 — price_inr is valid 22K price in INR")

for record in result["data"]:
    city = record.get("extra", {}).get("city", "unknown")
    price_inr = record.get("price_inr")

    if not isinstance(price_inr, (int, float)):
        failed(f"{city} — price_inr is not a number: {price_inr}")

    if price_inr <= 0:
        failed(f"{city} — price_inr is not positive: {price_inr}")

    # Confirm it matches the 22K price in extra{}
    karat_prices = record.get("extra", {}).get("karat_prices", {})
    expected_22k = karat_prices.get("22K")

    if expected_22k and price_inr == expected_22k:
        passed(f"{city} — price_inr = ₹{price_inr:,.2f} (matches 22K ✓)")
    elif expected_22k:
        failed(
            f"{city} — price_inr (₹{price_inr}) does not match "
            f"22K karat price (₹{expected_22k})"
        )
    else:
        passed(f"{city} — price_inr = ₹{price_inr:,.2f}")

# ============================================================
# TEST 8 — unit must be "gram" not "troy_ounce"
# ============================================================
section("TEST 8 — unit is 'gram' (retail city rate, not spot price)")

for record in result["data"]:
    city = record.get("extra", {}).get("city", "unknown")
    unit = record.get("unit")

    if unit == "gram":
        passed(f"{city} — unit = gram ✓")
    elif unit == "troy_ounce":
        failed(
            f"{city} — unit is 'troy_ounce' but should be 'gram' — "
            f"GoodReturns gives retail per-gram INR rates"
        )
    else:
        failed(f"{city} — unexpected unit value: '{unit}'")

# ============================================================
# TEST 9 — extra.karat_prices has 24K, 22K, 18K for every city
# ============================================================
section("TEST 9 — karat_prices has 24K, 22K, 18K for every city")

for record in result["data"]:
    city = record.get("extra", {}).get("city", "unknown")
    karat_prices = record.get("extra", {}).get("karat_prices", {})

    print(f"\n  --- {city.upper()} karat prices ---")

    for karat in ["24K", "22K", "18K"]:
        if karat in karat_prices:
            price = karat_prices[karat]
            passed(f"{karat} = ₹{price:,.2f} per gram")
        else:
            failed(f"{karat} price MISSING from extra.karat_prices for {city}")

# ============================================================
# TEST 10 — Price sanity check — ₹1,000 to ₹1,00,000 per gram
# ============================================================
section("TEST 10 — Price sanity check (₹1,000 – ₹1,00,000 per gram)")

for record in result["data"]:
    city = record.get("extra", {}).get("city", "unknown")
    karat_prices = record.get("extra", {}).get("karat_prices", {})

    for karat, price in karat_prices.items():
        if MIN_PRICE_INR <= price <= MAX_PRICE_INR:
            passed(f"{city} {karat} — ₹{price:,.2f} is within valid range")
        else:
            failed(
                f"{city} {karat} — ₹{price:,.2f} is OUTSIDE valid range "
                f"(₹{MIN_PRICE_INR:,} – ₹{MAX_PRICE_INR:,})"
            )

# ============================================================
# TEST 11 — Validate standard record format
# ============================================================
section("TEST 11 — Validate record format for each city")

for record in result["data"]:
    city = record.get("extra", {}).get("city", "unknown")
    print(f"\n  --- {city.upper()} ---")

    for field in REQUIRED_FIELDS:
        if field in record:
            passed(f"Field present: {field} = {record[field]}")
        else:
            failed(f"Field MISSING: {field} in {city} record")

    if record.get("source_id") == "goodreturns":
        passed(f"source_id correct: {record['source_id']}")
    else:
        failed(f"source_id wrong: {record.get('source_id')}")

    if record.get("metal") == "gold":
        passed(f"metal correct: gold")
    else:
        failed(f"metal wrong: {record.get('metal')} — should be 'gold'")

    extra = record.get("extra", {})
    for key in ["city", "primary_karat", "currency", "karat_prices"]:
        if key in extra:
            passed(f"extra.{key} present: {extra[key]}")
        else:
            failed(f"extra.{key} MISSING")

    if extra.get("primary_karat") == "22K":
        passed("extra.primary_karat is '22K' ✓")
    else:
        failed(f"extra.primary_karat should be '22K' — got: {extra.get('primary_karat')}")

    if extra.get("currency") == "INR":
        passed("extra.currency is 'INR' ✓")
    else:
        failed(f"extra.currency should be 'INR' — got: {extra.get('currency')}")

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
print("  GoodReturns scraper is working correctly.")
print("  Safe to proceed to moneycontrol.py")
print()
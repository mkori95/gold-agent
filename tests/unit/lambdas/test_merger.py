"""
test_merger.py

Unit tests for the Merger class.

IMPORTANT — Always run this from project root:
    python tests/unit/lambdas/test_merger.py

What this tests:
1.  Basic merge — 3 API sources          → metals dict built correctly
2.  INR rate applied                     → price_inr calculated correctly
3.  Consensus confidence                 → high for 3 sources
4.  GoodReturns city rates               → go to city_rates{} not trimmed mean
5.  Metals.Dev extra fields              → attached to correct metal
6.  GoldAPI.io karat prices              → attached to gold
7.  Karat fallback calculation           → used when GoldAPI.io missing
8.  Anomaly detection integration        → bad price rejected before trimmed mean
9.  Missing metal handled                → partial metals dict returned
10. No INR rate                          → price_inr is None
11. Merge result has required fields     → all fields present
12. source_prices preserved              → raw prices in result
13. GoodReturns excluded from consensus  → unit=gram records not in trimmed mean
"""

import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, ".")

from src.lambdas.consolidator.merger import Merger

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
# Mock data helpers
# ============================================================
def mock_spot_record(metal, price_usd, source_id, extra=None):
    return {
        "metal":       metal,
        "price_usd":   price_usd,
        "currency":    "USD",
        "price_inr":   None,
        "unit":        "troy_ounce",
        "source_id":   source_id,
        "source_name": source_id,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "extra":       extra or {}
    }

def mock_city_record(city, price_22k, source_id="goodreturns"):
    return {
        "metal":       "gold",
        "price_usd":   None,
        "currency":    "INR",
        "price_inr":   price_22k,
        "unit":        "gram",
        "source_id":   source_id,
        "source_name": "GoodReturns.in",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "extra": {
            "city":          city,
            "karat_prices":  {"24K": 9780.0, "22K": price_22k, "18K": 7340.0},
            "primary_karat": "22K",
            "currency":      "INR"
        }
    }

def mock_scraper_result(source_id, records):
    return {
        "source_id":        source_id,
        "source_name":      source_id,
        "status":           "success",
        "data":             records,
        "error":            None,
        "duration_seconds": 0.5,
        "scraped_at":       datetime.now(timezone.utc).isoformat(),
        "records_count":    len(records)
    }

# ============================================================
# Shared test INR rate
# 1 INR = 0.01099 USD → 1 USD = ~91 INR
# ============================================================
TEST_INR_RATE = 0.01099

# ============================================================
# Initialise
# ============================================================
merger = Merger()

# ============================================================
# TEST 1 — Basic merge with 3 API sources
# ============================================================
section("TEST 1 — Basic merge with 3 API sources")

results = [
    mock_scraper_result("gold_api_com", [
        mock_spot_record("gold",     3100.00, "gold_api_com"),
        mock_spot_record("silver",   32.50,   "gold_api_com"),
        mock_spot_record("platinum", 980.00,  "gold_api_com"),
        mock_spot_record("copper",   4.50,    "gold_api_com"),
    ]),
    mock_scraper_result("metals_dev", [
        mock_spot_record("gold",     3098.00, "metals_dev",
            extra={"mcx_gold": 3250.00, "ibja_gold": 3210.00,
                   "lbma_gold_am": 3088.50, "lbma_gold_pm": 3092.75}),
        mock_spot_record("silver",   32.30,   "metals_dev"),
        mock_spot_record("platinum", 978.00,  "metals_dev"),
        mock_spot_record("copper",   4.48,    "metals_dev"),
    ]),
    mock_scraper_result("goldapi_io", [
        mock_spot_record("gold",     3102.00, "goldapi_io",
            extra={"karats": {"24K": 99.80, "22K": 91.48, "18K": 74.85}}),
        mock_spot_record("silver",   32.60,   "goldapi_io"),
        mock_spot_record("platinum", 982.00,  "goldapi_io"),
    ]),
]

merged = merger.merge(results, inr_rate=TEST_INR_RATE)

if "metals" in merged:
    passed("metals key present in merged result")
else:
    failed("metals key missing from merged result")

if "gold" in merged["metals"]:
    passed("gold present in metals")
else:
    failed("gold missing from metals")

if "silver" in merged["metals"]:
    passed("silver present in metals")
else:
    failed("silver missing from metals")

if "platinum" in merged["metals"]:
    passed("platinum present in metals")
else:
    failed("platinum missing from metals")

if "copper" in merged["metals"]:
    passed("copper present in metals")
else:
    failed("copper missing from metals")

# ============================================================
# TEST 2 — INR rate applied correctly
# ============================================================
section("TEST 2 — INR rate applied correctly")

gold = merged["metals"]["gold"]
expected_inr = round(gold["price_usd"] / TEST_INR_RATE, 2)

if gold["price_inr"] == expected_inr:
    passed(f"price_inr = ₹{gold['price_inr']} (correctly calculated)")
else:
    failed(f"Expected ₹{expected_inr} got ₹{gold['price_inr']}")

if merged["inr_rate"] == TEST_INR_RATE:
    passed(f"inr_rate preserved: {merged['inr_rate']}")
else:
    failed(f"inr_rate should be {TEST_INR_RATE}")

if merged["usd_to_inr"] == round(1 / TEST_INR_RATE, 4):
    passed(f"usd_to_inr = ₹{merged['usd_to_inr']}")
else:
    failed(f"usd_to_inr calculation wrong")

# ============================================================
# TEST 3 — Confidence is "high" for 3 sources
# ============================================================
section("TEST 3 — Confidence is 'high' for 3 gold sources")

if gold["confidence"] == "high":
    passed(f"gold confidence = 'high'")
else:
    failed(f"Expected 'high' got '{gold['confidence']}'")

if gold["sources_count"] == 3:
    passed(f"sources_count = 3")
else:
    failed(f"Expected 3 got {gold['sources_count']}")

# ============================================================
# TEST 4 — GoodReturns city rates in city_rates{}
# ============================================================
section("TEST 4 — GoodReturns city rates in city_rates{}")

results_with_goodreturns = results + [
    mock_scraper_result("goodreturns", [
        mock_city_record("mumbai",  8950.0),
        mock_city_record("delhi",   8930.0),
        mock_city_record("chennai", 8960.0),
    ])
]

merged_with_cities = merger.merge(results_with_goodreturns, inr_rate=TEST_INR_RATE)
gold_with_cities   = merged_with_cities["metals"]["gold"]

if "city_rates" in gold_with_cities:
    passed("city_rates key present on gold")
else:
    failed("city_rates key missing from gold")

city_rates = gold_with_cities["city_rates"]

for city in ["mumbai", "delhi", "chennai"]:
    if city in city_rates:
        passed(f"city_rates has {city}: {city_rates[city]}")
    else:
        failed(f"city_rates missing {city}")

# ============================================================
# TEST 5 — Metals.Dev extra fields attached
# ============================================================
section("TEST 5 — Metals.Dev extra fields attached to gold")

extra = gold["extra"]

for field in ["mcx_gold", "ibja_gold", "lbma_gold_am", "lbma_gold_pm"]:
    if extra.get(field) is not None:
        passed(f"extra.{field} = {extra[field]}")
    else:
        failed(f"extra.{field} missing from gold")

# ============================================================
# TEST 6 — GoldAPI.io karat prices attached
# ============================================================
section("TEST 6 — GoldAPI.io karat prices attached to gold")

karats = gold["karats"]

if karats:
    passed(f"karats dict present: {list(karats.keys())}")
else:
    failed("karats dict missing or empty")

for karat in ["24K", "22K", "18K"]:
    if karat in karats:
        passed(f"karat {karat} present: {karats[karat]}")
    else:
        failed(f"karat {karat} missing")

# ============================================================
# TEST 7 — Karat fallback when GoldAPI.io missing
# ============================================================
section("TEST 7 — Karat fallback calculation (no GoldAPI.io)")

results_no_goldapi = [
    mock_scraper_result("gold_api_com", [
        mock_spot_record("gold", 3100.00, "gold_api_com"),
    ]),
    mock_scraper_result("metals_dev", [
        mock_spot_record("gold", 3098.00, "metals_dev"),
    ]),
]

merged_no_goldapi = merger.merge(results_no_goldapi, inr_rate=TEST_INR_RATE)
gold_no_goldapi   = merged_no_goldapi["metals"]["gold"]
karats_fallback   = gold_no_goldapi["karats"]

if karats_fallback:
    passed(f"Fallback karats calculated: {list(karats_fallback.keys())}")
else:
    failed("Fallback karats missing — should be calculated from purity ratios")

for karat in ["24K", "22K", "18K"]:
    if karat in karats_fallback:
        passed(f"Fallback {karat}: {karats_fallback[karat]}")
    else:
        failed(f"Fallback {karat} missing")

# ============================================================
# TEST 8 — Anomaly detection integration
# Bad price should be rejected before trimmed mean
# ============================================================
section("TEST 8 — Anomaly detection rejects bad prices")

results_with_bad_price = [
    mock_scraper_result("gold_api_com", [
        mock_spot_record("gold", 3100.00, "gold_api_com"),
    ]),
    mock_scraper_result("metals_dev", [
        mock_spot_record("gold", 3098.00, "metals_dev"),
    ]),
    mock_scraper_result("goldapi_io", [
        mock_spot_record("gold", 99999.00, "goldapi_io"),  # bad price
    ]),
]

merged_bad = merger.merge(results_with_bad_price, inr_rate=TEST_INR_RATE)
gold_bad   = merged_bad["metals"]["gold"]

# Bad price rejected — only 2 valid sources → confidence "medium"
if gold_bad["confidence"] == "medium":
    passed("Bad price rejected — confidence dropped to 'medium' (2 valid sources)")
else:
    failed(
        f"Expected 'medium' confidence after bad price rejection — "
        f"got '{gold_bad['confidence']}'"
    )

if "goldapi_io" not in gold_bad["sources_used"]:
    passed("goldapi_io with bad price correctly excluded from sources_used")
else:
    failed("goldapi_io should be excluded from sources_used")

# ============================================================
# TEST 9 — No INR rate → price_inr is None
# ============================================================
section("TEST 9 — No INR rate — price_inr should be None")

merged_no_inr = merger.merge(results, inr_rate=None)
gold_no_inr   = merged_no_inr["metals"]["gold"]

if gold_no_inr["price_inr"] is None:
    passed("price_inr is None when no INR rate provided")
else:
    failed(f"price_inr should be None — got {gold_no_inr['price_inr']}")

if merged_no_inr["inr_rate"] is None:
    passed("inr_rate is None in merged result")
else:
    failed("inr_rate should be None")

# ============================================================
# TEST 10 — Gold metal has all required fields
# ============================================================
section("TEST 10 — Gold metal has all required fields")

required_metal_fields = [
    "price_usd",
    "price_inr",
    "unit",
    "confidence",
    "sources_used",
    "sources_count",
    "source_prices",
    "spread_percent",
    "spread_flagged",
    "karats",
    "city_rates",
    "extra"
]

gold = merged["metals"]["gold"]

for field in required_metal_fields:
    if field in gold:
        passed(f"Field present: {field} = {gold[field]}")
    else:
        failed(f"Field MISSING: {field}")

# ============================================================
# TEST 11 — Merged result has required top-level fields
# ============================================================
section("TEST 11 — Merged result has required top-level fields")

for field in ["inr_rate", "usd_to_inr", "metals"]:
    if field in merged:
        passed(f"Top-level field present: {field}")
    else:
        failed(f"Top-level field MISSING: {field}")

# ============================================================
# TEST 12 — Source prices preserved in result
# ============================================================
section("TEST 12 — Source prices preserved in source_prices{}")

source_prices = gold["source_prices"]

for source in ["gold_api_com", "metals_dev", "goldapi_io"]:
    if source in source_prices:
        passed(f"source_prices has {source}: ${source_prices[source]}")
    else:
        failed(f"source_prices missing {source}")

# ============================================================
# TEST 13 — GoodReturns excluded from consensus prices
# ============================================================
section("TEST 13 — GoodReturns records excluded from consensus")

gold_with_cities = merged_with_cities["metals"]["gold"]
source_prices    = gold_with_cities["source_prices"]

if "goodreturns" not in source_prices:
    passed("goodreturns correctly excluded from source_prices (consensus)")
else:
    failed("goodreturns should not be in source_prices — city rates only")

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  Merger is working correctly.")
print("  Safe to proceed to dynamo_writer.py and s3_writer.py stubs.")
print()
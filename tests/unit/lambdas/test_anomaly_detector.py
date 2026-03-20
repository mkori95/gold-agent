"""
test_anomaly_detector.py

Unit tests for the AnomalyDetector class.

IMPORTANT — Always run this from project root:
    python tests/unit/lambdas/test_anomaly_detector.py

What this tests:
1.  Valid gold price           → is_valid True
2.  Valid silver price         → is_valid True
3.  Valid platinum price       → is_valid True
4.  Valid copper price         → is_valid True
5.  Price below minimum        → is_valid False, reason populated
6.  Price above maximum        → is_valid False, reason populated
7.  Price is zero              → is_valid False
8.  Price is negative          → is_valid False
9.  Price is None              → is_valid False
10. Price is wrong type        → is_valid False
11. Unknown metal              → is_valid True (let through with warning)
12. filter() — mixed list      → returns only valid records
13. filter() — all invalid     → returns empty list
14. filter() — empty list      → returns empty list
15. Result has required fields → all fields present
"""

import sys
import logging

sys.path.insert(0, ".")

from src.lambdas.consolidator.anomaly_detector import AnomalyDetector

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
# Helper — build a mock price record
# ============================================================
def mock_record(metal, price_usd, source_id="test_source"):
    return {
        "metal":      metal,
        "price_usd":  price_usd,
        "source_id":  source_id,
        "source_name": "Test Source",
        "currency":   "USD",
        "price_inr":  None,
        "unit":       "troy_ounce",
        "timestamp":  "2026-03-01T10:00:00+00:00",
        "extra":      {}
    }

# ============================================================
# Initialise
# ============================================================
section("Initialising AnomalyDetector")

detector = AnomalyDetector()

if detector.metals_config:
    passed(f"Metals config loaded — {list(detector.metals_config.keys())}")
else:
    failed("Metals config failed to load — check config/metals.json exists")

# ============================================================
# TEST 1 — Valid gold price
# ============================================================
section("TEST 1 — Valid gold price")

result = detector.validate(mock_record("gold", 3100.00))

if result["is_valid"] == True:
    passed(f"Gold $3100.00 — is_valid True")
else:
    failed(f"Gold $3100.00 should be valid — reason: {result['reason']}")

if result["reason"] is None:
    passed("reason is None for valid record")
else:
    failed(f"reason should be None — got: {result['reason']}")

# ============================================================
# TEST 2 — Valid silver price
# ============================================================
section("TEST 2 — Valid silver price")

result = detector.validate(mock_record("silver", 32.50))

if result["is_valid"] == True:
    passed(f"Silver $32.50 — is_valid True")
else:
    failed(f"Silver $32.50 should be valid — reason: {result['reason']}")

# ============================================================
# TEST 3 — Valid platinum price
# ============================================================
section("TEST 3 — Valid platinum price")

result = detector.validate(mock_record("platinum", 980.00))

if result["is_valid"] == True:
    passed(f"Platinum $980.00 — is_valid True")
else:
    failed(f"Platinum $980.00 should be valid — reason: {result['reason']}")

# ============================================================
# TEST 4 — Valid copper price
# ============================================================
section("TEST 4 — Valid copper price")

result = detector.validate(mock_record("copper", 4.50))

if result["is_valid"] == True:
    passed(f"Copper $4.50 — is_valid True")
else:
    failed(f"Copper $4.50 should be valid — reason: {result['reason']}")

# ============================================================
# TEST 5 — Price below minimum
# Gold minimum is $500 — test with $100
# ============================================================
section("TEST 5 — Price below minimum")

result = detector.validate(mock_record("gold", 100.00))

if result["is_valid"] == False:
    passed(f"Gold $100.00 — is_valid False (below $500 minimum)")
else:
    failed("Gold $100.00 should be rejected — below minimum")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated for rejected record")

# ============================================================
# TEST 6 — Price above maximum
# Gold maximum is $15,000 — test with $50,000
# ============================================================
section("TEST 6 — Price above maximum")

result = detector.validate(mock_record("gold", 50000.00))

if result["is_valid"] == False:
    passed(f"Gold $50,000.00 — is_valid False (above $15,000 maximum)")
else:
    failed("Gold $50,000.00 should be rejected — above maximum")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated for rejected record")

# ============================================================
# TEST 7 — Price is zero
# ============================================================
section("TEST 7 — Price is zero")

result = detector.validate(mock_record("gold", 0))

if result["is_valid"] == False:
    passed("Gold $0 — is_valid False")
else:
    failed("Gold $0 should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 8 — Price is negative
# ============================================================
section("TEST 8 — Price is negative")

result = detector.validate(mock_record("gold", -100.00))

if result["is_valid"] == False:
    passed("Gold -$100 — is_valid False")
else:
    failed("Negative price should be rejected")

# ============================================================
# TEST 9 — Price is None
# ============================================================
section("TEST 9 — Price is None")

result = detector.validate(mock_record("gold", None))

if result["is_valid"] == False:
    passed("Gold None price — is_valid False")
else:
    failed("None price should be rejected")

if result["reason"] is not None:
    passed(f"reason populated: {result['reason']}")
else:
    failed("reason should be populated")

# ============================================================
# TEST 10 — Price is wrong type (string)
# ============================================================
section("TEST 10 — Price is wrong type (string)")

result = detector.validate(mock_record("gold", "3100.00"))

if result["is_valid"] == False:
    passed("Gold price as string — is_valid False")
else:
    failed("String price should be rejected")

# ============================================================
# TEST 11 — Unknown metal — let through with warning
# ============================================================
section("TEST 11 — Unknown metal — should pass through")

result = detector.validate(mock_record("unobtanium", 999.00))

if result["is_valid"] == True:
    passed("Unknown metal 'unobtanium' — is_valid True (let through)")
else:
    failed("Unknown metals should be allowed through — we never silently drop data")

# ============================================================
# TEST 12 — filter() with mixed valid and invalid records
# ============================================================
section("TEST 12 — filter() with mixed valid and invalid records")

mixed_records = [
    mock_record("gold",     3100.00, "source_a"),   # valid
    mock_record("gold",     100.00,  "source_b"),   # invalid — too low
    mock_record("silver",   32.50,   "source_c"),   # valid
    mock_record("gold",     50000.00,"source_d"),   # invalid — too high
    mock_record("platinum", 980.00,  "source_e"),   # valid
]

valid_records = detector.filter(mixed_records)

if len(valid_records) == 3:
    passed(f"filter() returned 3 valid records from 5 total")
else:
    failed(f"Expected 3 valid records — got {len(valid_records)}")

valid_sources = [r["source_id"] for r in valid_records]

if "source_a" in valid_sources:
    passed("source_a (gold $3100) included")
else:
    failed("source_a should be included")

if "source_c" in valid_sources:
    passed("source_c (silver $32.50) included")
else:
    failed("source_c should be included")

if "source_e" in valid_sources:
    passed("source_e (platinum $980) included")
else:
    failed("source_e should be included")

if "source_b" not in valid_sources:
    passed("source_b (gold $100 — too low) correctly excluded")
else:
    failed("source_b should be excluded")

if "source_d" not in valid_sources:
    passed("source_d (gold $50000 — too high) correctly excluded")
else:
    failed("source_d should be excluded")

# ============================================================
# TEST 13 — filter() with all invalid records
# ============================================================
section("TEST 13 — filter() with all invalid records")

all_invalid = [
    mock_record("gold", 100.00),     # too low
    mock_record("gold", 50000.00),   # too high
    mock_record("gold", None),       # no price
]

valid_records = detector.filter(all_invalid)

if len(valid_records) == 0:
    passed("filter() returned empty list when all records invalid")
else:
    failed(f"Expected 0 valid records — got {len(valid_records)}")

# ============================================================
# TEST 14 — filter() with empty list
# ============================================================
section("TEST 14 — filter() with empty list")

valid_records = detector.filter([])

if valid_records == []:
    passed("filter() returned empty list for empty input")
else:
    failed(f"Expected empty list — got {valid_records}")

# ============================================================
# TEST 15 — Result has all required fields
# ============================================================
section("TEST 15 — Validate result has all required fields")

required_fields = ["is_valid", "price_usd", "metal", "source_id", "reason"]

result = detector.validate(mock_record("gold", 3100.00))

for field in required_fields:
    if field in result:
        passed(f"Field present: {field} = {result[field]}")
    else:
        failed(f"Field MISSING: {field}")

# ============================================================
# DONE
# ============================================================
section("ALL TESTS PASSED ✅")
print()
print("  AnomalyDetector is working correctly.")
print("  Safe to proceed to validator.py")
print()
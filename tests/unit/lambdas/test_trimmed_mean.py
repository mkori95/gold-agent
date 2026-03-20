"""
test_trimmed_mean.py

Unit tests for the TrimmedMean class.

IMPORTANT — Always run this from project root:
    python tests/unit/lambdas/test_trimmed_mean.py

What this tests:
1.  0 sources        → confidence "unavailable", price None
2.  1 source         → confidence "low", price = that source
3.  2 sources        → confidence "medium", price = average
4.  3 sources        → confidence "high", outlier effect removed
5.  4 sources        → confidence "high", highest + lowest dropped
6.  5 sources        → confidence "high", still trims only 1 from each end
7.  All same prices  → spread = 0.0, still works
8.  Spread < 1%      → no flag
9.  Spread 1-2%      → no flag (warning only in logs)
10. Spread > 2%      → spread_flagged = True
11. Source prices    → always preserved in result regardless of count
12. Sources used     → only trimmed sources returned for 3+
"""

import sys
import logging

# Add project root to path
sys.path.insert(0, ".")

from src.lambdas.consolidator.trimmed_mean import TrimmedMean

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
# Initialise
# ============================================================
trimmed_mean = TrimmedMean()

# ============================================================
# TEST 1 — 0 sources
# ============================================================
section("TEST 1 — 0 sources")

result = trimmed_mean.calculate({})

if result["confidence"] == "unavailable":
    passed("confidence is 'unavailable'")
else:
    failed(f"Expected 'unavailable' got '{result['confidence']}'")

if result["consensus_price"] is None:
    passed("consensus_price is None")
else:
    failed(f"Expected None got {result['consensus_price']}")

if result["sources_count"] == 0:
    passed("sources_count is 0")
else:
    failed(f"Expected 0 got {result['sources_count']}")

# ============================================================
# TEST 2 — 1 source
# ============================================================
section("TEST 2 — 1 source")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00
})

if result["confidence"] == "low":
    passed("confidence is 'low'")
else:
    failed(f"Expected 'low' got '{result['confidence']}'")

if result["consensus_price"] == 3100.00:
    passed(f"consensus_price = ${result['consensus_price']}")
else:
    failed(f"Expected $3100.00 got ${result['consensus_price']}")

if result["sources_count"] == 1:
    passed("sources_count is 1")
else:
    failed(f"Expected 1 got {result['sources_count']}")

# ============================================================
# TEST 3 — 2 sources — simple average
# ============================================================
section("TEST 3 — 2 sources — simple average")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00
})

if result["confidence"] == "medium":
    passed("confidence is 'medium'")
else:
    failed(f"Expected 'medium' got '{result['confidence']}'")

expected_avg = round((3100.00 + 3098.00) / 2, 4)
if result["consensus_price"] == expected_avg:
    passed(f"consensus_price = ${result['consensus_price']} (correct average)")
else:
    failed(f"Expected ${expected_avg} got ${result['consensus_price']}")

if result["sources_count"] == 2:
    passed("sources_count is 2")
else:
    failed(f"Expected 2 got {result['sources_count']}")

# ============================================================
# TEST 4 — 3 sources — trimmed mean
# Lowest (3098) and highest (3106.50) dropped
# Only middle value (3100) remains
# ============================================================
section("TEST 4 — 3 sources — trimmed mean")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00,
    "goldapi_io":   3106.50
})

if result["confidence"] == "high":
    passed("confidence is 'high'")
else:
    failed(f"Expected 'high' got '{result['confidence']}'")

# For 3 sources: drop highest (3106.50) and lowest (3098.00)
# Remaining: [3100.00] → consensus = 3100.00
expected = 3100.00
if result["consensus_price"] == expected:
    passed(f"consensus_price = ${result['consensus_price']} (correct — middle value)")
else:
    failed(f"Expected ${expected} got ${result['consensus_price']}")

if result["sources_count"] == 3:
    passed("sources_count is 3")
else:
    failed(f"Expected 3 got {result['sources_count']}")

# ============================================================
# TEST 5 — 4 sources — highest + lowest dropped
# ============================================================
section("TEST 5 — 4 sources — highest + lowest dropped")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00,
    "goldapi_io":   3102.00,
    "source_four":  3500.00   # clear outlier — should be dropped
})

if result["confidence"] == "high":
    passed("confidence is 'high'")
else:
    failed(f"Expected 'high' got '{result['confidence']}'")

# Sorted: [3098, 3100, 3102, 3500]
# Drop lowest (3098) and highest (3500)
# Remaining: [3100, 3102] → average = 3101.00
expected = round((3100.00 + 3102.00) / 2, 4)
if result["consensus_price"] == expected:
    passed(f"consensus_price = ${result['consensus_price']} (outlier $3500 correctly dropped)")
else:
    failed(f"Expected ${expected} got ${result['consensus_price']}")

if result["sources_count"] == 4:
    passed("sources_count is 4")
else:
    failed(f"Expected 4 got {result['sources_count']}")

# Verify outlier source not in sources_used
if "source_four" not in result["sources_used"]:
    passed("Outlier source correctly excluded from sources_used")
else:
    failed("Outlier source should not be in sources_used")

# ============================================================
# TEST 6 — 5 sources — still trims only 1 from each end
# ============================================================
section("TEST 6 — 5 sources — trims only 1 from each end")

result = trimmed_mean.calculate({
    "source_a": 3090.00,   # lowest — dropped
    "source_b": 3098.00,
    "source_c": 3100.00,
    "source_d": 3102.00,
    "source_e": 3200.00    # highest — dropped
})

if result["confidence"] == "high":
    passed("confidence is 'high'")
else:
    failed(f"Expected 'high' got '{result['confidence']}'")

# Sorted: [3090, 3098, 3100, 3102, 3200]
# Drop 3090 and 3200
# Remaining: [3098, 3100, 3102] → average = 3100.00
expected = round((3098.00 + 3100.00 + 3102.00) / 3, 4)
if result["consensus_price"] == expected:
    passed(f"consensus_price = ${result['consensus_price']} (both outliers dropped)")
else:
    failed(f"Expected ${expected} got ${result['consensus_price']}")

if result["sources_count"] == 5:
    passed("sources_count is 5")
else:
    failed(f"Expected 5 got {result['sources_count']}")

# ============================================================
# TEST 7 — All same prices — spread = 0
# ============================================================
section("TEST 7 — All same prices — spread should be 0.0")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3100.00,
    "goldapi_io":   3100.00
})

if result["spread_percent"] == 0.0:
    passed("spread_percent = 0.0 when all prices identical")
else:
    failed(f"Expected 0.0 got {result['spread_percent']}")

if result["consensus_price"] == 3100.00:
    passed(f"consensus_price = ${result['consensus_price']}")
else:
    failed(f"Expected $3100.00 got ${result['consensus_price']}")

# ============================================================
# TEST 8 — Spread < 1% — no flag
# ============================================================
section("TEST 8 — Spread < 1% — spread_flagged should be False")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00,
    "goldapi_io":   3102.00
})

spread = result["spread_percent"]
if spread < 1.0:
    passed(f"spread_percent = {spread}% (under 1% threshold)")
else:
    failed(f"Expected spread < 1% got {spread}%")

if result["spread_flagged"] == False:
    passed("spread_flagged = False")
else:
    failed("spread_flagged should be False for spread < 2%")

# ============================================================
# TEST 9 — Spread > 2% — spread_flagged should be True
# ============================================================
section("TEST 9 — Spread > 2% — spread_flagged should be True")

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3035.00,   # significantly lower — creates >2% spread
    "goldapi_io":   3102.00
})

spread = result["spread_percent"]
passed(f"spread_percent = {spread}%")

if result["spread_flagged"] == True:
    passed("spread_flagged = True (spread exceeded 2% threshold)")
else:
    failed(f"spread_flagged should be True for spread {spread}% > 2%")

# ============================================================
# TEST 10 — Source prices always preserved
# ============================================================
section("TEST 10 — Source prices always preserved in result")

input_prices = {
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00,
    "goldapi_io":   3106.50
}

result = trimmed_mean.calculate(input_prices)

if result["source_prices"] == input_prices:
    passed("source_prices preserved exactly — all original prices present")
else:
    failed(
        f"source_prices not preserved correctly\n"
        f"  Expected: {input_prices}\n"
        f"  Got:      {result['source_prices']}"
    )

# ============================================================
# TEST 11 — Result has all required fields
# ============================================================
section("TEST 11 — Result has all required fields")

required_fields = [
    "consensus_price",
    "confidence",
    "sources_used",
    "sources_count",
    "spread_percent",
    "spread_flagged",
    "source_prices"
]

result = trimmed_mean.calculate({
    "gold_api_com": 3100.00,
    "metals_dev":   3098.00
})

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
print("  TrimmedMean is working correctly.")
print("  Safe to proceed to anomaly_detector.py")
print()
"""
Unit tests for the RapidAPI Gold Silver Rates India scraper.
Marked skip -- requires RAPIDAPI_KEY and makes live API calls.
Run manually: pytest tests/unit/scrapers/test_rapid_api_gold_silver.py -m live

What this tests:
1.  sources.json loads correctly
2.  rapid_api_gold_silver config block is found
3.  RAPIDAPI_KEY is set in environment
4.  Scraper initialises without errors
5.  Active locations loaded from config
6.  All active locations return gold records
7.  Gold records have correct format
8.  Silver records have correct format
9.  Karat prices parsed correctly for gold
10. Purity prices parsed correctly for silver
11. Indian cities have price_inr set
12. International locations have price_inr as None
13. price_usd is always None
"""
import json
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skip(reason="live scraper test — requires RAPIDAPI_KEY, run manually")

REQUIRED_FIELDS = ["metal", "price_usd", "price_inr", "unit",
                   "source_id", "source_name", "timestamp"]


@pytest.fixture(scope="module")
def source_config():
    with open("config/sources.json", "r") as f:
        sources_data = json.load(f)
    config = next(
        (s for s in sources_data["sources"] if s["id"] == "rapid_api_gold_silver"), None
    )
    assert config is not None, "rapid_api_gold_silver not found in sources.json"
    return config


@pytest.fixture(scope="module")
def scraper(source_config):
    from src.scrapers.sites.rapid_api_gold_silver import RapidApiGoldSilverScraper
    return RapidApiGoldSilverScraper(source_config)


@pytest.fixture(scope="module")
def scraper_result(scraper):
    return scraper.run()


def test_sources_json_loads():
    with open("config/sources.json", "r") as f:
        data = json.load(f)
    assert "sources" in data


def test_config_found(source_config):
    assert source_config["auth"]["type"]
    assert source_config["auth"]["env_key"]


def test_api_key_set():
    assert os.environ.get("RAPIDAPI_KEY"), "RAPIDAPI_KEY not set"


def test_scraper_initialises(scraper, source_config):
    assert scraper.source_id == "rapid_api_gold_silver"
    assert scraper.active_locations == source_config["locations"]["active"]
    assert scraper.currency_map


def test_active_locations_loaded(scraper, source_config):
    assert scraper.active_locations == source_config["locations"]["active"]


def test_scraper_returns_success(scraper_result):
    assert scraper_result["status"] == "success", f"Scrape failed: {scraper_result.get('error')}"


def test_gold_returned_for_all_locations(scraper, scraper_result):
    locations_with_gold = [
        r["extra"]["location"] for r in scraper_result["data"] if r["metal"] == "gold"
    ]
    for loc in scraper.active_locations:
        assert loc in locations_with_gold, f"Gold missing for: {loc}"


def test_gold_record_format(scraper_result):
    gold_records = [r for r in scraper_result["data"] if r["metal"] == "gold"]
    for record in gold_records:
        location = record["extra"]["location"]
        for field in REQUIRED_FIELDS:
            assert field in record, f"Gold {location} -- field missing: {field}"
        assert record["unit"] == "gram_10", f"Gold {location} -- unit wrong: {record['unit']}"
        assert record["source_id"] == "rapid_api_gold_silver"


def test_silver_record_format(scraper_result):
    silver_records = [r for r in scraper_result["data"] if r["metal"] == "silver"]
    for record in silver_records:
        location = record["extra"]["location"]
        for field in REQUIRED_FIELDS:
            assert field in record, f"Silver {location} -- field missing: {field}"
        assert record["unit"] == "kg", f"Silver {location} -- unit wrong: {record['unit']}"


def test_gold_karat_prices(scraper_result):
    gold_records = [r for r in scraper_result["data"] if r["metal"] == "gold"]
    for record in gold_records:
        location = record["extra"]["location"]
        karat_prices = record["extra"].get("karat_prices", {})
        assert karat_prices, f"Gold {location} -- karat_prices missing"
        for karat, price in karat_prices.items():
            assert isinstance(price, float) and price > 0, f"{karat} price invalid: {price}"


def test_silver_purity_prices(scraper_result):
    silver_records = [r for r in scraper_result["data"] if r["metal"] == "silver"]
    for record in silver_records:
        location = record["extra"]["location"]
        purity_prices = record["extra"].get("purity_prices", {})
        assert purity_prices, f"Silver {location} -- purity_prices missing"


def test_indian_cities_have_price_inr(scraper, scraper_result):
    indian_locations = [
        loc for loc in scraper.active_locations if loc not in scraper.international_locations
    ]
    for record in scraper_result["data"]:
        if record["extra"]["location"] in indian_locations:
            assert record["price_inr"] is not None and record["price_inr"] > 0, \
                f"{record['metal']} {record['extra']['location']} -- price_inr should be set"


def test_international_locations_no_price_inr(scraper, scraper_result):
    for record in scraper_result["data"]:
        if record["extra"]["location"] in scraper.international_locations:
            assert record["price_inr"] is None, \
                f"{record['metal']} {record['extra']['location']} -- price_inr should be None"


def test_price_usd_always_none(scraper_result):
    for record in scraper_result["data"]:
        assert record["price_usd"] is None, \
            f"{record['metal']} {record['extra']['location']} -- price_usd should be None"

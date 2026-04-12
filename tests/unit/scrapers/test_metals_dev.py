"""
Unit tests for the Metals.Dev scraper.
Marked skip -- requires METALS_DEV_API_KEY and makes live API calls.
Run manually: pytest tests/unit/scrapers/test_metals_dev.py -m live

What this tests:
1.  sources.json loads correctly
2.  metals_dev config block is found
3.  METALS_DEV_API_KEY is set in environment
4.  Scraper initialises without errors
5.  All 4 metals return a price
6.  Copper unit conversion is correct
7.  INR rate is extracted correctly
8.  MCX and IBJA prices captured for gold
9.  MCX prices captured for silver
10. LBMA prices captured correctly
11. All records have correct standard format
"""
import json
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skip(reason="live scraper test — requires METALS_DEV_API_KEY, run manually")

REQUIRED_FIELDS = ["metal", "price_usd", "currency", "price_inr",
                   "unit", "source_id", "source_name", "timestamp"]


@pytest.fixture(scope="module")
def source_config():
    with open("config/sources.json", "r") as f:
        sources_data = json.load(f)
    config = next((s for s in sources_data["sources"] if s["id"] == "metals_dev"), None)
    assert config is not None, "metals_dev not found in sources.json"
    return config


@pytest.fixture(scope="module")
def scraper(source_config):
    from src.scrapers.sites.metals_dev import MetalsDevScraper
    return MetalsDevScraper(source_config)


@pytest.fixture(scope="module")
def scraper_result(scraper):
    return scraper.run()


def test_sources_json_loads():
    with open("config/sources.json", "r") as f:
        data = json.load(f)
    assert "sources" in data


def test_metals_dev_config_found(source_config):
    assert source_config["metals"]
    assert source_config["auth"]["type"]
    assert source_config["auth"]["env_key"]


def test_api_key_set():
    assert os.environ.get("METALS_DEV_API_KEY"), "METALS_DEV_API_KEY not set"


def test_scraper_initialises(scraper):
    assert scraper.source_id == "metals_dev"
    assert scraper.metals
    assert scraper.COPPER_LB_TO_TOZ


def test_scraper_returns_success(scraper_result):
    assert scraper_result["status"] == "success", f"Scrape failed: {scraper_result.get('error')}"


def test_all_metals_returned(source_config, scraper_result):
    metals_returned = [r["metal"] for r in scraper_result["data"]]
    for metal in source_config["metals"]:
        assert metal in metals_returned, f"Metal missing: {metal}"


def test_inr_rate_extracted(scraper):
    assert scraper.inr_rate is not None, "INR rate was not extracted"
    usd_to_inr = round(1 / scraper.inr_rate, 2)
    assert 80 <= usd_to_inr <= 100, f"INR rate looks wrong: 1 USD = {usd_to_inr}"


def test_copper_unit_conversion(scraper_result):
    copper = next((r for r in scraper_result["data"] if r["metal"] == "copper"), None)
    assert copper is not None, "Copper record not found"
    extra = copper.get("extra", {})
    assert "price_per_pound" in extra
    assert "price_per_toz" in extra
    assert "conversion_factor" in extra
    price_lb = extra["price_per_pound"]
    price_toz = extra["price_per_toz"]
    conversion = extra["conversion_factor"]
    expected_toz = round(price_lb / conversion, 6)
    assert abs(expected_toz - price_toz) < 0.001
    assert copper["price_usd"] == price_toz


def test_gold_mcx_ibja_prices(scraper_result):
    gold = next((r for r in scraper_result["data"] if r["metal"] == "gold"), None)
    assert gold is not None
    extra = gold.get("extra", {})
    for field in ["mcx_gold", "mcx_gold_am", "mcx_gold_pm", "ibja_gold",
                  "lbma_gold_am", "lbma_gold_pm"]:
        assert extra.get(field) is not None, f"Gold extra field missing: {field}"


def test_silver_mcx_prices(scraper_result):
    silver = next((r for r in scraper_result["data"] if r["metal"] == "silver"), None)
    assert silver is not None
    extra = silver.get("extra", {})
    for field in ["mcx_silver", "mcx_silver_am", "mcx_silver_pm", "lbma_silver"]:
        assert extra.get(field) is not None, f"Silver extra field missing: {field}"


def test_record_format(scraper_result):
    for record in scraper_result["data"]:
        for field in REQUIRED_FIELDS:
            assert field in record, f"Field missing: {field} in {record['metal']} record"
        assert isinstance(record["price_usd"], (int, float)) and record["price_usd"] > 0
        assert record["source_id"] == "metals_dev"
        assert record["unit"] == "troy_ounce"

"""
Unit tests for the Gold-API.com scraper.
Marked skip — makes live API calls. Run manually when needed:
    pytest tests/unit/scrapers/test_gold_api_com.py -m live

What this tests:
1. sources.json loads correctly
2. gold_api_com config block is found
3. Scraper initialises without errors
4. All 4 metals return a price
5. Prices are within valid ranges
6. Price records have the correct standard format
"""
import json
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skip(reason="live scraper test — run manually with: pytest -m live")

REQUIRED_FIELDS = ["metal", "price_usd", "currency", "price_inr",
                   "unit", "source_id", "source_name", "timestamp"]


@pytest.fixture(scope="module")
def source_config():
    with open("config/sources.json", "r") as f:
        sources_data = json.load(f)
    config = next((s for s in sources_data["sources"] if s["id"] == "gold_api_com"), None)
    assert config is not None, "gold_api_com not found in sources.json"
    return config


@pytest.fixture(scope="module")
def scraper_result(source_config):
    from src.scrapers.sites.gold_api_com import GoldApiComScraper
    scraper = GoldApiComScraper(source_config)
    return scraper.run()


def test_sources_json_loads():
    with open("config/sources.json", "r") as f:
        data = json.load(f)
    assert "sources" in data


def test_gold_api_com_config_found(source_config):
    assert source_config is not None
    assert source_config["metals"]
    assert "enabled" in source_config


def test_scraper_initialises(source_config):
    from src.scrapers.sites.gold_api_com import GoldApiComScraper
    scraper = GoldApiComScraper(source_config)
    assert scraper.source_id == "gold_api_com"


def test_scraper_returns_success(scraper_result):
    assert scraper_result["status"] == "success", f"Scrape failed: {scraper_result.get('error')}"


def test_all_metals_returned(source_config, scraper_result):
    metals_returned = [r["metal"] for r in scraper_result["data"]]
    for metal in source_config["metals"]:
        assert metal in metals_returned, f"Metal missing: {metal}"


def test_record_format(source_config, scraper_result):
    for record in scraper_result["data"]:
        for field in REQUIRED_FIELDS:
            assert field in record, f"Field missing: {field} in {record['metal']} record"
        assert isinstance(record["price_usd"], (int, float)) and record["price_usd"] > 0
        assert record["source_id"] == "gold_api_com"
        assert record["unit"] == "troy_ounce"
        assert "extra" in record

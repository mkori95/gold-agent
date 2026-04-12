"""
Unit tests for the GoldAPI.io scraper.
Marked skip -- requires GOLDAPI_IO_KEY and makes live API calls.
Run manually: pytest tests/unit/scrapers/test_goldapi_io.py -m live

What this tests:
1.  sources.json loads correctly
2.  goldapi_io config block is found
3.  GOLDAPI_IO_KEY is set in environment
4.  Scraper initialises without errors
5.  All 3 metals return a price (gold, silver, platinum)
6.  Standard karats (24K, 22K, 18K) are captured
7.  Extended karats (21K, 20K, 16K, 14K, 10K) are in extra{}
8.  Market data (ask, bid, change) is captured
9.  All records have correct standard format
"""
import json
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skip(reason="live scraper test — requires GOLDAPI_IO_KEY, run manually")

REQUIRED_FIELDS = ["metal", "price_usd", "currency", "price_inr",
                   "unit", "source_id", "source_name", "timestamp"]


@pytest.fixture(scope="module")
def source_config():
    with open("config/sources.json", "r") as f:
        sources_data = json.load(f)
    config = next((s for s in sources_data["sources"] if s["id"] == "goldapi_io"), None)
    assert config is not None, "goldapi_io not found in sources.json"
    return config


@pytest.fixture(scope="module")
def scraper_result(source_config):
    from src.scrapers.sites.goldapi_io import GoldApiIoScraper
    scraper = GoldApiIoScraper(source_config)
    return scraper.run()


def test_sources_json_loads():
    with open("config/sources.json", "r") as f:
        data = json.load(f)
    assert "sources" in data


def test_goldapi_io_config_found(source_config):
    assert source_config["metals"]
    assert source_config["auth"]["type"]


def test_api_key_set():
    assert os.environ.get("GOLDAPI_IO_KEY"), "GOLDAPI_IO_KEY not set"


def test_scraper_initialises(source_config):
    from src.scrapers.sites.goldapi_io import GoldApiIoScraper
    scraper = GoldApiIoScraper(source_config)
    assert scraper.source_id == "goldapi_io"
    assert scraper.STANDARD_KARATS
    assert scraper.EXTENDED_KARATS


def test_scraper_returns_success(scraper_result):
    assert scraper_result["status"] == "success", f"Scrape failed: {scraper_result.get('error')}"


def test_all_metals_returned(source_config, scraper_result):
    metals_returned = [r["metal"] for r in scraper_result["data"]]
    for metal in source_config["metals"]:
        assert metal in metals_returned, f"Metal missing: {metal}"


def test_standard_karats_captured(scraper_result):
    for record in scraper_result["data"]:
        karats = record.get("extra", {}).get("karats", {})
        for karat in ["24K", "22K", "18K"]:
            assert karat in karats, f"{karat} missing for {record['metal']}"


def test_extended_karats_in_extra(scraper_result):
    for record in scraper_result["data"]:
        extended = record.get("extra", {}).get("extended_karats", {})
        for karat in ["21K", "20K", "16K", "14K", "10K"]:
            assert karat in extended, f"{karat} missing from extended_karats for {record['metal']}"


def test_market_data_captured(scraper_result):
    for record in scraper_result["data"]:
        extra = record.get("extra", {})
        for field in ["ask", "bid", "change", "change_percent",
                      "prev_close_price", "high_price", "low_price"]:
            assert extra.get(field) is not None, f"{field} missing for {record['metal']}"


def test_record_format(scraper_result):
    for record in scraper_result["data"]:
        for field in REQUIRED_FIELDS:
            assert field in record, f"Field missing: {field} in {record['metal']} record"
        assert isinstance(record["price_usd"], (int, float)) and record["price_usd"] > 0
        assert record["source_id"] == "goldapi_io"
        assert record["unit"] == "troy_ounce"

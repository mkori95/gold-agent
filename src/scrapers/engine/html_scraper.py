"""
html_scraper.py

Handles all HTML scraping for the Gold Agent scraper engine.
Used by all scraper-type sources (GoodReturns.in, Moneycontrol etc)

This class:
- Downloads raw HTML pages using requests
- Parses HTML using BeautifulSoup
- Handles anti-scraping measures politely
- Adds delays between requests to avoid being blocked
- Returns parsed BeautifulSoup object for site scrapers to extract data

It does NOT know anything about gold prices specifically.
Individual site scrapers use this to get parsed HTML and then
find the specific tags they need.
"""

import requests
import logging
import time
import random
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


class HTMLScraper:
    """
    Handles all HTML scraping for scraper-type sources.

    Used by individual site scrapers — they create an instance
    of this class and call fetch() to get parsed HTML back.
    """

    # Default timeout for all page downloads — seconds
    DEFAULT_TIMEOUT = 15

    # Pretend to be a real browser so websites don't block us
    # This is a real Chrome browser User-Agent string
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, source_config: dict):
        """
        Called when HTMLScraper is created.

        Args:
            source_config: The full config block for this source
                           from sources.json
        """
        self.source_id = source_config["id"]
        self.source_name = source_config["name"]
        self.base_url = source_config["url"]
        self.timeout = self.DEFAULT_TIMEOUT

        # How long to wait between requests to be polite
        # Read from sources.json — default 5 seconds if not set
        self.delay_seconds = (
            source_config
            .get("rate_limit", {})
            .get("delay_between_requests_seconds", 5)
        )

    # ============================================================
    # Main method — downloads page and returns parsed HTML
    # ============================================================
    def fetch(
        self,
        endpoint: str,
        params: dict = None,
        extra_headers: dict = None
    ) -> BeautifulSoup:
        """
        Downloads a page and returns parsed BeautifulSoup object.

        Args:
            endpoint:      The page path e.g. "/gold-rates-in-mumbai.html"
            params:        Optional query parameters as dict
            extra_headers: Optional extra headers as dict

        Returns:
            Parsed BeautifulSoup object ready for tag extraction

        Raises:
            Exception if page download fails for any reason
        """

        # Build the full URL
        url = f"{self.base_url}{endpoint}"

        # Build headers — pretend to be a real browser
        headers = self._build_headers(extra_headers)

        logger.info(
            f"[{self.source_id}] Fetching page: {url}"
        )

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params or {},
                timeout=self.timeout
            )

            # Handle HTTP error status codes
            self._handle_http_errors(response)

            # Parse HTML with BeautifulSoup using lxml parser
            # lxml is faster than Python's built-in html.parser
            soup = BeautifulSoup(response.text, "lxml")

            logger.info(
                f"[{self.source_id}] Page downloaded successfully — "
                f"{len(response.text)} characters"
            )

            return soup

        except requests.exceptions.Timeout:
            raise Exception(
                f"[{self.source_id}] Page download timed out after "
                f"{self.timeout} seconds — {url}"
            )

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"[{self.source_id}] Connection error — "
                f"could not reach {url}"
            )

    # ============================================================
    # Fetch multiple pages with polite delay between each
    # ============================================================
    def fetch_multiple(
        self,
        endpoints: list,
        extra_headers: dict = None
    ) -> list:
        """
        Downloads multiple pages with a polite delay between each.

        Used by GoodReturns scraper — we scrape 8 cities so we
        need to make 8 requests. We add a delay between each
        so we don't hammer their server.

        Args:
            endpoints:     List of endpoint paths to fetch
            extra_headers: Optional extra headers for all requests

        Returns:
            List of tuples — (endpoint, BeautifulSoup or None)
            None means that page failed — others continue
        """
        results = []

        for i, endpoint in enumerate(endpoints):
            try:
                soup = self.fetch(endpoint, extra_headers=extra_headers)
                results.append((endpoint, soup))

            except Exception as e:
                # One page failing doesn't stop the others
                logger.error(
                    f"[{self.source_id}] Failed to fetch {endpoint} — "
                    f"{str(e)}"
                )
                results.append((endpoint, None))

            # Add polite delay between requests
            # Skip delay after the last request
            if i < len(endpoints) - 1:
                self._polite_delay()

        return results

    # ============================================================
    # Build request headers — pretend to be a real browser
    # ============================================================
    def _build_headers(self, extra_headers: dict = None) -> dict:
        """
        Builds headers that make us look like a real browser.

        Websites check these headers to detect bots.
        We set realistic values to avoid being blocked.

        Args:
            extra_headers: Any additional headers to include

        Returns:
            Dict of headers
        """
        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }

        # Merge in any extra headers
        if extra_headers:
            headers.update(extra_headers)

        return headers

    # ============================================================
    # Polite delay between requests
    # ============================================================
    def _polite_delay(self) -> None:
        """
        Waits between requests to be a polite scraper.

        We add a small random extra delay on top of the
        configured delay — this makes our requests look
        more like a human browsing and less like a bot.

        Configured in sources.json:
        delay_between_requests_seconds: 5
        """

        # Add random extra 0-2 seconds on top of configured delay
        # Makes timing look more human
        extra = random.uniform(0, 2)
        total_delay = self.delay_seconds + extra

        logger.info(
            f"[{self.source_id}] Polite delay — "
            f"waiting {round(total_delay, 1)} seconds"
        )

        time.sleep(total_delay)

    # ============================================================
    # Handle HTTP error status codes
    # ============================================================
    def _handle_http_errors(self, response: requests.Response) -> None:
        """
        Checks the HTTP response status code and raises
        meaningful errors for common failure cases.

        Args:
            response: The requests Response object

        Raises:
            Exception with clear message for each error type
        """

        status = response.status_code

        # 200 — all good
        if status == 200:
            return

        # 403 — website is blocking us
        if status == 403:
            raise Exception(
                f"[{self.source_id}] Blocked by website (403) — "
                f"may need to update User-Agent or add more delay"
            )

        # 404 — page not found
        if status == 404:
            raise Exception(
                f"[{self.source_id}] Page not found (404) — "
                f"URL may have changed — check endpoint in sources.json"
            )

        # 429 — too many requests
        if status == 429:
            raise Exception(
                f"[{self.source_id}] Too many requests (429) — "
                f"increase delay_between_requests_seconds in sources.json"
            )

        # 500+ — server error on their side
        if status >= 500:
            raise Exception(
                f"[{self.source_id}] Server error ({status}) — "
                f"source may be down temporarily"
            )

        # Any other non-200 status
        raise Exception(
            f"[{self.source_id}] Unexpected status code: {status}"
        )
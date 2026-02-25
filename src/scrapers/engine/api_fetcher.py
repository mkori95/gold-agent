"""
api_fetcher.py

Handles all HTTP API calls for the Gold Agent scraper engine.
Used by all API-type sources (Gold-API.com, Metals.Dev, GoldAPI.io etc)

This class:
- Builds the correct request (headers, query params, auth)
- Makes the HTTP call with timeout
- Handles all HTTP errors cleanly
- Returns raw JSON response

It does NOT know anything about gold prices specifically.
Individual site scrapers use this to make calls and then
extract the fields they need.
"""

import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class APIFetcher:
    """
    Handles all REST API calls for API-type sources.

    Used by individual site scrapers — they create an instance
    of this class and call fetch() to get raw JSON back.
    """

    # Default timeout for all API calls — seconds
    DEFAULT_TIMEOUT = 10

    def __init__(self, source_config: dict):
        """
        Called when APIFetcher is created.

        Args:
            source_config: The full config block for this source
                           from sources.json
        """
        self.source_id = source_config["id"]
        self.source_name = source_config["name"]
        self.base_url = source_config["url"]
        self.auth_config = source_config["auth"]
        self.timeout = self.DEFAULT_TIMEOUT

    # ============================================================
    # Main method — makes the API call and returns JSON
    # ============================================================
    def fetch(
        self,
        endpoint: str,
        params: dict = None,
        headers: dict = None
    ) -> dict:
        """
        Makes a GET request to the API and returns JSON response.

        Args:
            endpoint: The endpoint path e.g. "/price/XAU"
            params:   Optional query parameters as dict
            headers:  Optional extra headers as dict

        Returns:
            Parsed JSON response as dict

        Raises:
            Exception if request fails for any reason
        """

        # Build the full URL
        url = f"{self.base_url}{endpoint}"

        # Build headers — start with defaults
        request_headers = self._build_headers(headers)

        # Build query params — start with what was passed in
        request_params = params or {}

        # Add auth to headers or params depending on auth type
        request_headers, request_params = self._apply_auth(
            request_headers,
            request_params
        )

        logger.info(
            f"[{self.source_id}] Calling {url}"
        )

        try:
            response = requests.get(
                url,
                headers=request_headers,
                params=request_params,
                timeout=self.timeout
            )

            # Handle HTTP error status codes
            self._handle_http_errors(response)

            # Parse and return JSON
            return response.json()

        except requests.exceptions.Timeout:
            raise Exception(
                f"[{self.source_id}] Request timed out after "
                f"{self.timeout} seconds — {url}"
            )

        except requests.exceptions.ConnectionError:
            raise Exception(
                f"[{self.source_id}] Connection error — "
                f"could not reach {url}"
            )

        except requests.exceptions.JSONDecodeError:
            raise Exception(
                f"[{self.source_id}] Response was not valid JSON — {url}"
            )

    # ============================================================
    # Build request headers
    # ============================================================
    def _build_headers(self, extra_headers: dict = None) -> dict:
        """
        Builds the base headers for every request.

        Args:
            extra_headers: Any additional headers to include

        Returns:
            Dict of headers
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "GoldAgent/1.0"
        }

        # Merge in any extra headers passed in
        if extra_headers:
            headers.update(extra_headers)

        return headers

    # ============================================================
    # Apply authentication — header or query param
    # ============================================================
    def _apply_auth(
        self,
        headers: dict,
        params: dict
    ) -> tuple:
        """
        Adds authentication to the request.

        Reads auth config from sources.json:
        - type: "header" → adds API key as a request header
        - type: "query_param" → adds API key as a URL parameter
        - required: false → no auth needed, returns unchanged

        Args:
            headers: Current headers dict
            params:  Current query params dict

        Returns:
            Tuple of (updated headers, updated params)
        """

        # No auth needed for this source
        if not self.auth_config["required"]:
            return headers, params

        # Get the API key from environment variables
        env_key = self.auth_config["env_key"]
        api_key = os.environ.get(env_key)

        if not api_key:
            raise Exception(
                f"[{self.source_id}] API key not found — "
                f"missing environment variable: {env_key}"
            )

        auth_type = self.auth_config["type"]

        # Auth via request header — e.g. GoldAPI.io uses x-access-token
        if auth_type == "header":
            header_name = self.auth_config["header_name"]
            headers[header_name] = api_key
            logger.info(
                f"[{self.source_id}] Auth applied via header: {header_name}"
            )

        # Auth via query param — e.g. Metals.Dev uses ?api_key=xxx
        elif auth_type == "query_param":
            params["api_key"] = api_key
            logger.info(
                f"[{self.source_id}] Auth applied via query param"
            )

        else:
            raise Exception(
                f"[{self.source_id}] Unknown auth type: {auth_type} — "
                f"must be 'header' or 'query_param'"
            )

        return headers, params

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

        # 401 — bad API key
        if status == 401:
            raise Exception(
                f"[{self.source_id}] Unauthorized (401) — "
                f"check your API key in .env file"
            )

        # 403 — forbidden
        if status == 403:
            raise Exception(
                f"[{self.source_id}] Forbidden (403) — "
                f"API key may not have access to this endpoint"
            )

        # 429 — rate limit hit
        if status == 429:
            raise Exception(
                f"[{self.source_id}] Rate limit exceeded (429) — "
                f"quota may be exhausted for this month"
            )

        # 404 — endpoint not found
        if status == 404:
            raise Exception(
                f"[{self.source_id}] Endpoint not found (404) — "
                f"check the URL in sources.json"
            )

        # 500 — server error on their side
        if status >= 500:
            raise Exception(
                f"[{self.source_id}] Server error ({status}) — "
                f"source may be down temporarily"
            )

        # Any other non-200 status
        raise Exception(
            f"[{self.source_id}] Unexpected status code: {status}"
        )
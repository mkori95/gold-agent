"""
secrets_manager.py

Fetches API keys from AWS Secrets Manager and injects them
into os.environ so all scrapers can access them normally.

Caches secrets in memory after first fetch — Lambda containers
stay warm for ~15 minutes so we only hit Secrets Manager once
per container lifetime.

Secrets stored in AWS:
    gold-agent/metals-dev-api-key
    gold-agent/goldapi-io-key

Usage:
    from src.scrapers.engine.secrets_manager import SecretsManager
    SecretsManager.load()
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Secrets to fetch — maps secret name → env variable name
SECRETS_MAP = {
    "gold-agent/metals-dev-api-key": "METALS_DEV_API_KEY",
    "gold-agent/goldapi-io-key":     "GOLDAPI_IO_KEY"
}

AWS_REGION = "ap-south-1"


class SecretsManager:
    """
    Fetches and caches secrets from AWS Secrets Manager.

    Uses class-level cache so secrets are fetched once
    per Lambda container lifetime — not on every invocation.
    """

    # Class-level cache — shared across all instances
    _loaded = False

    @classmethod
    def load(cls) -> None:
        """
        Fetches all secrets and injects into os.environ.

        Skips if already loaded — cached for container lifetime.
        Skips gracefully if running locally with .env file present.
        """

        # Already loaded — use cache
        if cls._loaded:
            logger.info("Secrets already loaded from cache — skipping")
            return

        # Running locally — .env file handles this
        # Check if keys already set by load_dotenv()
        if os.environ.get("METALS_DEV_API_KEY") and os.environ.get("GOLDAPI_IO_KEY"):
            logger.info("Secrets already in environment — running locally")
            cls._loaded = True
            return

        logger.info("Fetching secrets from AWS Secrets Manager")

        try:
            client = boto3.client(
                "secretsmanager",
                region_name=AWS_REGION
            )

            for secret_name, env_key in SECRETS_MAP.items():
                try:
                    response = client.get_secret_value(
                        SecretId=secret_name
                    )

                    # Set in os.environ so scrapers can read normally
                    os.environ[env_key] = response["SecretString"]

                    logger.info(
                        f"Secret loaded — {secret_name} → {env_key}"
                    )

                except ClientError as e:
                    logger.error(
                        f"Failed to fetch secret {secret_name} — {str(e)}"
                    )
                    raise

            cls._loaded = True
            logger.info("All secrets loaded and cached successfully")

        except Exception as e:
            logger.error(f"SecretsManager.load() failed — {str(e)}")
            raise
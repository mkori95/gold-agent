"""
handler.py

AWS Lambda entry point for the Consolidator.

This is intentionally thin — all business logic lives
in consolidator.py. This file just bridges AWS Lambda
to our Consolidator class.

Lambda is triggered by EventBridge on a schedule:
    - Every 60 minutes for gold_api_com (unlimited)
    - Every 720 minutes for metals_dev + goldapi_io (quota managed)
    - Every 120 minutes for goodreturns

EventBridge event format (standard scheduled event):
    {
        "version": "0",
        "id": "...",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "time": "2026-03-01T14:00:00Z",
        ...
    }

Lambda response format:
    {
        "statusCode": 200,
        "body": { ... consolidator result ... }
    }

Deployment:
    Deployed via Terraform as part of Phase 1 infrastructure.
    Function name: gold-agent-consolidator
    Runtime: python3.12
    Handler: handler.handler
    Timeout: 300 seconds (5 minutes — goodreturns scrapes 28 cities)
    Memory: 256 MB
"""

from dotenv import load_dotenv
load_dotenv()

import json
import logging
from src.lambdas.consolidator.consolidator import Consolidator

# Set up logging — CloudWatch picks this up automatically in Lambda
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)


def handler(event, context):
    """
    AWS Lambda handler function.

    Args:
        event:   EventBridge scheduled event dict
        context: Lambda context object (runtime info)

    Returns:
        Dict with statusCode and body
    """

    logger.info(
        f"Consolidator Lambda triggered — "
        f"event source: {event.get('source', 'unknown')}"
    )

    try:
        consolidator = Consolidator()
        result       = consolidator.run()

        status_code = 200 if result["status"] == "success" else 500

        logger.info(
            f"Consolidator Lambda complete — "
            f"status: {result['status']} — "
            f"metals: {result['metals_count']} — "
            f"duration: {result['duration_seconds']}s"
        )

        return {
            "statusCode": status_code,
            "body":       result
        }

    except Exception as e:
        logger.error(f"Consolidator Lambda failed — {str(e)}")

        return {
            "statusCode": 500,
            "body": {
                "status": "failed",
                "error":  str(e)
            }
        }
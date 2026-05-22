import hashlib
import hmac
import os
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def is_valid_signature(raw_body: bytes, x_hub_signature_256: str) -> bool:
    """
    Meta signs every webhook POST with HMAC-SHA256 using the app secret.
    Header format: sha256=<hex_digest>
    """
    app_secret = os.environ.get("WHATSAPP_APP_SECRET", "")
    if not app_secret:
        # No secret configured — skip validation (dev/test only)
        logger.warning("WHATSAPP_APP_SECRET not set; skipping signature check")
        return True

    if not x_hub_signature_256 or not x_hub_signature_256.startswith("sha256="):
        logger.warning("Missing or malformed X-Hub-Signature-256 header")
        return False

    expected_sig = x_hub_signature_256[len("sha256="):]
    computed_sig = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)

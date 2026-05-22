import os
import json
import urllib.request
import urllib.error
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v19.0"


def _get_token() -> str:
    return os.environ["WHATSAPP_TOKEN"]


def _get_phone_number_id() -> str:
    return os.environ["WHATSAPP_PHONE_NUMBER_ID"]


def send_text(to: str, message: str) -> dict:
    """Send a plain text WhatsApp message."""
    phone_number_id = _get_phone_number_id()
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    return _post(url, payload)


def send_template(to: str, template_name: str, language_code: str = "en", components: list = None) -> dict:
    """Send a WhatsApp template message (must be pre-approved by Meta)."""
    phone_number_id = _get_phone_number_id()
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    template = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if components:
        template["components"] = components
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }
    return _post(url, payload)


def mark_read(message_id: str) -> dict:
    """Mark an incoming message as read (shows blue ticks)."""
    phone_number_id = _get_phone_number_id()
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    return _post(url, payload)


def download_media(media_id: str) -> bytes:
    """Download a WhatsApp media file by ID. Returns raw bytes (OGG/Opus for voice)."""
    token = _get_token()

    # Step 1: resolve the media ID to a download URL
    meta_req = urllib.request.Request(
        f"{GRAPH_API_URL}/{media_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(meta_req, timeout=10) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    download_url = meta["url"]

    # Step 2: download the binary — Meta requires the same auth header
    file_req = urllib.request.Request(
        download_url,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(file_req, timeout=30) as resp:
        return resp.read()


def _post(url: str, payload: dict) -> dict:
    token = _get_token()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            logger.info(f"WhatsApp API response: {result}")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        logger.error(f"WhatsApp API error {e.code}: {body}")
        raise

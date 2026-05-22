"""
whisper-transcriber Lambda — container image.

Invoked async by whatsapp-handler after it uploads the voice OGG to S3.
Event:
  {
    "s3_bucket": "gold-agent-prices",
    "s3_key": "voice-temp/{message_id}.ogg",
    "phone_number": "91XXXXXXXXXX",
    "city": "Hyderabad",
    "language_hint": "te"
  }
Flow: download OGG → ffmpeg → WAV → Whisper base → delete OGG → invoke agent-brain.
"""

import json
import logging
import os
import subprocess
import tempfile

import boto3
import whisper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WHISPER_CACHE = "/var/task/.whisper_cache"
AGENT_BRAIN_FUNCTION = os.environ.get("AGENT_BRAIN_FUNCTION_NAME", "gold-agent-brain")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "ap-south-1")

_model = None
_s3 = None
_lambda_client = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading Whisper base model")
        _model = whisper.load_model("base", download_root=WHISPER_CACHE)
        logger.info("Whisper base model ready")
    return _model


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=AWS_REGION)
    return _s3


def _get_lambda():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client("lambda", region_name=AWS_REGION)
    return _lambda_client


def handler(event: dict, context) -> dict:
    s3_bucket = event["s3_bucket"]
    s3_key = event["s3_key"]
    phone_number = event["phone_number"]
    city = event.get("city", "")
    language_hint = event.get("language_hint", "en")

    s3 = _get_s3()

    with tempfile.TemporaryDirectory() as tmp:
        ogg_path = os.path.join(tmp, "audio.ogg")
        wav_path = os.path.join(tmp, "audio.wav")

        logger.info(f"Downloading s3://{s3_bucket}/{s3_key}")
        s3.download_file(s3_bucket, s3_key, ogg_path)

        # OGG/Opus → WAV 16 kHz mono (Whisper requirement)
        result = subprocess.run(
            ["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
            capture_output=True,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr.decode()}")
            raise RuntimeError("Audio conversion failed")

        output = _get_model().transcribe(wav_path, fp16=False)

    # Delete from S3 immediately — don't wait until after agent-brain invoke
    try:
        s3.delete_object(Bucket=s3_bucket, Key=s3_key)
        logger.info(f"Deleted s3://{s3_bucket}/{s3_key}")
    except Exception as e:
        logger.warning(f"Could not delete voice temp file: {e}")

    text = output["text"].strip()
    detected_language = output.get("language") or language_hint
    logger.info(f"Transcribed: lang={detected_language} text={text[:120]}")

    if not text:
        logger.info("Empty transcription — skipping agent-brain invoke")
        return {"status": "empty"}

    payload = {
        "phone_number": phone_number,
        "message": text,
        "language": detected_language,
        "intent": "unknown",
        "city": city,
    }
    _get_lambda().invoke(
        FunctionName=AGENT_BRAIN_FUNCTION,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    logger.info(f"agent-brain invoked async for {phone_number}")
    return {"status": "ok", "language": detected_language, "text": text}

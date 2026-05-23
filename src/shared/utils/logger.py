import logging
import os


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    # In Lambda, the runtime installs its own handler on the root logger.
    # Adding a second StreamHandler here causes every log line to appear twice.
    # Outside Lambda (local dev/tests), add one so logs actually show up.
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME") and not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
        ))
        logger.addHandler(handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
    return logger

""""""
import logging
import os

DEFAULT_LEVEL = os.getenv("PYBOY_LOG_LEVEL", "INFO").upper()

FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATEFMT = "%H:%M:%S"

_INITIALIZED = False

def init_logger(level: str = DEFAULT_LEVEL) -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    logging.basicConfig(level=level, format=FORMAT, datefmt=DATEFMT)
    logging.getLogger("pika").setLevel(logging.WARNING)
    _INITIALIZED = True

import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")

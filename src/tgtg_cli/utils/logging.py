import logging
from logging.handlers import TimedRotatingFileHandler

from tgtg_cli.cli.config import LOG_FILE_PATH


def get_logger(
    name: str = "TGTG-CLI",
    level: int = logging.DEBUG,
) -> logging.Logger:
    """
    Initializes the logger for the application if it doesn't exist yet or
    returns the existing logger.
    Creates a custom file handler to create new log files every day at midnight
    and adds a custom formatter. Old log files are deleted automatically once
    the backup count is exceeded.

    Args:
        name (str, optional): Name of the logger. Defaults to "TGTG-CLI".
        level (int, optional): Level of the logger. Defaults to logging.DEBUG.

    Returns:
        logging.Logger: Logger object.
    """
    # Check if logger already exists
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    # Set level
    logger.setLevel(level)

    # Create handler that rotates the log files every day
    handler = TimedRotatingFileHandler(
        filename=LOG_FILE_PATH,
        when="midnight",
        backupCount=2,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add formatter to handler and handler to logger
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

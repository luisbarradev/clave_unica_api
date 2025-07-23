
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import logging
import os
import uuid
from functools import wraps

EXECUTION_ID = uuid.uuid4()
_logger_initialized = False


def get_logger(name: str = __name__) -> logging.Logger:
    """Get a logger instance with a standardized format.

    Initializes basic logging configuration if not already done.
    """
    global _logger_initialized
    if not _logger_initialized:
        log_format = f'[%(levelname)s] [%(name)s] {EXECUTION_ID} - %(message)s'
        if os.getenv('LOG_WITH_TIMESTAMP', 'true').lower() == 'true':
            log_format = f'%(asctime)s {log_format}'

        logging.basicConfig(
            level=logging.INFO,
            format=log_format
        )
        _logger_initialized = True
    return logging.getLogger(name)


# Get a default logger for this module
logger = get_logger(__name__)


def log_execution_func(func):
    """Decorate a function to log its execution and handle exceptions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"Executing {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"Finished {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper

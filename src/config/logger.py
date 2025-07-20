
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import logging
import uuid

EXECUTION_ID = uuid.uuid4()

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - %(levelname)s - [{EXECUTION_ID}] - %(message)s'
)


def log_execution_func(func):
    async def wrapper(*args, **kwargs):
        logging.info(f"Executing {func.__name__} with args: {args} and kwargs: {kwargs}")
        result = await func(*args, **kwargs)
        logging.info(f"Finished {func.__name__} with result: {result}")
        return result
    return wrapper
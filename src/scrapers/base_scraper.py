
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    @abstractmethod
    async def run(self) -> Any:
        """Runs the scraper and returns the extracted data."""
        pass

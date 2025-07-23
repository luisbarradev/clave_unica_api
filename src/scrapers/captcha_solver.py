
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import os

from playwright.async_api import Page
from playwright_recaptcha import recaptchav2

from src.config.logger import get_logger

logger = get_logger(__name__)

class RecaptchaSolver:
    """A class to handle reCAPTCHA solving using CapSolver."""

    def __init__(self):
        self.capsolver_api_key = os.getenv("CAPSOLVER_API_KEY")
        if not self.capsolver_api_key:
            logger.error(
                "CAPSOLVER_API_KEY environment variable is not set. "
                "It is required for reCAPTCHA solving."
            )
            raise ValueError(
                "CAPSOLVER_API_KEY environment variable is not set. "
                "It is required for reCAPTCHA solving."
            )

    async def solve(self, page: Page):
        """Solves the reCAPTCHA on the given page."""
        solver = recaptchav2.AsyncSolver(page, capsolver_api_key=self.capsolver_api_key)
        await solver.solve_recaptcha(wait=True, image_challenge=True)

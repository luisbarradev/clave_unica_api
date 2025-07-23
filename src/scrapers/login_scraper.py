
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from playwright.async_api import Page

from src.models.clave_unica import ClaveUnica
from src.scrapers.login_strategies.base_strategy import LoginStrategy


class LoginScraper:
    """A class to handle login operations using a specified login strategy."""

    def __init__(self, strategy: LoginStrategy):
        self.strategy = strategy

    async def do_login(self, page: Page, credentials: ClaveUnica) -> bool:
        """Performs the login operation using the configured strategy."""
        return await self.strategy.do_login(page, credentials)

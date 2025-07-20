
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from abc import ABC, abstractmethod
from playwright.async_api import Page
from src.models.clave_unica import ClaveUnica


class LoginStrategy(ABC):
    @abstractmethod
    async def do_login(self, page: Page, credentials: ClaveUnica) -> bool:
        pass

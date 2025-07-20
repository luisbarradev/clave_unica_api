
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from src.models.clave_unica import ClaveUnica
from playwright.async_api import Page
from src.config.logger import get_logger, log_execution_func

logger = get_logger(__name__)

class LoginScraper:

    def __init__(self, clave_unica: ClaveUnica):
        self.clave_unica = clave_unica

    @log_execution_func
    async def do_login(self, page: Page) -> bool:
        try:
            await page.get_by_role("textbox", name="Ingresa tu RUN").click()
            await page.get_by_role("textbox", name="Ingresa tu RUN").fill(self.clave_unica.rut)
            await page.get_by_role("textbox", name="Ingresa tu ClaveÚnica").click()
            await page.get_by_role("textbox", name="Ingresa tu ClaveÚnica").fill(self.clave_unica._password)
            await page.keyboard.press("Enter")
            await page.get_by_role("button", name="INGRESA").click()
            return True
        except Exception as err:
            logger.error(f"Error during login: {err}", exc_info=True)
            return False

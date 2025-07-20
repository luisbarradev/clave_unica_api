
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from src.scrapers.login_strategies.base_strategy import LoginStrategy
from src.models.clave_unica import ClaveUnica
from playwright.async_api import Page
from src.config.logger import get_logger, log_execution_func
from src.config.config import NETWORK_IDLE_TIMEOUT
from src.utils.exceptions import InvalidCredentialsError, UserBlockedError, UserNotFoundError, UserAlreadyBlockedError

logger = get_logger(__name__)


class ClaveUnicaLoginStrategy(LoginStrategy):
    @log_execution_func
    async def do_login(self, page: Page, credentials: ClaveUnica) -> bool:
        try:
            await page.get_by_role("textbox", name="Ingresa tu RUN").click()
            await page.get_by_role("textbox", name="Ingresa tu RUN").fill(credentials.rut)
            await page.get_by_role("textbox", name="Ingresa tu ClaveÚnica").click()
            await page.get_by_role("textbox", name="Ingresa tu ClaveÚnica").fill(credentials._password)
            await page.keyboard.press("Enter")

            await page.get_by_role("button", name="INGRESA").click()
            await page.wait_for_load_state('networkidle', timeout=NETWORK_IDLE_TIMEOUT)

            invalid_credentials_selector = page.locator(
                "text=Datos de acceso no válidos")
            if await invalid_credentials_selector.is_visible():
                logger.warning("Login failed: Invalid credentials provided.")
                raise InvalidCredentialsError(
                    "Invalid credentials provided for ClaveÚnica.")

            user_blocked_selector = page.locator(
                "text=El usuario será bloqueado al siguiente intento fallido")
            if await user_blocked_selector.is_visible():
                logger.warning(
                    "Login failed: User will be blocked on next attempt.")
                raise UserBlockedError(
                    "User will be blocked due to too many failed login attempts.")

            user_not_found_selector = page.locator(
                "text=Usuario no encontrado")
            if await user_not_found_selector.is_visible():
                logger.warning("Login failed: User not found.")
                raise UserNotFoundError("User not found.")

            user_already_blocked_selector = page.locator(
                "text=Usuario Bloqueado")
            if await user_already_blocked_selector.is_visible():
                logger.warning("Login failed: User is already blocked.")
                raise UserAlreadyBlockedError("User is already blocked.")

            return True
        except (InvalidCredentialsError, UserBlockedError, UserNotFoundError, UserAlreadyBlockedError):
            raise
        except Exception as err:
            logger.error(f"Error during login: {err}", exc_info=True)
            return False

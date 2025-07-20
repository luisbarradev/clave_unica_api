
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

from src.models.clave_unica import ClaveUnica
from playwright.async_api import Page
from src.config.logger import get_logger, log_execution_func
from src.config.config import NETWORK_IDLE_TIMEOUT
from src.utils.exceptions import InvalidCredentialsError, UserBlockedError, UserNotFoundError, UserAlreadyBlockedError

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

            # Click the login button and wait for network to be idle
            await page.get_by_role("button", name="INGRESA").click()
            await page.wait_for_load_state('networkidle', timeout=NETWORK_IDLE_TIMEOUT)

            # Check for invalid credentials message
            invalid_credentials_selector = page.locator("text=Datos de acceso no válidos")
            if await invalid_credentials_selector.is_visible():
                logger.warning("Login failed: Invalid credentials provided.")
                raise InvalidCredentialsError("Invalid credentials provided for ClaveÚnica.")
            
            # Check for user will be blocked message
            user_blocked_selector = page.locator("text=El usuario será bloqueado al siguiente intento fallido")
            if await user_blocked_selector.is_visible():
                logger.warning("Login failed: User will be blocked on next attempt.")
                raise UserBlockedError("User will be blocked due to too many failed login attempts.")

            # Check for user not found message
            user_not_found_selector = page.locator("text=Usuario no encontrado")
            if await user_not_found_selector.is_visible():
                logger.warning("Login failed: User not found.")
                raise UserNotFoundError("User not found.")

            # Check for user already blocked message
            user_already_blocked_selector = page.locator("text=Usuario Bloqueado")
            if await user_already_blocked_selector.is_visible():
                logger.warning("Login failed: User is already blocked.")
                raise UserAlreadyBlockedError("User is already blocked.")
            
            # If none of the error messages are visible, assume successful login
            return True
        except (InvalidCredentialsError, UserBlockedError, UserNotFoundError, UserAlreadyBlockedError):
            raise  # Re-raise the specific error
        except Exception as err:
            logger.error(f"Error during login: {err}", exc_info=True)
            return False


__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import argparse
import asyncio

from playwright.async_api import async_playwright

from src.facades.scraper_facade import ScraperFacade
from src.models.clave_unica import ClaveUnica
from src.scrapers.captcha_solver import RecaptchaSolver
from src.scrapers.login_scraper import LoginScraper


async def main():
    """Run the CLI application."""
    parser = argparse.ArgumentParser(description="CLI para ejecutar scrapers.")
    subparsers = parser.add_subparsers(
        dest="command", help="Comandos disponibles")

    # Subparser para el scraper CMF
    cmf_parser = subparsers.add_parser(
        "cmf", help="Ejecuta el scraper de la CMF")
    cmf_parser.add_argument("--headless", action="store_true",
                            help="Ejecuta el navegador en modo headless")
    cmf_parser.add_argument("--debug", action="store_true",
                            help="Muestra mensajes de depuración")
    cmf_parser.add_argument("--username", required=True,
                            help="Usuario (RUT) para iniciar sesión")
    cmf_parser.add_argument("--password", required=True,
                            help="Contraseña para iniciar sesión")

    # Subparser para el scraper AFC
    afc_parser = subparsers.add_parser(
        "afc", help="Ejecuta el scraper de la AFC")
    afc_parser.add_argument("--headless", action="store_true",
                            help="Ejecuta el navegador en modo headless")
    afc_parser.add_argument("--debug", action="store_true",
                            help="Muestra mensajes de depuración")
    afc_parser.add_argument("--username", required=True,
                            help="Usuario (RUT) para iniciar sesión")
    afc_parser.add_argument("--password", required=True,
                            help="Contraseña para iniciar sesión")

    afc_parser = subparsers.add_parser(
        "sii", help="Ejecuta el scraper de la SII")
    afc_parser.add_argument("--headless", action="store_true",
                            help="Ejecuta el navegador en modo headless")
    afc_parser.add_argument("--debug", action="store_true",
                            help="Muestra mensajes de depuración")
    afc_parser.add_argument("--username", required=True,
                            help="Usuario (RUT) para iniciar sesión")
    afc_parser.add_argument("--password", required=True,
                            help="Contraseña para iniciar sesión")

    args = parser.parse_args()

    if args.command in {"cmf", "afc", "sii"}:
        print(f"Ejecutando scraper {args.command.upper()}...")

        clave_unica = ClaveUnica(rut=args.username, password=args.password)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=args.headless)
            context = await browser.new_context()

            from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy
            login_scraper = LoginScraper(ClaveUnicaLoginStrategy())
            facade = ScraperFacade(
                context=context,
                login_scraper=login_scraper,
                clave_unica=clave_unica,
                captcha_solver=RecaptchaSolver(),
            )

            try:
                data = await facade.scrape(args.command)
                print(f"Scraper {args.command.upper()} ejecutado con éxito. Resultados:")
                print(data)
            except Exception as e:
                print(f"Error al ejecutar el scraper {args.command.upper()}: {e}")
            finally:
                await browser.close()
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())

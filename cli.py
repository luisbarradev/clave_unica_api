
__AUTHOR__ = "Luis Francisco Barra Sandoval"
__EMAIL__ = "contacto@luisbarra.cl"
__VERSION__ = "1.0.0"

import argparse
import asyncio
from playwright.async_api import async_playwright
from src.scrapers.CMF_scraper import CMFScraper
from src.scrapers.AFC_scraper import AFCScraper
from src.scrapers.captcha_solver import RecaptchaSolver
from src.scrapers.login_scraper import LoginScraper
from src.models.clave_unica import ClaveUnica


async def main():
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
    

    args = parser.parse_args()

    if args.command == "cmf":
        print("Ejecutando scraper CMF...")

        clave_unica = ClaveUnica(
            rut=args.username,
            password=args.password
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=args.headless)
            context = await browser.new_context()

            from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy
            login_scraper = LoginScraper(ClaveUnicaLoginStrategy())
            cmf_scraper = CMFScraper(
                context=context, login_scraper=login_scraper, clave_unica=clave_unica)

            try:
                data = await cmf_scraper.run()
                print("Scraper CMF ejecutado con éxito. Resultados:")
                print(data)
            except Exception as e:
                print(f"Error al ejecutar el scraper CMF: {e}")
            finally:
                await browser.close()
    elif args.command == "afc":
        print("Ejecutando scraper AFC...")

        clave_unica = ClaveUnica(
            rut=args.username,
            password=args.password
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=args.headless)
            context = await browser.new_context()

            from src.scrapers.login_strategies.clave_unica_strategy import ClaveUnicaLoginStrategy
            login_scraper = LoginScraper(ClaveUnicaLoginStrategy())
            afc_scraper = AFCScraper(
                context=context, login_scraper=login_scraper, clave_unica=clave_unica, captcha_solver=RecaptchaSolver())

            try:
                data = await afc_scraper.run()
                print("Scraper AFC ejecutado con éxito. Resultados:")
                print(data)
            except Exception as e:
                print(f"Error al ejecutar el scraper AFC: {e}")
            finally:
                await browser.close()
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())

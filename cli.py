import argparse
import asyncio
import sys
from playwright.async_api import async_playwright
from src.scrapers.CMF_scraper import CMFScraper
from src.scrapers.login_scraper import LoginScraper
from src.models.clave_unica import ClaveUnica

async def main():
    parser = argparse.ArgumentParser(description="CLI para ejecutar scrapers.")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Subparser para el scraper CMF
    cmf_parser = subparsers.add_parser("cmf", help="Ejecuta el scraper de la CMF")
    cmf_parser.add_argument("--headless", action="store_true", help="Ejecuta el navegador en modo headless")
    cmf_parser.add_argument("--debug", action="store_true", help="Muestra mensajes de depuración")
    cmf_parser.add_argument("--username", required=True, help="Usuario (RUT) para iniciar sesión")
    cmf_parser.add_argument("--password", required=True, help="Contraseña para iniciar sesión")

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
            
            login_scraper = LoginScraper(clave_unica)
            cmf_scraper = CMFScraper(context=context, login_scraper=login_scraper)
            
            try:
                data = await cmf_scraper.run()
                print("Scraper CMF ejecutado con éxito. Resultados:")
                print(data)
            except Exception as e:
                print(f"Error al ejecutar el scraper CMF: {e}")
            finally:
                await browser.close()
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
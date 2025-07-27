from __future__ import annotations

from playwright.async_api import BrowserContext

from src.models.clave_unica import ClaveUnica
from src.scrapers.AFC_scraper import AFCScraper
from src.scrapers.captcha_solver import RecaptchaSolver
from src.scrapers.CMF_scraper import CMFScraper
from src.scrapers.login_scraper import LoginScraper
from src.scrapers.SII_scraper import SIIScraper


class ScraperFacade:
    """Facade to simplify running different scrapers with a common interface."""

    def __init__(
        self,
        context: BrowserContext,
        login_scraper: LoginScraper,
        clave_unica: ClaveUnica,
        captcha_solver: RecaptchaSolver | None = None,
    ) -> None:
        self.context = context
        self.login_scraper = login_scraper
        self.clave_unica = clave_unica
        self.captcha_solver = captcha_solver

    async def scrape(self, scraper_type: str):
        """Run the requested scraper and return its results."""
        stype = scraper_type.lower()
        if stype == "cmf":
            scraper = CMFScraper(
                context=self.context,
                login_scraper=self.login_scraper,
                clave_unica=self.clave_unica,
            )
        elif stype == "afc":
            if not self.captcha_solver:
                raise ValueError("captcha_solver is required for AFC scraper")
            scraper = AFCScraper(
                context=self.context,
                login_scraper=self.login_scraper,
                clave_unica=self.clave_unica,
                captcha_solver=self.captcha_solver,
            )
        elif stype == "sii":
            if not self.captcha_solver:
                raise ValueError("captcha_solver is required for SII scraper")
            scraper = SIIScraper(
                context=self.context,
                login_scraper=self.login_scraper,
                clave_unica=self.clave_unica,
                captcha_solver=self.captcha_solver,
            )
        else:
            raise ValueError(f"Unknown scraper type: {scraper_type}")

        return await scraper.run()

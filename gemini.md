# Project Context - clave_unica_api

This document summarizes the changes and current state of the `clave_unica_api` project as of July 20, 2025.

## Key Changes Implemented:

1.  **New Scraper: AFCScraper**
    *   Implemented a new scraper (`src/scrapers/AFC_scraper.py`) to extract data from the AFC website.
    *   Handles reCAPTCHA solving.
    *   Extracts "empresas" (companies) and "cotizaciones" (contributions) data.
    *   Automatically scrapes data for the current year, and the two previous years.
    *   Corrected data extraction for contributions, including stripping whitespace from 'period' and parsing monetary values using `parse_money`.

2.  **Common Scraper Interface (BaseScraper)**
    *   Introduced `src/scrapers/base_scraper.py` defining a `BaseScraper` abstract class with a `run()` method.
    *   Both `CMFScraper` and `AFCScraper` now inherit from `BaseScraper` and implement the `run()` method without external parameters (they manage their own `Page` instances).

3.  **DTOs for AFC Scraper**
    *   Created `src/dto/afc_data.py` to define `TypedDict` structures (`AFCEmpresaEntry`, `AFCCotizacionEntry`, `AFCScraperResult`) for type-safe data handling.
    *   Ensured property names are in English.
    *   Corrected type inconsistencies (e.g., `int` instead of `str` for monetary values) based on MyPy checks.

4.  **Separation of Captcha Logic**
    *   Extracted reCAPTCHA solving logic into a dedicated class `RecaptchaSolver` in `src/scrapers/captcha_solver.py`.
    *   `RecaptchaSolver` is now injected into `AFCScraper` for better modularity and testability.

5.  **API Integration (`api/api.py`)**
    *   Added new synchronous (`/scrape/afc`) and asynchronous (`/async/scrape/afc`) endpoints for the `AFCScraper`.
    *   Ensured consistent API response format (`{"status": "success", "data": ...}`).

6.  **CLI Integration (`cli.py`)**
    *   Added a new `afc` subcommand to the CLI for direct execution of the `AFCScraper`.
    *   Removed the `--years` argument from the `afc` subcommand as the scraper now determines the years internally.

7.  **Worker Integration (`src/worker.py`)**
    *   Modified the worker to dynamically select and execute the appropriate scraper (`CMFScraper` or `AFCScraper`) based on the `scraper_type` in the task queue.

8.  **Type Checking (MyPy)**
    *   All relevant files (`api.py`, `cli.py`, `src/worker.py`, `src/scrapers/AFC_scraper.py`, `src/dto/afc_data.py`, `src/scrapers/captcha_solver.py`) have been checked with MyPy, and all type errors have been resolved.
    *   `types-requests` was added to `pyproject.toml` to resolve missing stubs.

## Current Status:

The project is now capable of scraping CMF and AFC data, with the AFC scraper being modular, type-safe, and integrated into both the API and CLI. The reCAPTCHA solving logic is separated for better maintainability. All type-checking issues identified by MyPy have been addressed.

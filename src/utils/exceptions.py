class ScraperError(Exception):
    """Base exception for all scraper-related errors."""
    pass

class ScraperLoginError(ScraperError):
    """Exception raised for errors during the login process."""
    pass

class ScraperDataExtractionError(ScraperError):
    """Exception raised for errors during data extraction."""
    pass

class SelectorNotFoundError(ScraperDataExtractionError):
    """Exception raised when a required selector is not found on the page."""
    pass
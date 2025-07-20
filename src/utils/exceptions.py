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


class InvalidCredentialsError(ScraperLoginError):
    """Exception raised when login credentials are invalid."""
    pass


class UserBlockedError(ScraperLoginError):
    """Exception raised when the user is blocked due to too many failed login attempts."""
    pass


class UserNotFoundError(ScraperLoginError):
    """Exception raised when the user is not found."""
    pass


class UserAlreadyBlockedError(ScraperLoginError):
    """Exception raised when the user is already blocked."""
    pass
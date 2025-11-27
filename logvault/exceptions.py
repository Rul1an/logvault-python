"""
LogVault SDK Exceptions
"""


class LogVaultError(Exception):
    """Base exception for all LogVault errors"""
    pass


class AuthenticationError(LogVaultError):
    """API key is invalid or missing"""
    pass


class RateLimitError(LogVaultError):
    """Rate limit exceeded or monthly quota reached"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(LogVaultError):
    """Request validation failed"""
    pass


class APIError(LogVaultError):
    """API request failed"""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        # Ensure sensitive data (like keys in response) is not inadvertently exposed in str(e)
        # if the response dict is printed directly.
        # For now, we rely on the message being sanitized by the caller.
        super().__init__(message)
        self.status_code = status_code
        # Store response data but don't expose it in __str__ by default
        self.response = response

    def __repr__(self):
        return f"<APIError status={self.status_code}>"

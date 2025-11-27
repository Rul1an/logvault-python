"""
LogVault Python SDK
Audit-Log-as-a-Service client library
"""

from .client import Client, AsyncClient
from .exceptions import (
    LogVaultError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    APIError
)

__version__ = "0.1.0"

__all__ = [
    'Client',
    'AsyncClient',
    'LogVaultError',
    'AuthenticationError',
    'RateLimitError',
    'ValidationError',
    'APIError'
]

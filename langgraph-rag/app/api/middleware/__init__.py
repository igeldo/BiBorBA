"""API middleware for error handling and request processing."""

from .error_handler import (
    safe_error_handler,
    safe_error_handler_sync,
    APIError,
    ValidationError,
    ResourceNotFoundError,
    ExternalServiceError,
    DatabaseError
)

__all__ = [
    "safe_error_handler",
    "safe_error_handler_sync",
    "APIError",
    "ValidationError",
    "ResourceNotFoundError",
    "ExternalServiceError",
    "DatabaseError"
]

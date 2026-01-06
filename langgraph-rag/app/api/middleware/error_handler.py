"""
Error handling middleware for secure API responses.

This module provides decorators and custom exceptions to ensure:
- Sensitive error details stay in logs only
- Client receives generic, safe error messages
- Error IDs enable support debugging
"""

import logging
import functools
import uuid
from typing import Callable, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors that are safe to expose to client"""

    def __init__(self, status_code: int, message: str, error_code: str = None):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        super().__init__(self.message)


class ResourceNotFoundError(APIError):
    """Resource not found - safe to expose"""

    def __init__(self, resource: str, identifier: Any = None):
        msg = f"{resource} not found" + (f": {identifier}" if identifier else "")
        super().__init__(404, msg, "RESOURCE_NOT_FOUND")


class ValidationError(APIError):
    """Validation error - safe to expose"""

    def __init__(self, message: str):
        super().__init__(400, message, "VALIDATION_ERROR")


class ExternalServiceError(APIError):
    """External service unavailable - safe to expose"""

    def __init__(self, service_name: str):
        super().__init__(503, f"{service_name} service unavailable", "SERVICE_UNAVAILABLE")


class DatabaseError(APIError):
    """Database operation failed - generic message only"""

    def __init__(self):
        super().__init__(500, "Database operation failed", "DATABASE_ERROR")


def safe_error_handler(func: Callable):
    """
    Decorator for secure error handling in async API endpoints.

    - HTTPException passes through unchanged
    - APIError subclasses are converted to safe HTTPException
    - All other exceptions are caught and logged with full details,
      but only a generic message is returned to the client
    - Each error gets a unique ID for support correlation

    Usage:
        @router.post("/endpoint")
        @safe_error_handler
        async def my_endpoint():
            # No try-except needed!
            result = await some_service.do_something()
            return result
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        error_id = str(uuid.uuid4())[:8]

        try:
            return await func(*args, **kwargs)

        except HTTPException:
            raise

        except APIError as e:
            logger.warning(
                f"[{error_id}] {func.__name__}: {e.message}",
                extra={"error_code": e.error_code}
            )
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "message": e.message,
                    "error_code": e.error_code,
                    "error_id": error_id
                }
            )

        except Exception as e:
            logger.error(
                f"[{error_id}] Unhandled exception in {func.__name__}: {type(e).__name__}",
                exc_info=True,
                extra={
                    "exception_type": type(e).__name__,
                    "error_id": error_id
                }
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "An internal error occurred",
                    "error_code": "INTERNAL_ERROR",
                    "error_id": error_id
                }
            )

    return wrapper


def safe_error_handler_sync(func: Callable):
    """
    Decorator for secure error handling in synchronous API endpoints.

    Same behavior as safe_error_handler but for non-async functions.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        error_id = str(uuid.uuid4())[:8]

        try:
            return func(*args, **kwargs)

        except HTTPException:
            raise

        except APIError as e:
            logger.warning(
                f"[{error_id}] {func.__name__}: {e.message}",
                extra={"error_code": e.error_code}
            )
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "message": e.message,
                    "error_code": e.error_code,
                    "error_id": error_id
                }
            )

        except Exception as e:
            logger.error(
                f"[{error_id}] Unhandled exception in {func.__name__}: {type(e).__name__}",
                exc_info=True,
                extra={
                    "exception_type": type(e).__name__,
                    "error_id": error_id
                }
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "An internal error occurred",
                    "error_code": "INTERNAL_ERROR",
                    "error_id": error_id
                }
            )

    return wrapper

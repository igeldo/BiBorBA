# utils/timing.py
"""Simple timing utilities for performance debugging"""

import time
import logging
from functools import wraps
from typing import Callable, Any

def log_timing(operation_name: str = None):
    """
    Simple decorator to log execution time at DEBUG level

    Usage:
        @log_timing("My operation")
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            op_name = operation_name or func.__name__

            start_time = time.perf_counter()
            logger.debug(f"⏱️  START: {op_name}")

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"✅ DONE: {op_name} - {duration_ms:.1f}ms")
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"❌ ERROR: {op_name} - {duration_ms:.1f}ms - {e}")
                raise

        return wrapper
    return decorator


class TimingContext:
    """Context manager for timing code blocks"""

    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.debug(f"⏱️  START: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        if exc_type is None:
            self.logger.debug(f"✅ DONE: {self.name} - {duration_ms:.1f}ms")
        else:
            self.logger.debug(f"❌ ERROR: {self.name} - {duration_ms:.1f}ms - {exc_val}")
        return False

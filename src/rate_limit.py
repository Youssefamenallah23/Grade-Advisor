"""
Rate limiting and exponential backoff retry utilities for Gemini API calls.
Shared across extract.py and agent.py to handle free-tier RPM/RPD limits reliably.
"""

import time
import random
import logging
from typing import Callable, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rate_limit")


def retry_with_backoff(
    func: Callable,
    max_retries: int = 5,
    initial_delay: float = 4.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0
) -> Any:
    """
    Executes func with exponential backoff and jitter upon encountering rate limits
    or transient API errors.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            err_msg = str(e).lower()
            
            # Identify rate limit or transient errors
            is_rate_limit = any(term in err_msg for term in [
                "429", "resource_exhausted", "quota", "rate limit",
                "too many requests", "503", "unavailable", "timeout"
            ])
            
            if attempt == max_retries:
                logger.error(f"Exceeded max retries ({max_retries}). Last error: {e}")
                raise e

            if is_rate_limit:
                jitter = random.uniform(0.5, 1.5)
                sleep_time = min(delay * jitter, max_delay)
                logger.warning(
                    f"Rate limit / transient error on attempt {attempt}/{max_retries}: {e}. "
                    f"Retrying in {sleep_time:.2f}s..."
                )
                time.sleep(sleep_time)
                delay *= backoff_factor
            else:
                logger.error(f"Non-retryable or unexpected error encountered: {e}")
                raise e

    raise last_exception or RuntimeError("Retry loop ended without result")


class RateLimiter:
    """
    Simple sliding/interval rate limiter to enforce max requests per minute (RPM).
    Free tier limit is ~10-15 RPM; a default spacing of 4.5 seconds safely stays under 13 RPM.
    """
    def __init__(self, min_interval_seconds: float = 4.5):
        self.min_interval = min_interval_seconds
        self.last_call_time = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            sleep_needed = self.min_interval - elapsed
            logger.debug(f"Pacing request: sleeping {sleep_needed:.2f}s to respect RPM...")
            time.sleep(sleep_needed)
        self.last_call_time = time.time()

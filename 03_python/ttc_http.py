"""
TTC HTTP — Retry wrapper for Anthropic API calls.
Handles 529 (overloaded) and 5xx by retrying with backoff.
"""

import time
import urllib.request
import urllib.error


def urlopen_with_retry(req: urllib.request.Request, timeout: int = 120, max_retries: int = 3):
    """
    Open the request with retries on 529 and 5xx.
    Backoff: 2s, 4s, 8s between attempts.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last_error = e
            retryable = e.code == 529 or (500 <= e.code < 600)
            if retryable and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error

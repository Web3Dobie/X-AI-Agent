# rate_limit_manager.py
"""
Manages the application's awareness of the X API's 24-hour post limit
by maintaining the limit state in memory based on API response headers.

Includes a fallback mechanism to reset stale state after 24 hours.
"""
import logging
import time
from datetime import datetime, timezone

class RateLimitState:
    """A simple class to hold the current rate limit state in memory."""
    def __init__(self):
        self.remaining = 17  # Start with the full quota
        self.reset_timestamp = 0
        self.last_updated = None

# Create a single, shared instance for the entire application
rate_limit_state = RateLimitState()

def update_rate_limit_state_from_headers(headers):
    """Parses headers from a response and updates the global state."""
    if 'x-app-limit-24hour-remaining' in headers:
        rate_limit_state.remaining = int(headers['x-app-limit-24hour-remaining'])
        rate_limit_state.reset_timestamp = int(headers['x-app-limit-24hour-reset'])
        rate_limit_state.last_updated = time.monotonic()
        
        logging.info(
            f"📊 Rate limit state updated: {rate_limit_state.remaining} posts remaining. "
            f"Resets at {datetime.fromtimestamp(rate_limit_state.reset_timestamp, tz=timezone.utc).isoformat()}"
        )

def is_rate_limited():
    """
    Checks our internal state to see if the limit is reached.
    Includes a fallback to reset stale state older than 24 hours.
    """
    # FRESH START CHECK: If we've never tracked a post, we're not limited
    if rate_limit_state.last_updated is None and rate_limit_state.reset_timestamp == 0:
        logging.info("Rate limit state is fresh (never updated). Not limited.")
        return False
    
    # Stale State Check: If the state hasn't been updated in over 24 hours
    if rate_limit_state.last_updated and (time.monotonic() - rate_limit_state.last_updated) > 86400:
        logging.warning("Rate limit state is stale (older than 24 hours). Forcing a reset to default values.")
        rate_limit_state.remaining = 17
        rate_limit_state.reset_timestamp = 0
        rate_limit_state.last_updated = None
        return False

    # Check if the reset time from the API is in the past
    if rate_limit_state.reset_timestamp != 0 and time.time() > rate_limit_state.reset_timestamp:
        logging.info("Rate limit window has reset based on API timestamp.")
        # Reset the state since window has passed
        rate_limit_state.remaining = 17
        rate_limit_state.reset_timestamp = 0
        return False
    
    # If the window has not reset, check if we have any posts left
    is_limited = rate_limit_state.remaining <= 0
    if is_limited:
        logging.warning(
            f"Rate limit active: remaining={rate_limit_state.remaining}, "
            f"reset_at={datetime.fromtimestamp(rate_limit_state.reset_timestamp, tz=timezone.utc).isoformat() if rate_limit_state.reset_timestamp else 'unknown'}, "
            f"last_updated={rate_limit_state.last_updated}"
        )
    
    return is_limited

def decrement_rate_limit_counter():
    """Manually decrements the remaining posts counter after a successful post."""
    if rate_limit_state.remaining > 0:
        rate_limit_state.remaining -= 1
        # Update the timestamp on every decrement to prevent the state from becoming stale
        rate_limit_state.last_updated = time.monotonic()
        
    logging.info(f"📊 Rate limit counter decremented. Posts remaining (local estimate): {rate_limit_state.remaining}")
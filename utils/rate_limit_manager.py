# rate_limit_manager.py
"""
Manages the application's awareness of the X API's 24-hour post limit
by maintaining the limit state in memory based on API response headers.
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
    """Checks our internal state to see if the limit is reached."""
    # Check if the reset time is in the past. If so, we are not limited.
    if rate_limit_state.reset_timestamp != 0 and time.time() > rate_limit_state.reset_timestamp:
        logging.info("Rate limit window has reset.")
        return False
    
    # If the window has not reset, check if we have any posts left.
    is_limited = rate_limit_state.remaining <= 0
    if is_limited:
        logging.warning("Local state indicates rate limit is active.")
    
    return is_limited

def decrement_rate_limit_counter():
    """Manually decrements the remaining posts counter after a successful post."""
    if rate_limit_state.remaining > 0:
        rate_limit_state.remaining -= 1
    logging.info(f"📊 Rate limit counter decremented. Posts remaining (local estimate): {rate_limit_state.remaining}")
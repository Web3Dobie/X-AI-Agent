# rate_limit_manager.py
"""
Manages the application's awareness of the X API's 24-hour post limit
by maintaining the limit state in memory based on API response headers.

Includes a fallback mechanism to reset stale state after 24 hours.
"""
import logging
import time
from datetime import datetime, timezone

# Initialize logger at module level
logger = logging.getLogger(__name__)

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
    """Check with calendar-based daily reset"""
    
    # Get current UTC date
    now_utc = datetime.now(timezone.utc)
    current_day = now_utc.date()
    
    # Check if we need to reset for new day
    if rate_limit_state.last_updated:
        last_update_time = datetime.fromtimestamp(rate_limit_state.last_updated, tz=timezone.utc)
        last_update_day = last_update_time.date()
        
        if last_update_day < current_day:
            # New day! Reset counter
            logger.info(f"📅 New day detected. Resetting rate limit counter from {rate_limit_state.remaining} to 17")
            rate_limit_state.remaining = 17
            rate_limit_state.last_updated = time.time()  # Use real time, not monotonic
            rate_limit_state.reset_timestamp = 0
            return False
    
    # Check if over limit
    if rate_limit_state.remaining <= 0:
        logger.warning(
            f"Rate limit active: remaining={rate_limit_state.remaining}"
        )
        return True
    
    return False

def decrement_rate_limit_counter():
    """Decrement counter using real timestamps"""
    if rate_limit_state.remaining > 0:
        rate_limit_state.remaining -= 1
        rate_limit_state.last_updated = time.time()  # Use real time, not monotonic
        
        logger.info(
            f"📊 Rate limit counter decremented. Posts remaining: {rate_limit_state.remaining}"
        )
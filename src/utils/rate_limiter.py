import time
import asyncio
import logging

class RateLimiter:
    def __init__(self, calls_per_second):
        self.calls_per_second = calls_per_second
        self.last_call = 0
        self.logger = logging.getLogger(__name__)

    async def wait(self):
        try:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call
            if time_since_last_call < 1 / self.calls_per_second:
                wait_time = 1 / self.calls_per_second - time_since_last_call
                self.logger.debug(f"Rate limiting: waiting for {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
            self.last_call = time.time()
        except Exception as e:
            self.logger.exception("Error in rate limiter")
            raise

#!/usr/bin/env python3
"""Quick test of pondside.telemetry."""

import logging
import time

from pondside.telemetry import init, get_tracer

# Initialize telemetry
init("test-script")

# Get a logger and tracer
logger = logging.getLogger(__name__)
tracer = get_tracer()

# Test basic logging
logger.info("Test log message - should appear in Logfire")

# Test span with nested logging
with tracer.start_as_current_span("test-span"):
    logger.info("Log inside span - should nest under test-span")
    time.sleep(0.1)  # Give it a moment
    logger.info("Another log inside span")

logger.info("Log after span - should be standalone")

print("Done! Check Logfire for 'test-script' service.")

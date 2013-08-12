"""
Perform global initialization.
"""

# Configure the logger
import logging

CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.WARNING)
logging.getLogger('').addHandler(CONSOLE_HANDLER)

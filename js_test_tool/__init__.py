"""
Perform global initialization.
"""

VERSION = '0.0.9'
DESCRIPTION = 'Run JavaScript test suites and collect coverage information.'

# Configure the logger
import logging

CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.WARNING)
CONSOLE_HANDLER.setFormatter(logging.Formatter(fmt='%(levelname)s: %(message)s'))
logging.getLogger('').addHandler(CONSOLE_HANDLER)

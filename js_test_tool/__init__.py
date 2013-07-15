"""
Perform global initialization.
"""

# Configure the logger
# All messages are logged a log file,
# but warnings and above are also logged to stdout
import logging
logging.basicConfig(filename="js_test_tool.log", level=logging.DEBUG)

CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.WARNING)
logging.getLogger('').addHandler(CONSOLE_HANDLER)

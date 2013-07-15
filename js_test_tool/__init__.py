# Configure the logger
# All messages are logged a log file,
# but warnings and above are also logged to stdout
import logging
logging.basicConfig(filename="js_test_tool.log", level=logging.DEBUG)

console = logging.StreamHandler()
console.setLevel(logging.WARNING)
logging.getLogger('').addHandler(console)

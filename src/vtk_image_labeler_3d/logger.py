import logging
import os
from datetime import datetime

from config import get_config
cfg = get_config()
print(f'cfg={cfg}')
log_dir = cfg["log_dir"] 

print(f'log_dir={log_dir}')

# Define log directory
LOG_DIR = log_dir
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Define log file name with timestamp
log_filename = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# Set up logger
logger = logging.getLogger("app_logger")
logger.setLevel(logging.DEBUG)  # Change to logging.INFO if you don't want debug messages

# Formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# File Handler
file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Function to log an exception
def log_exception(e):
    logger.error("Exception occurred", exc_info=e)

def log_and_raise_exception(e):
    logger.error("Exception occurred", exc_info=e)
    raise e

def _info(msg):
    logger.info(msg)

def _err(msg):
    logger.error(msg)

   
# Example usage:
if __name__ == "__main__":
    logger.info("Logger initialized")
    try:
        1 / 0  # Intentional error
    except Exception as e:
        log_exception(e)

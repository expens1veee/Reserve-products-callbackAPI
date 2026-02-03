import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("app_logger")

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Простой вывод в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, log_level))
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


log_file_path = os.getenv("LOG_FILE_PATH", "app.log")
if log_file_path:
    max_log_size = int(os.getenv("LOG_MAX_SIZE_BYTES", "5000000"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "2"))
    
    file_handler = RotatingFileHandler(log_file_path, maxBytes=max_log_size, backupCount=backup_count)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
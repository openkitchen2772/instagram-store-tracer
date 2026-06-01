import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Ensure logs folder exist or create if not
project_root = Path(__file__).resolve().parent.parent
logs_folder_path = project_root / "logs"
logs_folder_path.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("instagram_store_tracer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )   

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    logs_file_path = logs_folder_path / "app.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(logs_file_path),
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(log_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

logger.info(f"Main logger initiated. <PID: {os.getpid()}>")
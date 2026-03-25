import json
import logging
import logging.config
import os
from pathlib import Path


def setup_logging() -> None:
    # 設定ファイルのパス設定
    current_dir = Path(__file__).parent
    config_path = os.path.join(current_dir, "logging.config.json")

    # loggingの設定
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"logging config file not found: file {config_path}")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

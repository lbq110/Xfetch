"""基础模块类 - 所有模块的抽象基类"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


class BaseModule(ABC):
    """所有模块的基类"""

    def __init__(self, config_path: str) -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logger()

    def _load_config(self) -> dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _setup_logger(self) -> logging.Logger:
        """设置日志（控制台 + 文件）"""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"{self.__class__.__name__.lower()}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def load_json(self, file_path: str) -> Any:
        """加载 JSON 文件，文件不存在时返回 None"""
        path = Path(file_path)
        if not path.exists():
            self.logger.warning(f"文件不存在: {file_path}")
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_json(self, data: Any, file_path: str) -> None:
        """保存 JSON 文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"保存文件: {file_path}")

    def get_timestamp_filename(self, extension: str = "json") -> str:
        """生成带时间戳的文件名，格式: 2026-01-14_20.json"""
        return f"{datetime.now().strftime('%Y-%m-%d_%H')}.{extension}"

    @abstractmethod
    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """运行模块，返回输出文件路径或 None"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config_path})"

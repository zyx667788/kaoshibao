"""统一日志配置模块"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime


def setup_logging(
    name: str = "kaoshibao",
    level: str = "INFO",
    log_dir: Path = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    配置结构化日志

    Args:
        name: logger名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志文件目录，None则只输出到控制台
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件Handler（如果指定了log_dir）
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # 普通日志文件（按大小轮转）
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{name}.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 错误日志单独文件
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{name}_error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str = "kaoshibao") -> logging.Logger:
    """获取已配置的logger"""
    return logging.getLogger(name)


# 初始化默认logger
_logger = None

def init_default_logger(log_dir: Path = None, level: str = None) -> logging.Logger:
    """初始化默认logger（应用启动时调用一次）"""
    global _logger
    if level is None:
        level = os.environ.get('LOG_LEVEL', 'INFO')
    if log_dir is None:
        log_dir = Path(__file__).parent / "logs"
    _logger = setup_logging("kaoshibao", level, log_dir)
    return _logger
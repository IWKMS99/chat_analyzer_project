# === Standard library ===
import logging
import os
from typing import Optional


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None) -> None:
    """Настраивает базовую конфигурацию логирования."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    handlers = [logging.StreamHandler()]  # По умолчанию выводим в консоль
    if log_file:
        # Убедимся, что директория для лог-файла существует
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    logging.info(f"Логирование настроено на уровень {log_level.upper()}.")
    if log_file:
        logging.info(f"Логи также записываются в файл: {log_file}")


def ensure_dir(path: str) -> None:
    """Убеждается, что директория существует, и создает ее при необходимости."""
    if path and not os.path.exists(path):
        try:
            os.makedirs(path)
            logging.info(f"Создана директория: {path}")
        except OSError as e:
            logging.error(f"Не удалось создать директорию {path}: {e}")

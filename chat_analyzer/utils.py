# === Standard library ===
import functools
import logging
import os
import re
import warnings
from typing import Callable, Optional, Sequence, Tuple

# === Visualization ===
import matplotlib.pyplot as plt

# === Data handling ===
import pandas as pd

_TIME_WINDOW_UNITS = {
    "h": "h",
    "hr": "h",
    "hour": "h",
    "hours": "h",
    "m": "min",
    "min": "min",
    "mins": "min",
    "minute": "min",
    "minutes": "min",
    "s": "s",
    "sec": "s",
    "secs": "s",
    "second": "s",
    "seconds": "s",
    "d": "D",
    "day": "D",
    "days": "D",
    "t": "min",
}


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Настраивает базовую конфигурацию логирования."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    handlers = [logging.StreamHandler()]
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # Suppress noisy third-party debug logs.
    for noisy_logger in ("matplotlib", "PIL", "spacy"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logging.info("Логирование настроено на уровень %s.", log_level.upper())
    if log_file:
        logging.info("Логи также записываются в файл: %s", log_file)


def ensure_dir(path: str) -> None:
    """Убеждается, что директория существует, и создает ее при необходимости."""
    if path and not os.path.exists(path):
        try:
            os.makedirs(path)
            logging.info("Создана директория: %s", path)
        except OSError as exc:
            logging.error("Не удалось создать директорию %s: %s", path, exc)


def require_non_empty_df(
    df: Optional[pd.DataFrame],
    logger: logging.Logger,
    context: str,
    required_columns: Optional[Sequence[str]] = None,
) -> bool:
    """Проверяет, что DataFrame не пуст и содержит необходимые колонки."""
    if df is None or df.empty:
        logger.warning("Нет данных для %s.", context)
        return False

    if required_columns:
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            logger.error("Отсутствуют необходимые столбцы для %s: %s", context, missing)
            return False

    return True


def finalize_plot(
    logger: logging.Logger,
    save_path: Optional[str] = None,
    plot_name: str = "график",
) -> None:
    """Deprecated matplotlib helper."""
    warnings.warn(
        "finalize_plot deprecated: используйте chat_analyzer.plotting.base.finalize_plotly_figure",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            logger.info("%s сохранен в %s", plot_name.capitalize(), save_path)
    except Exception as exc:  # pragma: no cover - defensive log
        logger.error("Не удалось сохранить %s в %s: %s", plot_name, save_path, exc)
    finally:
        plt.close()


def managed_plot(plot_name: str) -> Callable:
    """Deprecated matplotlib decorator."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                "managed_plot deprecated: используйте plotly plotting helpers",
                DeprecationWarning,
                stacklevel=2,
            )
            logger = logging.getLogger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive log
                log_exception(logger, f"Ошибка при отрисовке ({plot_name}): {exc}", exc)
            finally:
                plt.close()
            return None

        return wrapper

    return decorator


def finalize_plotly_html_path(output_dir: str, chart_name: str) -> str:
    return os.path.join(output_dir, "charts", f"{chart_name}.html")


def finalize_plotly_png_path(output_dir: str, chart_name: str) -> str:
    return os.path.join(output_dir, "charts", f"{chart_name}.png")


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """Логирует исключение со стеком только в DEBUG режиме."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.error(message, exc_info=True)
    else:
        logger.error("%s: %s", message, exc)


def normalize_time_window(time_window: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Нормализует строку временного окна к формату, совместимому с pandas>=3.

    Returns:
        (normalized_window, error_message)
    """
    if time_window is None:
        return None, "Пустое временное окно."

    raw = str(time_window).strip()
    if not raw:
        return None, "Пустое временное окно."

    match = re.fullmatch(r"(?P<num>\d+)\s*(?P<unit>[A-Za-z]+)", raw)
    if not match:
        return None, f"Не удалось распознать формат временного окна: {time_window}"

    num = int(match.group("num"))
    if num <= 0:
        return None, f"Временное окно должно быть положительным: {time_window}"

    unit = match.group("unit").lower()
    mapped_unit = _TIME_WINDOW_UNITS.get(unit)
    if mapped_unit is None:
        return None, f"Неподдерживаемая единица временного окна: {time_window}"

    normalized = f"{num}{mapped_unit}"

    # Validate against pandas parser.
    try:
        pd.tseries.frequencies.to_offset(normalized)
    except ValueError as exc:
        return None, f"Некорректное временное окно {time_window}: {exc}"

    return normalized, None

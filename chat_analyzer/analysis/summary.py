# === Standard library ===
import logging
from typing import Optional

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt

from chat_analyzer.utils import finalize_plot, require_non_empty_df

logger = logging.getLogger(__name__)


def summarize_chat(df: pd.DataFrame, save_path: Optional[str] = None) -> None:
    """
    Выводит ключевые метрики чата и строит бар-чарт топ-10 авторов.
    Предполагается, что timezone уже нормализована в main.py.
    """
    if not require_non_empty_df(df, logger, "summarize_chat", required_columns=["date", "from"]):
        return
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        logger.error("Столбец 'date' отсутствует или имеет некорректный тип для summarize_chat.")
        return

    metrics = {
        "Всего сообщений": len(df),
        "Первое сообщение": df["date"].min().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "Последнее сообщение": df["date"].max().strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    logger.info("\n--- Сводка по чату ---\n%s\n%s", pd.Series(metrics), "-" * 20)

    try:
        top_users = df["from"].value_counts().head(10)
        if top_users.empty:
            logger.warning("Нет данных для построения графика топ-10 авторов.")
            return

        plt.figure(figsize=(8, 5))
        top_users.plot.barh(color="teal")
        plt.title("Топ-10 активных авторов")
        plt.xlabel("Число сообщений")
        plt.ylabel("Автор")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        finalize_plot(logger, save_path, "график топ-10 авторов")
    except Exception as exc:
        logger.error(f"Ошибка при построении графика топ-10 авторов: {exc}", exc_info=True)
        plt.close()

# === Standard library ===
import logging
from typing import Optional

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def summarize_chat(df: pd.DataFrame, timezone: str = 'Europe/Brussels', save_path: Optional[str] = None) -> None:
    """
    Выводит ключевые метрики чата и строит бар-чарт топ-10 авторов.

    Args:
        df: DataFrame с данными чата (ожидаются столбцы 'date', 'from').
        timezone: Временная зона для конвертации дат (по умолчанию 'Europe/Brussels').
        save_path: Путь для сохранения графика (если None, график не сохраняется).

    Metrics:
        - Общее число сообщений.
        - Дата первого и последнего сообщения в указанной временной зоне.
    """
    if df is None or df.empty:
        logger.warning("Нет данных для сводки (summarize_chat).")
        return

    if 'date' not in df or not pd.api.types.is_datetime64_any_dtype(df['date']):
        logger.error("Столбец 'date' отсутствует или имеет некорректный тип для summarize_chat.")
        return
    if 'from' not in df:
        logger.error("Столбец 'from' отсутствует для summarize_chat.")
        return

    # Конвертация времени без модификации исходного DataFrame
    try:
        # Убедимся, что 'date' имеет информацию о временной зоне (должна быть UTC из data_loader)
        if df['date'].dt.tz is None:
            date_local = df['date'].dt.tz_localize('UTC').dt.tz_convert(timezone)
            logger.warning("Столбец 'date' не имел временной зоны. Предполагается UTC.")
        else:
            date_local = df['date'].dt.tz_convert(timezone)
    except Exception as e:
        logger.error(f"Ошибка конвертации времени в {timezone}: {e}")
        # Попробуем использовать UTC как запасной вариант
        try:
            date_local = df['date'].dt.tz_convert('UTC')
            logger.warning("Используется UTC вместо запрошенной временной зоны из-за ошибки.")
        except Exception as e_utc:
            logger.error(f"Не удалось конвертировать время даже в UTC: {e_utc}. Даты не будут отображены.")
            date_local = None  # Не можем отобразить даты

    # Формирование метрик
    metrics = [
        ('Всего сообщений', len(df)),
    ]
    if date_local is not None:
        metrics.extend([
            ('Первое сообщение', date_local.min().strftime('%Y-%m-%d %H:%M:%S %Z') if not date_local.empty else 'N/A'),
            ('Последнее сообщение',
             date_local.max().strftime('%Y-%m-%d %H:%M:%S %Z') if not date_local.empty else 'N/A'),
        ])
    else:
        metrics.extend([
            ('Первое сообщение', 'Ошибка даты'),
            ('Последнее сообщение', 'Ошибка даты'),
        ])

    summary_series = pd.Series(dict(metrics))
    print("\n--- Сводка по чату ---")
    print(summary_series)
    print("-" * 20)

    # Топ-10 авторов
    try:
        top_users = df['from'].value_counts().head(10)
        if top_users.empty:
            logger.warning("Нет данных для построения графика топ-10 авторов.")
            return

        plt.figure(figsize=(8, 5))
        top_users.plot.barh(color='teal')
        plt.title('Топ-10 активных авторов')
        plt.xlabel('Число сообщений')
        plt.ylabel('Автор')
        plt.gca().invert_yaxis()
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График топ-10 авторов сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график топ-10 авторов в {save_path}: {e}")
        # plt.show() # Убрано, чтобы не блокировать выполнение скрипта
        plt.close()  # Закрываем фигуру, чтобы освободить память
    except Exception as e:
        logger.error(f"Ошибка при построении графика топ-10 авторов: {e}")

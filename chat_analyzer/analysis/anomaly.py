# === Standard library ===
import logging
from typing import Optional

# === Data handling & Stats ===
import pandas as pd
from scipy.stats import zscore

# === Visualization ===
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def analyze_anomalous_days(df: pd.DataFrame, threshold: float = 2.0, save_path: Optional[str] = None) -> None:
    """
    Находит и визуализирует дни с аномально высокой активностью.

    Args:
        df: DataFrame с данными чата (ожидаются столбцы 'date_only', 'from', 'text').
        threshold: Порог Z-оценки для определения аномалии.
        save_path: Путь для сохранения графика.
    """
    if df is None or df.empty:
        logger.warning("Нет данных для анализа аномальных дней.")
        return

    required_columns = ['date_only', 'from', 'text']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_anomalous_days: {required_columns}")
        return

    try:
        # Подсчет сообщений по дням
        daily_counts = df.groupby('date_only').size().rename('msg_count')

        if daily_counts.empty:
            logger.warning("Нет данных по дням для расчета Z-оценки.")
            return

        # Если данных мало, Z-оценка может быть неинформативна
        if len(daily_counts) < 5:  # Произвольный порог
            logger.warning("Слишком мало дней для надежного анализа аномалий.")
            spikes = pd.Series(dtype=float)  # Пустая серия
        else:
            # Вычисление Z-score
            # Обрабатываем возможный случай с нулевым стандартным отклонением
            if daily_counts.std() == 0:
                zs = pd.Series(0, index=daily_counts.index)  # Все Z-оценки равны 0
                logger.warning("Стандартное отклонение дневной активности равно 0. Аномалии не могут быть найдены.")
            else:
                zs = zscore(daily_counts.fillna(0))

            # Находим дни, где Z-оценка превышает порог
            spikes = daily_counts[zs > threshold]

        print("\n--- Анализ аномальных дней ---")
        if not spikes.empty:
            print(f"Аномальные дни (Z-score > {threshold}) с повышенной активностью:")
            print(spikes)
        else:
            print(f"Аномальных дней с активностью выше порога Z-score={threshold} не найдено.")

        # Визуализация
        plt.figure(figsize=(14, 7))
        daily_counts.index = pd.to_datetime(
            daily_counts.index)  # Преобразуем индекс в datetime для корректного отображения
        plt.plot(daily_counts.index, daily_counts, label='Сообщения по дням', color='blue', alpha=0.6, marker='.',
                 linestyle='-')

        if not spikes.empty:
            spikes.index = pd.to_datetime(spikes.index)  # Преобразуем индекс в datetime
            plt.scatter(spikes.index, spikes, color='red', label=f'Аномальные дни (Z > {threshold})', zorder=5, s=50)

        plt.title('Ежедневная активность и аномальные дни', fontsize=16)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График аномальных дней сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график аномальных дней в {save_path}: {e}")
        # plt.show()
        plt.close()

        # Анализ содержимого аномальных дней (если они есть)
        if not spikes.empty:
            print("\nПримеры сообщений в аномальные дни (макс. 5 на день):")
            for date in spikes.index:
                # Используем исходный индекс date_only (не datetime) для фильтрации df
                date_only_format = date.date()
                print(f"\nДата: {date_only_format}")
                sample_msgs = df[df['date_only'] == date_only_format][['from', 'text']].head(5)
                if sample_msgs.empty:
                    print("  (Нет примеров сообщений)")
                else:
                    for _, row in sample_msgs.iterrows():
                        # Ограничиваем длину текста для вывода
                        text_preview = str(row['text'])[:100] + ('...' if len(str(row['text'])) > 100 else '')
                        print(f"  {row['from']}: {text_preview}")
        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе аномальных дней: {e}", exc_info=True)
        plt.close()

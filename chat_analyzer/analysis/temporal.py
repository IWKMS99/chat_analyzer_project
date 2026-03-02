# === Standard library ===
import logging
from typing import Optional

# === Data handling & Stats ===
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

# === Visualization ===
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


def calculate_response_time(df: pd.DataFrame, max_interval_minutes: float = 60) -> Optional[float]:
    """
    Вычисляет среднее время ответа в минутах между сообщениями *разных* авторов.

    Args:
        df: DataFrame с данными чата (ожидаются 'date', 'from_id').
        max_interval_minutes: Максимальный интервал для учета как ответа (в минутах).

    Returns:
        Среднее время ответа в минутах или None, если рассчитать не удалось.
    """
    if df is None or df.empty:
        logger.warning("Нет данных для расчёта времени ответа.")
        return None

    required_columns = ['date', 'from_id']  # Используем from_id для стабильности
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для calculate_response_time: {required_columns}")
        return None

    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        logger.error("Столбец 'date' должен быть типа datetime для calculate_response_time.")
        return None

    # Требуется как минимум 2 сообщения для расчета разницы
    if len(df) < 2:
        logger.warning("Недостаточно сообщений (<2) для расчета времени ответа.")
        return 0.0  # Можно вернуть 0 или None

    try:
        df_sorted = df.sort_values('date').copy()  # Работаем с копией

        # Сдвигаем 'from_id' и 'date' для сравнения с предыдущим сообщением
        df_sorted['prev_from_id'] = df_sorted['from_id'].shift(1)
        df_sorted['prev_date'] = df_sorted['date'].shift(1)

        # Фильтруем строки, где:
        # 1. Есть предыдущее сообщение (prev_date не NaT)
        # 2. Автор отличается от предыдущего (from_id != prev_from_id)
        responses = df_sorted[
            df_sorted['prev_date'].notna() &
            (df_sorted['from_id'] != df_sorted['prev_from_id'])
            ].copy()  # Явная копия для избежания SettingWithCopyWarning

        if responses.empty:
            logger.warning("Не найдено сообщений, являющихся ответами (смена автора).")
            return 0.0

        # Вычисляем разницу во времени в минутах
        responses['time_diff_min'] = (responses['date'] - responses['prev_date']).dt.total_seconds() / 60

        # Фильтруем по максимальному интервалу и положительной разнице
        valid_response_times = responses[
            (responses['time_diff_min'] > 0) &
            (responses['time_diff_min'] <= max_interval_minutes)
            ]['time_diff_min']

        if valid_response_times.empty:
            logger.warning(f"Не найдено ответов в пределах {max_interval_minutes} минут.")
            avg_response = 0.0
        else:
            avg_response = valid_response_times.mean()

        logger.info("\n--- Среднее время ответа ---")
        logger.info(f"(Учитываются ответы разных авторов в течение {max_interval_minutes} мин)")
        logger.info(f"Среднее время ответа: {avg_response:.2f} минут")
        logger.info(
            f"Медианное время ответа: {valid_response_times.median():.2f} минут" if not valid_response_times.empty else "Медианное время ответа: N/A")
        logger.info(f"Количество учтенных ответов: {len(valid_response_times)}")
        logger.info("-" * 20)
        return avg_response

    except Exception as e:
        logger.error(f"Ошибка при расчете времени ответа: {e}", exc_info=True)
        return None


def plot_response_time_distribution(df: pd.DataFrame, max_interval_minutes: float = 60,
                                    save_path: Optional[str] = None) -> None:
    """Строит гистограмму распределения времени ответа."""
    if df is None or df.empty:
        logger.warning("Нет данных для построения гистограммы времени ответа.")
        return

    required_columns = ['date', 'from_id']  # Используем from_id
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для plot_response_time_distribution: {required_columns}")
        return

    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        logger.error("Столбец 'date' должен быть типа datetime для plot_response_time_distribution.")
        return

    if len(df) < 2:
        logger.warning("Недостаточно сообщений (<2) для расчета распределения времени ответа.")
        return

    try:
        df_sorted = df.sort_values('date').copy()
        df_sorted['prev_from_id'] = df_sorted['from_id'].shift(1)
        df_sorted['prev_date'] = df_sorted['date'].shift(1)

        responses = df_sorted[
            df_sorted['prev_date'].notna() &
            (df_sorted['from_id'] != df_sorted['prev_from_id'])
            ].copy()

        if responses.empty:
            logger.warning("Не найдено сообщений-ответов для построения гистограммы.")
            return

        responses['time_diff_min'] = (responses['date'] - responses['prev_date']).dt.total_seconds() / 60

        # Фильтруем только валидные времена для гистограммы
        valid_response_times = responses[
            (responses['time_diff_min'] > 0) &
            (responses['time_diff_min'] <= max_interval_minutes)  # Используем тот же лимит
            ]['time_diff_min']

        if valid_response_times.empty:
            logger.warning(f"Не найдено валидных времен ответа (0 < t <= {max_interval_minutes} мин) для гистограммы.")
            return

        logger.info("\n--- Распределение времени ответа ---")
        logger.info(f"(Ответы разных авторов, 0 < t <= {max_interval_minutes} мин)")
        logger.info(f"Median:    {valid_response_times.median():.2f} min")
        logger.info(f"Mean:      {valid_response_times.mean():.2f} min")
        logger.info(f"90-й перц.: {valid_response_times.quantile(0.9):.2f} min")
        logger.info(f"95-й перц.: {valid_response_times.quantile(0.95):.2f} min")
        logger.info(f"Количество: {len(valid_response_times)}")

        # Гистограмма
        plt.figure(figsize=(10, 6))
        sns.histplot(valid_response_times, bins=50, kde=True, color='skyblue')
        plt.title(f"Распределение времени ответа (0 < t <= {max_interval_minutes} минут)", fontsize=16)
        plt.xlabel("Время ответа (минуты)", fontsize=12)
        plt.ylabel("Частота", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        # plt.xlim(left=0) # Начинаем с нуля
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Гистограмма времени ответа сохранена в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить гистограмму времени ответа в {save_path}: {e}")
        # plt.show()
        plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при построении гистограммы времени ответа: {e}", exc_info=True)
        plt.close()


def plot_daily_activity_with_moving_averages(df: pd.DataFrame, save_path: Optional[str] = None) -> Optional[pd.Series]:
    """Строит график дневной активности с 7- и 30-дневными скользящими средними."""
    if df is None or df.empty:
        logger.warning("Нет данных для графика дневной активности.")
        return None

    required_columns = ['date_only']
    if 'date_only' not in df:
        logger.error(f"Отсутствует необходимый столбец для plot_daily_activity_with_moving_averages: 'date_only'")
        return None

    try:
        # Группировка по дате (без времени)
        daily_counts = df.groupby('date_only').size().rename("msg_count")

        if daily_counts.empty:
            logger.warning("Нет данных по дням для расчета скользящих средних.")
            return None

        # Преобразуем индекс в DatetimeIndex для работы с rolling и seasonal_decompose
        try:
            # Пытаемся преобразовать объекты date в datetime
            daily_counts.index = pd.to_datetime(daily_counts.index)
        except TypeError as e:
            logger.error(
                f"Не удалось преобразовать индекс date_only в datetime: {e}. Пропускаем анализ временных рядов.")
            return None

        # Создаем полный диапазон дат, чтобы учесть дни без сообщений
        if not daily_counts.index.is_monotonic_increasing:
            daily_counts = daily_counts.sort_index()  # Убедимся, что индекс отсортирован

        full_date_range = pd.date_range(start=daily_counts.index.min(), end=daily_counts.index.max(), freq='D')
        daily_counts = daily_counts.reindex(full_date_range, fill_value=0)

        # Скользящее среднее за 7 и 30 дней
        # Используем center=True для более гладкого отображения тренда
        rolling_7 = daily_counts.rolling(window=7, min_periods=1, center=True).mean().rename("ma_7d")
        rolling_30 = daily_counts.rolling(window=30, min_periods=1, center=True).mean().rename("ma_30d")

        logger.info("\n--- Активность по дням ---")
        logger.info(f"Период: {daily_counts.index.min().date()} - {daily_counts.index.max().date()}")
        logger.info(f"Всего дней в периоде: {len(daily_counts)}")
        logger.info(f"Дней с сообщениями: {(daily_counts > 0).sum()}")
        logger.info(f"Среднее сообщений в день (за весь период): {daily_counts.mean():.2f}")
        logger.info(f"Медианное сообщений в день: {daily_counts.median():.1f}")
        logger.info(f"Максимум сообщений в день: {daily_counts.max()}")

        # Визуализация (matplotlib)
        plt.figure(figsize=(14, 6))
        plt.plot(daily_counts.index, daily_counts, label="Сообщения в день", color='grey', alpha=0.6, marker='.',
                 markersize=3, linestyle='')
        plt.plot(rolling_7.index, rolling_7, label="Скользящее среднее (7 дней)", color='orange', linewidth=2)
        plt.plot(rolling_30.index, rolling_30, label="Скользящее среднее (30 дней)", color='red', linewidth=2)
        plt.legend()
        plt.title("Активность по дням и скользящие средние", fontsize=16)
        plt.xlabel("Дата", fontsize=12)
        plt.ylabel("Количество сообщений", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График дневной активности сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график дневной активности в {save_path}: {e}")
        # plt.show()
        plt.close()
        logger.info("-" * 20)
        return daily_counts  # Возвращаем daily_counts для возможного использования в seasonal_decompose

    except Exception as e:
        logger.error(f"Ошибка при построении графика дневной активности: {e}", exc_info=True)
        plt.close()
        return None


def perform_seasonal_decomposition(daily_counts: pd.Series, period: int = 7, model: str = 'additive',
                                   save_path: Optional[str] = None) -> None:
    """Выполняет и отображает сезонную декомпозицию временного ряда дневной активности."""
    if daily_counts is None or daily_counts.empty:
        logger.warning("Нет данных daily_counts для сезонной декомпозиции.")
        return

    # Проверяем, достаточно ли данных для периода
    if len(daily_counts) < 2 * period:
        logger.warning(
            f"Недостаточно данных ({len(daily_counts)} точек) для надежной сезонной декомпозиции с периодом {period}. Требуется как минимум {2 * period}.")
        return

    try:
        logger.info(f"\n--- Сезонная декомпозиция (Период={period}, Модель={model}) ---")
        # Используем seasonal_decompose
        # Убедимся, что индекс имеет частоту 'D' (ежедневную)
        if daily_counts.index.freq is None:
            daily_counts = daily_counts.asfreq('D', fill_value=0)  # Пытаемся установить частоту
            logger.info("Установлена ежедневная частота ('D') для временного ряда.")

        # Выполняем декомпозицию
        decomposition = seasonal_decompose(daily_counts, model=model, period=period, extrapolate_trend='freq')

        # Визуализация результатов
        fig = decomposition.plot()
        fig.set_size_inches(12, 8)
        fig.suptitle(f'Сезонная декомпозиция (Период={period}, Модель={model})', y=1.01)
        plt.tight_layout(rect=[0, 0, 1, 0.98])  # Оставляем место для suptitle

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График сезонной декомпозиции сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график сезонной декомпозиции в {save_path}: {e}")
        # plt.show()
        plt.close()
        logger.info("-" * 20)

    except ValueError as ve:
        # Часто возникает, если в данных много нулей или ряд слишком короткий
        logger.error(
            f"Ошибка значения при сезонной декомпозиции (период={period}): {ve}. Возможно, ряд слишком короткий или содержит много нулей.")
        plt.close()
    except Exception as e:
        logger.error(f"Общая ошибка при сезонной декомпозиции: {e}", exc_info=True)
        plt.close()


def analyze_message_intervals(df: pd.DataFrame, max_interval_seconds: float = 3600,
                              save_path: Optional[str] = None) -> None:
    """Анализирует и визуализирует интервалы между *последовательными* сообщениями."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа интервалов между сообщениями.")
        return

    required_columns = ['date']
    if 'date' not in df:
        logger.error(f"Отсутствует необходимый столбец для analyze_message_intervals: 'date'")
        return
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        logger.error("Столбец 'date' имеет некорректный тип для analyze_message_intervals.")
        return

    if len(df) < 2:
        logger.warning("Недостаточно сообщений (<2) для расчета интервалов.")
        return

    try:
        df_sorted = df.sort_values('date').copy()

        # Вычисление интервалов между последовательными сообщениями (в секундах)
        intervals_seconds = df_sorted['date'].diff().dt.total_seconds().dropna()

        # Фильтрация разумных интервалов (например, > 0 и <= max_interval_seconds)
        valid_intervals = intervals_seconds[(intervals_seconds > 0) & (intervals_seconds <= max_interval_seconds)]

        if valid_intervals.empty:
            logger.warning(f"Не найдено интервалов между сообщениями в диапазоне (0, {max_interval_seconds}] секунд.")
            logger.info("\n--- Статистика интервалов между сообщениями ---")
            logger.info(f"Не найдено интервалов в диапазоне (0, {max_interval_seconds:.0f}] секунд.")
            logger.info("-" * 20)
            return

        logger.info("\n--- Статистика интервалов между сообщениями ---")
        logger.info(f"(Интервалы > 0 и <= {max_interval_seconds:.0f} секунд)")
        try:
            logger.info(valid_intervals.describe().to_string())
        except Exception:
            logger.info(valid_intervals.describe())

        plt.figure(figsize=(12, 6))
        sns.histplot(valid_intervals, bins=50, kde=True, color='purple')

        plt.title('Распределение интервалов между сообщениями', fontsize=16)
        plt.xlabel('Интервал (секунды)', fontsize=12)
        plt.ylabel('Частота', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)

        # Ограничение по X для читаемости (например, 95-й перцентиль)
        xlim_upper = valid_intervals.quantile(0.95)
        if pd.notna(xlim_upper) and xlim_upper > 0:
            plt.xlim(0, xlim_upper)

        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График интервалов между сообщениями сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график интервалов в {save_path}: {e}")
        # plt.show()
        plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе интервалов между сообщениями: {e}", exc_info=True)
        plt.close()

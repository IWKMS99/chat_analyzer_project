# === Standard library ===
import logging
from typing import Optional

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


def plot_hourly_activity(
        df: pd.DataFrame,
        percentage: bool = True,
        save_path: Optional[str] = None,
        max_legend_items: int = 10
) -> None:
    """
    Строит линейный график активности участников чата по часам дня.

    Args:
        df: DataFrame с данными чата (ожидаются столбцы 'hour', 'from').
        percentage: Если True, отображает долю сообщений в процентах, иначе — абсолютное количество.
        save_path: Путь для сохранения графика.
        max_legend_items: Максимальное число участников в легенде.
    """
    if df is None or df.empty:
        logger.warning("Нет данных для построения графика активности по часам.")
        return

    required_columns = ['hour', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для plot_hourly_activity: {required_columns}")
        return

    try:
        plt.figure(figsize=(14, 7))
        hourly_counts = df.groupby(['hour', 'from']).size().unstack(fill_value=0)

        if hourly_counts.empty:
            logger.warning("Нет сгруппированных данных по часам и авторам.")
            plt.close()
            return

        y_label = 'Количество сообщений'
        title = 'Активность по часам (абсолютные значения)'

        if percentage:
            total_sum = hourly_counts.sum().sum()
            if total_sum == 0:
                logger.warning("Нет сообщений для нормализации в plot_hourly_activity.")
                hourly_counts_plot = hourly_counts  # Отображаем нули
            else:
                hourly_counts_plot = hourly_counts.div(hourly_counts.sum(axis=0),
                                                       axis=1) * 100  # Нормализуем по каждому пользователю
                y_label = 'Доля сообщений пользователя (%)'
                title = 'Процентная активность по часам (от общего числа сообщений пользователя)'
        else:
            hourly_counts_plot = hourly_counts

        # Ограничиваем число участников для отображения
        num_users = len(hourly_counts_plot.columns)
        if num_users > max_legend_items:
            top_users_indices = hourly_counts.sum().nlargest(max_legend_items).index
            hourly_counts_plot = hourly_counts_plot[top_users_indices]
            logger.info(
                f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике почасовой активности.")

        if hourly_counts_plot.empty:
            logger.warning("Нет данных для отображения после фильтрации пользователей.")
            plt.close()
            return

        sns.lineplot(data=hourly_counts_plot, linewidth=2.5, palette='viridis', dashes=False)
        plt.title(title, fontsize=16)
        plt.xlabel('Час дня (локальное время)', fontsize=12)
        plt.ylabel(y_label, fontsize=12)

        # Размещаем легенду снаружи, если много элементов
        if len(hourly_counts_plot.columns) > 5:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        else:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(range(0, 24), fontsize=10)  # Убедимся, что есть все 24 часа
        plt.xlim(-0.5, 23.5)
        plt.tight_layout(
            rect=[0, 0, 0.9 if len(hourly_counts_plot.columns) > 5 else 1, 1])  # Оставляем место для легенды

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График активности по часам сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график активности по часам в {save_path}: {e}")
        # plt.show()
        plt.close()

    except Exception as e:
        logger.error(f"Ошибка при построении графика активности по часам: {e}", exc_info=True)
        plt.close()  # Убедимся, что фигура закрыта в случае ошибки


def plot_weekday_activity(
        df: pd.DataFrame,
        save_path: Optional[str] = None,
        max_legend_items: int = 10,
        stacked: bool = False  # Добавлен параметр для stacked bar chart
) -> None:
    """
    Строит график активности участников чата по дням недели.

    Args:
        df: DataFrame с данными чата (ожидаются столбцы 'day_of_week', 'from').
        save_path: Путь для сохранения графика.
        max_legend_items: Максимальное число участников в легенде.
        stacked: Строить ли stacked bar chart (True) или сгруппированный (False).
    """
    if df is None or df.empty:
        logger.warning("Нет данных для построения графика активности по дням недели.")
        return

    required_columns = ['day_of_week', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для plot_weekday_activity: {required_columns}")
        return

    # Проверка корректности значений day_of_week
    valid_days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
    unique_days = set(df['day_of_week'].unique())
    if not unique_days.issubset(valid_days):
        invalid_days = unique_days - valid_days
        logger.warning(
            f"Столбец 'day_of_week' содержит некорректные значения: {invalid_days}. Они будут проигнорированы.")
        df_filtered_days = df[df['day_of_week'].isin(valid_days)]
        if df_filtered_days.empty:
            logger.warning("Нет данных с корректными днями недели.")
            return
    else:
        df_filtered_days = df

    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    try:
        # Ограничение числа участников
        num_users = df_filtered_days['from'].nunique()
        if num_users > max_legend_items:
            top_users = df_filtered_days['from'].value_counts().nlargest(max_legend_items).index
            df_plot = df_filtered_days[df_filtered_days['from'].isin(top_users)]
            logger.info(f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике по дням недели.")
        else:
            df_plot = df_filtered_days

        if df_plot.empty:
            logger.warning("Нет данных для отображения на графике по дням недели после фильтрации.")
            return

        plt.figure(figsize=(12, 6))

        if stacked:
            # Подготовка данных для stacked bar
            weekday_counts = df_plot.groupby(['day_of_week', 'from']).size().unstack(fill_value=0)
            # Упорядочивание дней недели и добавление отсутствующих дней с нулями
            weekday_counts = weekday_counts.reindex(days_order, fill_value=0)
            weekday_counts.plot(kind='bar', stacked=True, figsize=(12, 6), colormap='viridis', ax=plt.gca())
            title = 'Активность по дням недели (Stacked)'
        else:
            # Используем seaborn countplot для сгруппированного графика
            sns.countplot(
                data=df_plot,
                x='day_of_week',
                hue='from',
                palette='viridis',
                order=days_order,
                ax=plt.gca()
            )
            title = 'Сообщения по дням недели (Сгруппировано)'

        plt.title(title, fontsize=16)
        plt.xlabel('День недели', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)
        plt.xticks(rotation=45)

        # Размещаем легенду снаружи
        if len(df_plot['from'].unique()) > 5:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        else:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, axis='y', linestyle='--', alpha=0.7)  # Сетка только по оси Y
        plt.tight_layout(rect=[0, 0, 0.85 if len(df_plot['from'].unique()) > 5 else 1, 1])

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График активности по дням недели сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график активности по дням недели в {save_path}: {e}")
        # plt.show()
        plt.close()

        # Вывод статистики (пример)
        weekday_summary = df_plot.groupby(['day_of_week', 'from']).size().unstack(fill_value=0).reindex(days_order,
                                                                                                        fill_value=0)
        logger.info("\n--- Активность по дням недели (Топ пользователей) ---")
        try:
            logger.info(weekday_summary.to_string())
        except Exception:  # Если to_string слишком большой
            logger.info(weekday_summary)
        logger.info("-" * 20)


    except Exception as e:
        logger.error(f"Ошибка при построении графика активности по дням недели: {e}", exc_info=True)
        plt.close()


def plot_monthly_activity(df: pd.DataFrame, save_path: Optional[str] = None, max_legend_items: int = 10) -> None:
    """Строит линейный график активности участников чата по месяцам."""
    if df is None or df.empty:
        logger.warning("Нет данных для построения графика активности по месяцам.")
        return

    required_columns = ['date', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для plot_monthly_activity: {required_columns}")
        return
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        logger.error("Столбец 'date' имеет некорректный тип для plot_monthly_activity.")
        return

    try:
        plt.figure(figsize=(14, 7))

        # Извлечение года и месяца
        df_copy = df.assign(year_month=df['date'].dt.to_period('M'))

        # Подсчет сообщений по месяцам и участникам
        monthly_counts = df_copy.groupby(['year_month', 'from']).size().unstack(fill_value=0)

        if monthly_counts.empty:
            logger.warning("Нет данных для графика по месяцам после группировки.")
            plt.close()
            return

        # Ограничение числа участников для отображения
        num_users = len(monthly_counts.columns)
        if num_users > max_legend_items:
            top_users_indices = df['from'].value_counts().nlargest(max_legend_items).index
            monthly_counts_plot = monthly_counts[top_users_indices]
            logger.info(f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике по месяцам.")
        else:
            monthly_counts_plot = monthly_counts

        if monthly_counts_plot.empty:
            logger.warning("Нет данных для отображения после фильтрации пользователей (месяцы).")
            plt.close()
            return

        # Построение линейного графика
        # Преобразуем PeriodIndex в строки для лучшего отображения на оси X
        monthly_counts_plot.index = monthly_counts_plot.index.astype(str)
        monthly_counts_plot.plot(figsize=(14, 7), marker='o', ax=plt.gca())

        plt.title('Количество сообщений по месяцам', fontsize=16)
        plt.xlabel('Год-Месяц', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)

        if len(monthly_counts_plot.columns) > 5:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        else:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout(rect=[0, 0, 0.85 if len(monthly_counts_plot.columns) > 5 else 1, 1])

        # Сохранение графика
        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График активности по месяцам сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график активности по месяцам в {save_path}: {e}")
        # plt.show()
        plt.close()

        # Вывод статистики
        logger.info("\n--- Статистика сообщений по месяцам (Топ пользователей) ---")
        try:
            logger.info(monthly_counts_plot.to_string())
        except Exception:
            logger.info(monthly_counts_plot)
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при построении графика активности по месяцам: {e}", exc_info=True)
        plt.close()


def analyze_time_periods(df: pd.DataFrame, save_path: Optional[str] = None, max_legend_items: int = 10) -> None:
    """Анализирует активность по временным интервалам дня."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа временных периодов.")
        return

    required_columns = ['hour', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_time_periods: {required_columns}")
        return

    try:
        df_copy = df.assign()
        # Определение временных интервалов
        bins = [-1, 6, 12, 18, 24]  # Используем -1 для включения 0
        labels = ['Ночь (0-6)', 'Утро (6-12)', 'День (12-18)', 'Вечер (18-24)']
        df_copy['time_period'] = pd.cut(df_copy['hour'], bins=bins, labels=labels, right=False)

        # Подсчет сообщений по интервалам и участникам
        period_counts = df_copy.groupby(['time_period', 'from'], observed=False).size().unstack(fill_value=0)

        if period_counts.empty:
            logger.warning("Нет данных для графика по временным периодам после группировки.")
            return

        # Ограничение числа участников для отображения
        num_users = len(period_counts.columns)
        if num_users > max_legend_items:
            top_users_indices = df['from'].value_counts().nlargest(max_legend_items).index
            period_counts_plot = period_counts[top_users_indices]
            logger.info(
                f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике по временным периодам.")
        else:
            period_counts_plot = period_counts

        if period_counts_plot.empty:
            logger.warning("Нет данных для отображения после фильтрации пользователей (периоды).")
            return

        # Построение столбчатого графика
        plt.figure(figsize=(14, 7))
        period_counts_plot.plot(kind='bar', ax=plt.gca(), colormap='viridis', rot=0)
        plt.title('Активность по временным интервалам дня', fontsize=16)
        plt.xlabel('Временной интервал', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)

        if len(period_counts_plot.columns) > 5:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        else:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout(rect=[0, 0, 0.85 if len(period_counts_plot.columns) > 5 else 1, 1])

        # Сохранение графика
        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График активности по периодам сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график активности по периодам в {save_path}: {e}")
        # plt.show()
        plt.close()

        # Вывод статистики
        logger.info("\n--- Статистика активности по временным интервалам (Топ пользователей) ---")
        try:
            logger.info(period_counts_plot.to_string())
        except Exception:
            logger.info(period_counts_plot)
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе временных периодов: {e}", exc_info=True)
        plt.close()

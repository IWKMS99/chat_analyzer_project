# === Standard library ===
import logging
from typing import Optional

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


def plot_user_message_counts(df: pd.DataFrame, top_n: int = 10, save_path: Optional[str] = None) -> None:
    """Строит график топ-N пользователей по количеству сообщений."""
    if df is None or df.empty:
        logger.warning("Нет данных для графика количества сообщений по пользователям.")
        return

    required_columns = ['from']
    if 'from' not in df:
        logger.error(f"Отсутствует необходимый столбец для plot_user_message_counts: 'from'")
        return

    try:
        user_counts = df['from'].value_counts()
        top_users = user_counts.head(top_n)

        if top_users.empty:
            logger.warning("Нет данных о количестве сообщений пользователей для графика.")
            return

        print(f"\n--- Топ-{len(top_users)} пользователей по числу сообщений ---")
        print(top_users)

        plt.figure(figsize=(10, max(5, top_n // 2)))  # Динамическая высота
        top_users.sort_values().plot(kind='barh', color='dodgerblue')  # Горизонтальный график
        plt.title(f"Топ-{len(top_users)} пользователей по числу сообщений", fontsize=16)
        plt.xlabel("Количество сообщений", fontsize=12)
        plt.ylabel("Пользователь", fontsize=12)
        plt.grid(True, axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График числа сообщений пользователей сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график числа сообщений пользователей в {save_path}: {e}")
        # plt.show()
        plt.close()
        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при построении графика числа сообщений пользователей: {e}", exc_info=True)
        plt.close()


def plot_user_avg_message_length(df: pd.DataFrame, top_n: int = 10, save_path: Optional[str] = None) -> None:
    """Строит график топ-N пользователей по средней длине сообщения."""
    if df is None or df.empty:
        logger.warning("Нет данных для графика средней длины сообщений.")
        return

    required_columns = ['from', 'text_length']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для plot_user_avg_message_length: {required_columns}")
        return

    try:
        # Рассчитываем среднюю длину, исключая NaN/пустые строки, если они есть
        avg_len = df.dropna(subset=['text_length']).groupby('from')['text_length'].mean()
        top_avg_len = avg_len.sort_values(ascending=False).head(top_n)

        if top_avg_len.empty:
            logger.warning("Не удалось рассчитать среднюю длину сообщений для графика.")
            return

        print(f"\n--- Топ-{len(top_avg_len)} пользователей по средней длине сообщения (символы) ---")
        print(top_avg_len.round(1))

        plt.figure(figsize=(10, max(5, top_n // 2)))  # Динамическая высота
        top_avg_len.sort_values().plot(kind='barh', color='mediumseagreen')  # Горизонтальный график
        plt.title(f"Топ-{len(top_avg_len)} пользователей по средней длине сообщения", fontsize=16)
        plt.xlabel("Средняя длина (символы)", fontsize=12)
        plt.ylabel("Пользователь", fontsize=12)
        plt.grid(True, axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График средней длины сообщений сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график средней длины сообщений в {save_path}: {e}")
        # plt.show()
        plt.close()
        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при построении графика средней длины сообщений: {e}", exc_info=True)
        plt.close()


def analyze_message_chains(df: pd.DataFrame, save_path: Optional[str] = None, max_legend_items: int = 10) -> None:
    """Анализирует длину цепочек сообщений от одного участника подряд."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа цепочек сообщений.")
        return

    required_columns = ['date', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_message_chains: {required_columns}")
        return

    if len(df) < 2:
        logger.warning("Недостаточно сообщений (<2) для анализа цепочек.")
        return

    try:
        df_sorted = df.sort_values('date').copy()

        # Определение цепочек (сообщения от одного участника подряд)
        # Цепочка меняется, когда 'from' отличается от предыдущего 'from'
        df_sorted['is_new_chain'] = (df_sorted['from'] != df_sorted['from'].shift(1))
        # cumsum() создает уникальный ID для каждой цепочки
        df_sorted['chain_id'] = df_sorted['is_new_chain'].cumsum()

        # Группируем по ID цепочки и автору, чтобы получить длину каждой цепочки
        chain_lengths = df_sorted.groupby(['chain_id', 'from']).size().reset_index(name='length')

        if chain_lengths.empty:
            logger.warning("Не удалось определить цепочки сообщений.")
            return

        # Статистика по длине цепочек для каждого участника
        chain_stats = chain_lengths.groupby('from')['length'].agg(['mean', 'median', 'max', 'count'])
        # Переименовываем 'count' в 'number_of_chains' для ясности
        chain_stats.rename(columns={'count': 'number_of_chains', 'mean': 'avg_chain_len', 'median': 'median_chain_len',
                                    'max': 'max_chain_len'}, inplace=True)

        print("\n--- Статистика цепочек сообщений ---")
        print("(Количество сообщений подряд от одного автора)")
        try:
            print(chain_stats.round(2).to_string())
        except Exception:
            print(chain_stats.round(2))

        # Ограничение числа участников для отображения на гистограмме
        num_users = chain_lengths['from'].nunique()
        participants_to_plot = chain_lengths['from'].unique()
        if num_users > max_legend_items:
            # Берем топ-N по количеству цепочек (или по средней длине?) - возьмем по количеству
            top_users_indices = chain_stats.nlargest(max_legend_items, 'number_of_chains').index
            participants_to_plot = top_users_indices
            logger.info(f"Отображено топ-{max_legend_items} пользователей из {num_users} на гистограмме длин цепочек.")

        # Построение гистограммы распределения длин цепочек
        plt.figure(figsize=(14, 7))
        plot_has_data = False
        for participant in participants_to_plot:
            subset = chain_lengths[chain_lengths['from'] == participant]['length']
            if not subset.empty:
                # Используем density=True для сравнения форм распределений
                sns.histplot(subset, bins=range(1, int(subset.max()) + 2), alpha=0.6, label=participant, kde=False,
                             stat="density", element="step")
                plot_has_data = True

        if not plot_has_data:
            logger.warning("Нет данных для отображения на гистограмме длин цепочек после фильтрации.")
            plt.close()
            print("-" * 20)
            return

        plt.title('Распределение длины цепочек сообщений (Плотность)', fontsize=16)
        plt.xlabel('Длина цепочки (количество сообщений)', fontsize=12)
        plt.ylabel('Плотность', fontsize=12)

        # Ограничиваем X для читаемости (например, 95-й перцентиль максимальной длины)
        try:
            xlim_upper = chain_lengths['length'].quantile(0.95)
            if pd.notna(xlim_upper) and xlim_upper > 1:  # Показывать хотя бы до 2
                plt.xlim(0.5, xlim_upper + 0.5)  # Начинаем с 0.5 для центрирования бинов
            else:
                plt.xlim(0.5, 10.5)  # Запасной вариант, если перцентиль мал
        except Exception as xlim_err:
            logger.warning(f"Не удалось определить xlim для графика цепочек: {xlim_err}. Используется стандартный.")
            plt.xlim(0.5, 10.5)

        num_plotted_items = len(plt.gca().get_lines()) + len(
            plt.gca().patches)  # Учитываем и линии KDE, и бары histplot
        if num_plotted_items > 10:  # Эвристика
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        elif num_plotted_items > 0:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout(rect=[0, 0, 0.85 if num_plotted_items > 10 else 1, 1])

        # Сохранение графика
        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График длин цепочек сообщений сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график длин цепочек в {save_path}: {e}")
        # plt.show()
        plt.close()
        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе цепочек сообщений: {e}", exc_info=True)
        plt.close()


def analyze_most_active_days(df: pd.DataFrame, top_n: int = 5, save_path: Optional[str] = None,
                             max_legend_items: int = 10) -> None:
    """Находит и визуализирует топ-N самых активных дней."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа самых активных дней.")
        return

    required_columns = ['date_only', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_most_active_days: {required_columns}")
        return

    try:
        # Подсчет сообщений по дням и участникам
        daily_counts_by_user = df.groupby(['date_only', 'from']).size().unstack(fill_value=0)

        if daily_counts_by_user.empty:
            logger.warning("Нет данных по дням и пользователям для анализа самых активных дней.")
            return

        # Сумма сообщений по дням
        daily_totals = daily_counts_by_user.sum(axis=1)

        # Топ-N самых активных дней
        top_days_totals = daily_totals.nlargest(top_n)

        if top_days_totals.empty:
            logger.warning("Не удалось определить самые активные дни.")
            return

        print(f"\n--- Топ-{len(top_days_totals)} самых активных дней ---")
        print(top_days_totals)

        # Подготовка данных для графика (только для топ-N дней)
        top_days_df = daily_counts_by_user.loc[top_days_totals.index]

        # Ограничение числа участников для отображения на stacked bar
        num_users = top_days_df.shape[1]
        users_to_plot = top_days_df.columns
        if num_users > max_legend_items:
            # Суммируем по всем топ-дням для определения топ-N участников
            top_users_indices = top_days_df.sum(axis=0).nlargest(max_legend_items).index
            # Оставляем топ-N и создаем колонку 'Other' для остальных
            other_users = top_days_df.columns.difference(top_users_indices)
            if not other_users.empty:
                top_days_plot = top_days_df[top_users_indices].copy()
                top_days_plot['Other'] = top_days_df[other_users].sum(axis=1)
            else:
                top_days_plot = top_days_df[top_users_indices]

            logger.info(
                f"Отображено топ-{max_legend_items} пользователей (+ 'Other') из {num_users} на графике активных дней.")
        else:
            top_days_plot = top_days_df

        # Построение столбчатого графика (stacked)
        plt.figure(figsize=(14, 7))
        # Сортируем дни по дате перед построением графика
        top_days_plot.index = pd.to_datetime(top_days_plot.index)  # Преобразуем в datetime для сортировки
        top_days_plot = top_days_plot.sort_index()
        # Преобразуем индекс обратно в строку для меток оси X
        top_days_plot.index = top_days_plot.index.strftime('%Y-%m-%d')

        top_days_plot.plot(kind='bar', stacked=True, ax=plt.gca(), colormap='tab20',
                           rot=45)  # Используем другую палитру для >10
        plt.title(f'Топ-{len(top_days_totals)} самых активных дней', fontsize=16)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Количество сообщений', fontsize=12)

        num_legend_items = len(top_days_plot.columns)
        if num_legend_items > 5:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        elif num_legend_items > 0:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout(rect=[0, 0, 0.85 if num_legend_items > 5 else 1, 1])

        # Сохранение графика
        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График самых активных дней сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график активных дней в {save_path}: {e}")
        # plt.show()
        plt.close()
        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе самых активных дней: {e}", exc_info=True)
        plt.close()

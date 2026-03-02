# === Standard library ===
import logging
from typing import Optional

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt
import seaborn as sns

from chat_analyzer.utils import finalize_plot, log_exception, normalize_time_window

logger = logging.getLogger(__name__)


def _define_sessions(df: pd.DataFrame, max_gap_minutes: float = 30) -> pd.DataFrame:
    """Вспомогательная функция для определения сессий."""
    if df is None or df.empty:
        return pd.DataFrame()  # Возвращаем пустой DataFrame

    df_sorted = df.sort_values('date').copy()
    df_sorted['time_diff'] = df_sorted['date'].diff().dt.total_seconds() / 60
    # Новая сессия начинается, если разрыв больше max_gap_minutes ИЛИ если это первое сообщение (isna())
    df_sorted['new_session'] = (df_sorted['time_diff'] > max_gap_minutes) | df_sorted['time_diff'].isna()
    df_sorted['session_id'] = df_sorted['new_session'].cumsum()
    return df_sorted


def analyze_dialog_sessions(df: pd.DataFrame, max_gap_minutes: float = 30, save_path: Optional[str] = None) -> None:
    """Анализирует сессии общения (длительность, количество сообщений)."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа сессий общения.")
        return

    required_columns = ['date', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_dialog_sessions: {required_columns}")
        return

    try:
        df_sessions = _define_sessions(df, max_gap_minutes)
        if df_sessions.empty:
            logger.warning("Не удалось определить сессии общения.")
            return

        # Подсчет сообщений и длительности сессий
        sessions = df_sessions.groupby('session_id').agg(
            start_time=('date', 'min'),
            end_time=('date', 'max'),
            message_count=('from', 'size'),
            participants=('from', lambda x: x.nunique())  # Число уникальных участников в сессии
        )
        # Рассчитываем длительность только если есть хотя бы 2 сообщения (end_time > start_time)
        sessions['duration_minutes'] = (sessions['end_time'] - sessions['start_time']).dt.total_seconds() / 60
        sessions.loc[
            sessions['message_count'] <= 1, 'duration_minutes'] = 0  # Сессии из 1 сообщения имеют длительность 0

        # Статистика по участникам в сессиях
        session_participants_stats = df_sessions.groupby(['session_id', 'from']).size().unstack(fill_value=0)

        logger.info("\n--- Статистика сессий общения ---")
        if sessions.empty:
            logger.info("Сессий общения не найдено.")
        else:
            logger.info(f"Общее количество сессий (разрыв > {max_gap_minutes} мин): {len(sessions)}")
            logger.info(f"Средняя длительность сессии (минуты): {sessions['duration_minutes'].mean():.2f}")
            logger.info(f"Медианная длительность сессии (минуты): {sessions['duration_minutes'].median():.2f}")
            logger.info(f"Максимальная длительность сессии (минуты): {sessions['duration_minutes'].max():.2f}")
            logger.info(f"Среднее количество сообщений в сессии: {sessions['message_count'].mean():.2f}")
            logger.info(f"Медианное количество сообщений в сессии: {sessions['message_count'].median():.2f}")
            logger.info(f"Максимальное количество сообщений в сессии: {sessions['message_count'].max():.0f}")
            logger.info(f"Среднее количество участников в сессии: {sessions['participants'].mean():.2f}")

            logger.info("\nРаспределение сообщений по участникам в сессиях (описание):")
            # Описываем только сессии с >0 сообщениями для каждого участника
            try:
                logger.info(session_participants_stats[session_participants_stats > 0].describe().to_string())
            except Exception:
                logger.info(session_participants_stats[session_participants_stats > 0].describe())

            # График: длительность vs количество сообщений
            plt.figure(figsize=(14, 7))
            # Ограничим оси для лучшей читаемости, если есть большие выбросы
            xlim_max = sessions['duration_minutes'].quantile(0.99) if len(sessions) > 10 else sessions[
                'duration_minutes'].max()
            ylim_max = sessions['message_count'].quantile(0.99) if len(sessions) > 10 else sessions[
                'message_count'].max()

            plt.scatter(sessions['duration_minutes'], sessions['message_count'], alpha=0.5, edgecolors='k', s=30)
            plt.title(f'Длительность сессий vs Количество сообщений (Разрыв > {max_gap_minutes} мин)', fontsize=16)
            plt.xlabel('Длительность сессии (минуты)', fontsize=12)
            plt.ylabel('Количество сообщений', fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.7)
            if xlim_max > 0: plt.xlim(left=-0.05 * xlim_max, right=xlim_max * 1.05)  # Добавляем небольшой отступ
            if ylim_max > 0: plt.ylim(bottom=-0.05 * ylim_max, top=ylim_max * 1.05)
            plt.tight_layout()

            # Сохранение графика
            if save_path:
                try:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    logger.info(f"График сессий общения сохранен в {save_path}")
                except Exception as e:
                    logger.error(f"Не удалось сохранить график сессий общения в {save_path}: {e}")
            # plt.show()
            plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе сессий общения: {e}", exc_info=True)
        plt.close()


def analyze_dialog_balance(df: pd.DataFrame, max_gap_minutes: float = 30, save_path: Optional[str] = None) -> None:
    """Анализирует баланс сообщений между участниками в рамках сессий."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа баланса диалога.")
        return

    required_columns = ['date', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_dialog_balance: {required_columns}")
        return

    # Баланс имеет смысл только если есть хотя бы 2 участника
    if df['from'].nunique() < 2:
        logger.warning("Анализ баланса диалога требует как минимум двух участников.")
        return

    try:
        df_sessions = _define_sessions(df, max_gap_minutes)
        if df_sessions.empty:
            logger.warning("Не удалось определить сессии для анализа баланса.")
            return

        # Подсчет сообщений по участникам в каждой сессии
        session_counts = df_sessions.groupby(['session_id', 'from']).size().unstack(fill_value=0)

        # Фильтрация сессий, где участвовали *все* основные участники (или хотя бы 2)
        # Берем топ-N участников, чтобы избежать сильно разреженных данных
        n_participants_to_consider = min(5, df['from'].nunique())  # Анализируем баланс между топ-5 (или меньше)
        top_participants = df['from'].value_counts().nlargest(n_participants_to_consider).index
        session_counts_filtered = session_counts[top_participants]

        # Оставляем сессии, где каждый из этих топ-N участников написал хотя бы 1 сообщение
        active_sessions = session_counts_filtered[(session_counts_filtered > 0).all(axis=1)]

        if active_sessions.empty:
            logger.warning(
                f"Не найдено сессий (разрыв > {max_gap_minutes} мин), где все топ-{n_participants_to_consider} участника были активны.")
            balance_ratios = pd.DataFrame()  # Пустой DataFrame для статистики
        else:
            # Расчет доли сообщений для каждого участника
            total_messages_in_active_sessions = active_sessions.sum(axis=1)
            balance_ratios = active_sessions.div(total_messages_in_active_sessions, axis=0)

        logger.info("\n--- Статистика баланса диалога ---")
        if balance_ratios.empty:
            logger.info(f"Не найдено сессий для анализа баланса между топ-{n_participants_to_consider} участниками.")
        else:
            logger.info(f"Анализ баланса для топ-{n_participants_to_consider} участников ({', '.join(top_participants)}).")
            logger.info(f"Количество сессий с участием всех этих участников: {len(balance_ratios)}")
            logger.info("\nСтатистика доли сообщений в таких сессиях:")
            try:
                logger.info(balance_ratios.describe().to_string())
            except Exception:
                logger.info(balance_ratios.describe())

            # Построение гистограммы
            plt.figure(figsize=(14, 7))
            # Используем отдельные гистограммы или kdeplot для лучшей читаемости
            for participant in balance_ratios.columns:
                sns.histplot(balance_ratios[participant], bins=20, alpha=0.6, label=participant, kde=False,
                             stat="density")  # Используем density для сравнения

            plt.title(f'Распределение доли сообщений в активных сессиях (Топ-{n_participants_to_consider} участников)',
                      fontsize=16)
            plt.xlabel('Доля сообщений участника в сессии', fontsize=12)
            plt.ylabel('Плотность', fontsize=12)  # Плотность, т.к. stat="density"
            plt.legend(title='Участник', fontsize=10)
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xlim(0, 1)
            plt.tight_layout()

            # Сохранение графика
            if save_path:
                try:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    logger.info(f"График баланса диалога сохранен в {save_path}")
                except Exception as e:
                    logger.error(f"Не удалось сохранить график баланса диалога в {save_path}: {e}")
            # plt.show()
            plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе баланса диалога: {e}", exc_info=True)
        plt.close()


def analyze_dialog_intensity(df: pd.DataFrame, time_window: str = '1h', save_path: Optional[str] = None,
                             max_legend_items: int = 10) -> None:
    """Анализирует интенсивность диалога (сообщения в минуту) по временным окнам."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа интенсивности диалога.")
        return

    required_columns = ['date', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_dialog_intensity: {required_columns}")
        return
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        logger.error("Столбец 'date' имеет некорректный тип для analyze_dialog_intensity.")
        return

    try:
        normalized_window, error = normalize_time_window(time_window)
        if error:
            logger.error("Некорректное временное окно: %s", error)
            return
        logger.info("Временное окно интенсивности нормализовано: %s -> %s", time_window, normalized_window)

        df_sorted = df.sort_values('date').copy()

        # Подсчет сообщений в заданном временном окне
        # Убедимся, что индекс - datetime
        df_sorted.set_index('date', inplace=True)

        # Используем resample для группировки по времени
        intensity = df_sorted.groupby('from').resample(normalized_window).size().unstack(level=0, fill_value=0)

        if intensity.empty:
            logger.warning(f"Нет данных для анализа интенсивности после группировки по {normalized_window}.")
            return

        # Перевод в сообщения в минуту
        try:
            minutes_in_window = pd.Timedelta(normalized_window).total_seconds() / 60
            if minutes_in_window <= 0:
                logger.error(f"Некорректное временное окно: {normalized_window}. Невозможно рассчитать интенсивность.")
                return
            intensity_per_minute = intensity / minutes_in_window
        except ValueError:
            logger.error(
                f"Не удалось распознать временное окно: {normalized_window}. Используется необработанное количество.")
            intensity_per_minute = intensity  # Отображаем просто количество
            y_label = f'Сообщений в {normalized_window}'
        else:
            y_label = 'Сообщений в минуту'

        logger.info("\n--- Статистика интенсивности диалогов ---")
        logger.info(f"Временное окно: {normalized_window}")
        logger.info(f"({y_label})")
        try:
            logger.info(intensity_per_minute.describe().to_string())
        except Exception:
            logger.info(intensity_per_minute.describe())

        # Ограничение числа участников для отображения
        num_users = len(intensity_per_minute.columns)
        if num_users > max_legend_items:
            # Используем общее количество сообщений для определения топ-N
            top_users_indices = df['from'].value_counts().nlargest(max_legend_items).index
            intensity_plot = intensity_per_minute[top_users_indices]
            logger.info(f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике интенсивности.")
        else:
            intensity_plot = intensity_per_minute

        if intensity_plot.empty:
            logger.warning("Нет данных для отображения после фильтрации пользователей (интенсивность).")
            return

        # Построение графика
        plt.figure(figsize=(14, 7))
        intensity_plot.plot(figsize=(14, 7), ax=plt.gca(), colormap='viridis')
        plt.title(f'Интенсивность диалогов ({y_label})', fontsize=16)
        plt.xlabel('Время', fontsize=12)
        plt.ylabel(y_label, fontsize=12)

        if len(intensity_plot.columns) > 5:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
        else:
            plt.legend(title='Участник', fontsize=10)

        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout(rect=[0, 0, 0.85 if len(intensity_plot.columns) > 5 else 1, 1])

        # Сохранение графика
        finalize_plot(logger, save_path, "график интенсивности диалога")
        logger.info("-" * 20)

    except Exception as e:
        log_exception(logger, "Ошибка при анализе интенсивности диалога", e)
        plt.close()


def analyze_dialog_initiators(df: pd.DataFrame, max_gap_minutes: float = 30, save_path: Optional[str] = None) -> None:
    """Анализирует, кто чаще начинает диалоги (сессии)."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа инициаторов диалогов.")
        return

    required_columns = ['date', 'from', 'hour']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_dialog_initiators: {required_columns}")
        return

    try:
        df_sessions = _define_sessions(df, max_gap_minutes)
        if df_sessions.empty:
            logger.warning("Не удалось определить сессии для анализа инициаторов.")
            return

        # Выбор первого сообщения в каждой сессии
        first_messages = df_sessions.loc[df_sessions['new_session'], ['from', 'hour', 'session_id']]
        # Альтернативный способ, если new_session не сработал идеально:
        # first_messages = df_sessions.loc[df_sessions.groupby('session_id')['date'].idxmin()]

        if first_messages.empty:
            logger.warning("Не найдено первых сообщений в сессиях.")
            return

        # Подсчет инициаций по участникам
        initiator_counts = first_messages['from'].value_counts()

        # Подсчет инициаций по часам
        hourly_initiators = first_messages.groupby(['hour', 'from']).size().unstack(fill_value=0)
        # Добавляем недостающие часы с нулями
        all_hours = pd.Index(range(24), name='hour')
        hourly_initiators = hourly_initiators.reindex(all_hours, fill_value=0)

        logger.info("\n--- Статистика инициаторов диалогов ---")
        logger.info(f"Проанализировано {len(first_messages)} сессий (разрыв > {max_gap_minutes} мин).")
        logger.info("\nКоличество инициированных диалогов по участникам:")
        logger.info(initiator_counts)
        logger.info("\nРаспределение инициаций по часам:")
        try:
            logger.info(hourly_initiators.to_string())
        except Exception:
            logger.info(hourly_initiators)

        # Построение графиков
        fig, axes = plt.subplots(2, 1, figsize=(12, 10),
                                 gridspec_kw={'height_ratios': [1, 2]})  # Даем больше места тепловой карте
        fig.suptitle(f'Анализ инициаторов диалогов (Разрыв > {max_gap_minutes} мин)', fontsize=16, y=1.02)

        # График 1: Общее количество инициаций
        if not initiator_counts.empty:
            initiator_counts.plot(kind='bar', ax=axes[0], color='skyblue')
            axes[0].set_title('Количество инициированных диалогов', fontsize=14)
            axes[0].set_xlabel('Участник', fontsize=12)
            axes[0].set_ylabel('Количество сессий', fontsize=12)
            axes[0].grid(True, axis='y', linestyle='--', alpha=0.7)
            axes[0].tick_params(axis='x', rotation=0)  # Без поворота, если помещается
        else:
            axes[0].text(0.5, 0.5, 'Нет данных для графика инициаторов', horizontalalignment='center',
                         verticalalignment='center', transform=axes[0].transAxes)
            axes[0].set_title('Количество инициированных диалогов', fontsize=14)

        # График 2: Инициации по часам (Тепловая карта)
        if not hourly_initiators.empty:
            max_val = hourly_initiators.values.max()
            sns.heatmap(hourly_initiators, ax=axes[1], cmap='viridis', annot=True, fmt='.0f', linewidths=.5,
                        cbar=max_val > 0)  # Показываем cbar если есть ненулевые значения
            axes[1].set_title('Инициации диалогов по часам (локальное время)', fontsize=14)
            axes[1].set_xlabel('Участник', fontsize=12)
            axes[1].set_ylabel('Час дня', fontsize=12)
            axes[1].tick_params(axis='y', rotation=0)
        else:
            axes[1].text(0.5, 0.5, 'Нет данных для тепловой карты инициаций', horizontalalignment='center',
                         verticalalignment='center', transform=axes[1].transAxes)
            axes[1].set_title('Инициации диалогов по часам (локальное время)', fontsize=14)

        plt.tight_layout(rect=[0, 0, 1, 0.98])  # Оставляем место для suptitle

        # Сохранение графика
        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График инициаторов диалогов сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график инициаторов диалогов в {save_path}: {e}")
        # plt.show()
        plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе инициаторов диалогов: {e}", exc_info=True)
        plt.close()


def _build_reply_edges(df: pd.DataFrame, max_interval_minutes: float = 240) -> pd.DataFrame:
    """Строит таблицу ответов current<-previous между участниками."""
    if df is None or df.empty:
        return pd.DataFrame()

    required_columns = ["date", "from"]
    if not all(col in df for col in required_columns):
        return pd.DataFrame()

    df_sorted = df.sort_values("date").copy()
    df_sorted["prev_from"] = df_sorted["from"].shift(1)
    df_sorted["prev_date"] = df_sorted["date"].shift(1)
    df_sorted["gap_min"] = (df_sorted["date"] - df_sorted["prev_date"]).dt.total_seconds() / 60

    replies = df_sorted[
        df_sorted["prev_from"].notna()
        & (df_sorted["from"] != df_sorted["prev_from"])
        & (df_sorted["gap_min"] > 0)
        & (df_sorted["gap_min"] <= max_interval_minutes)
    ][["prev_from", "from", "gap_min", "hour"]]
    return replies


def plot_reply_matrix(
        df: pd.DataFrame,
        save_path: Optional[str] = None,
        max_legend_items: int = 10,
        max_interval_minutes: float = 240,
) -> pd.DataFrame:
    """Матрица ответов: кто кому отвечает."""
    replies = _build_reply_edges(df, max_interval_minutes=max_interval_minutes)
    if replies.empty:
        logger.warning("Недостаточно данных для матрицы ответов.")
        return pd.DataFrame()

    counts = replies.groupby(["from", "prev_from"]).size().unstack(fill_value=0)

    # Ограничиваем отображение топ-пользователями, чтобы тепловая карта оставалась читаемой.
    participants = (
        df["from"].value_counts().head(max_legend_items).index
        if df["from"].nunique() > max_legend_items else df["from"].value_counts().index
    )
    counts = counts.reindex(index=participants, columns=participants, fill_value=0)

    if counts.empty:
        logger.warning("Матрица ответов пуста после фильтрации.")
        return counts

    plt.figure(figsize=(12, 8))
    sns.heatmap(counts, cmap="YlGnBu", annot=True, fmt=".0f", linewidths=0.5)
    plt.title("Матрица ответов: строки отвечают столбцам")
    plt.xlabel("Кому отвечают")
    plt.ylabel("Кто отвечает")
    plt.tight_layout()
    finalize_plot(logger, save_path, "матрица ответов")
    return counts


def plot_response_time_heatmaps(
        df: pd.DataFrame,
        save_path: Optional[str] = None,
        max_legend_items: int = 10,
        max_interval_minutes: float = 240,
) -> dict:
    """Тепловые карты медианного времени ответа по парам и по часам."""
    replies = _build_reply_edges(df, max_interval_minutes=max_interval_minutes)
    if replies.empty:
        logger.warning("Недостаточно данных для тепловой карты времени ответа.")
        return {"pair_median": pd.DataFrame(), "hourly_pair_median": pd.DataFrame()}

    top_users = df["from"].value_counts().head(max_legend_items).index
    replies = replies[replies["from"].isin(top_users) & replies["prev_from"].isin(top_users)]
    if replies.empty:
        logger.warning("После фильтрации топ-пользователей нет данных для тепловой карты времени ответа.")
        return {"pair_median": pd.DataFrame(), "hourly_pair_median": pd.DataFrame()}

    pair_median = replies.groupby(["from", "prev_from"])["gap_min"].median().unstack(fill_value=0.0)
    hourly_pair_median = replies.groupby(["hour", "from"])["gap_min"].median().unstack(fill_value=0.0).reindex(
        range(24), fill_value=0.0
    )

    fig, axes = plt.subplots(2, 1, figsize=(14, 12))
    sns.heatmap(pair_median, cmap="rocket_r", annot=True, fmt=".1f", linewidths=0.5, ax=axes[0])
    axes[0].set_title("Медианное время ответа по парам участников (мин)")
    axes[0].set_xlabel("Кому отвечают")
    axes[0].set_ylabel("Кто отвечает")

    sns.heatmap(hourly_pair_median, cmap="mako", linewidths=0.3, ax=axes[1], cbar=True)
    axes[1].set_title("Медианное время ответа по часам и отвечающему участнику (мин)")
    axes[1].set_xlabel("Кто отвечает")
    axes[1].set_ylabel("Час")

    plt.tight_layout()
    finalize_plot(logger, save_path, "тепловая карта времени ответа")
    return {"pair_median": pair_median, "hourly_pair_median": hourly_pair_median}


def plot_session_timeline(
        df: pd.DataFrame,
        max_gap_minutes: float = 30,
        save_path: Optional[str] = None,
        max_sessions: int = 60,
) -> pd.DataFrame:
    """Таймлайн сессий: старт/длительность/насыщенность/инициатор."""
    sessions_df = _define_sessions(df, max_gap_minutes=max_gap_minutes)
    if sessions_df.empty:
        logger.warning("Нет данных для таймлайна сессий.")
        return pd.DataFrame()

    summary = sessions_df.groupby("session_id").agg(
        start_time=("date", "min"),
        end_time=("date", "max"),
        initiator=("from", "first"),
        message_count=("from", "size"),
    )
    summary["duration_min"] = (summary["end_time"] - summary["start_time"]).dt.total_seconds() / 60
    summary = summary.sort_values("start_time")
    if len(summary) > max_sessions:
        summary = summary.tail(max_sessions)

    plt.figure(figsize=(14, 7))
    scatter = plt.scatter(
        summary["start_time"],
        summary["duration_min"],
        s=summary["message_count"] * 12,
        c=summary["message_count"],
        cmap="viridis",
        alpha=0.8,
    )
    plt.colorbar(scatter, label="Количество сообщений")
    plt.title(f"Таймлайн сессий (gap>{max_gap_minutes} мин): длительность и плотность")
    plt.xlabel("Начало сессии")
    plt.ylabel("Длительность (мин)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    finalize_plot(logger, save_path, "таймлайн сессий")
    return summary

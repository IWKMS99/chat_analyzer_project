# === Standard library ===
import logging
import re
from typing import Optional

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


def analyze_message_length(df: pd.DataFrame, save_path: Optional[str] = None, max_legend_items: int = 10) -> None:
    """Анализирует и визуализирует распределение длины сообщений."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа длины сообщений.")
        return

    required_columns = ['from', 'text_length']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_message_length: {required_columns}")
        return

    try:
        logger.info("\n--- Статистика длины сообщений (символы) ---")
        stats = df.groupby('from')['text_length'].describe()
        try:
            logger.info(stats.to_string())
        except Exception:
            logger.info(stats)

        # Ограничение числа участников для отображения
        num_users = df['from'].nunique()
        if num_users > max_legend_items:
            top_users = df['from'].value_counts().nlargest(max_legend_items).index
            df_plot = df[df['from'].isin(top_users)]
            logger.info(f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике длины сообщений.")
        else:
            df_plot = df

        if df_plot.empty:
            logger.warning("Нет данных для отображения на графике длины сообщений после фильтрации.")
            return

        plt.figure(figsize=(12, 6))

        # Построение гистограммы/KDE плотности длины сообщений
        sns.histplot(data=df_plot, x='text_length', hue='from', kde=True, stat='density', common_norm=False, bins=50,
                     palette='viridis', element="step")

        plt.title('Распределение длины сообщений (Плотность)', fontsize=16)
        plt.xlabel('Длина сообщения (символы)', fontsize=12)
        plt.ylabel('Плотность', fontsize=12)

        # Ограничение по X для читаемости (например, 98-й перцентиль)
        xlim_upper = df_plot['text_length'].quantile(0.98)
        if pd.notna(xlim_upper) and xlim_upper > 0:
            plt.xlim(0, xlim_upper)
        else:
            logger.warning("Не удалось определить верхнюю границу для оси X графика длины сообщений.")

        if len(df_plot['from'].unique()) <= 5:
            plt.legend(title='Участник', fontsize=10)
        else:
            plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))

        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout(rect=[0, 0, 0.85 if len(df_plot['from'].unique()) > 5 else 1, 1])

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График распределения длины сообщений сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график длины сообщений в {save_path}: {e}")
        # plt.show()
        plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе длины сообщений: {e}", exc_info=True)
        plt.close()


def analyze_question_messages(df: pd.DataFrame, save_path: Optional[str] = None, max_legend_items: int = 10) -> None:
    """Анализирует использование вопросительных знаков в сообщениях."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа вопросительных сообщений.")
        return

    required_columns = ['text', 'from', 'hour']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_question_messages: {required_columns}")
        return

    try:
        df_copy = df.assign()
        # Определение вопросительных сообщений (простой поиск знака вопроса)
        # Убедимся, что text - это строка
        df_copy['is_question'] = df_copy['text'].astype(str).str.contains(r'\?', na=False, regex=True)

        df_questions = df_copy[df_copy['is_question']]

        if df_questions.empty:
            logger.info("Вопросительных сообщений (содержащих '?') не найдено.")
            question_counts = pd.Series(dtype=int)
            question_ratio = pd.Series(dtype=float)
            hourly_questions = pd.DataFrame()
        else:
            # Подсчет вопросительных сообщений
            question_counts = df_questions.groupby('from').size()
            total_counts = df_copy.groupby('from').size()
            # Рассчитываем долю, избегая деления на ноль
            question_ratio = question_counts.divide(total_counts).fillna(0)

            # Подсчет по часам
            hourly_questions = df_questions.groupby(['hour', 'from']).size().unstack(fill_value=0)
            # Добавляем недостающие часы
            all_hours = pd.Index(range(24), name='hour')
            hourly_questions = hourly_questions.reindex(all_hours, fill_value=0)

        logger.info("\n--- Статистика вопросительных сообщений ('?') ---")
        if question_counts.empty:
            logger.info("Не найдено сообщений, содержащих '?'.")
        else:
            logger.info("\nКоличество вопросов:")
            logger.info(question_counts)
            logger.info("\nДоля вопросов от всех сообщений участника:")
            # Форматируем вывод доли в процентах
            logger.info(question_ratio.map('{:.2%}'.format))
            logger.info("\nРаспределение вопросов по часам (локальное время):")
            try:
                logger.info(hourly_questions.to_string())
            except Exception:
                logger.info(hourly_questions)

            # Ограничение числа участников для отображения
            num_users = hourly_questions.shape[1]
            if num_users > max_legend_items:
                # Используем общее количество вопросов для определения топ-N
                top_users_indices = question_counts.nlargest(max_legend_items).index
                hourly_questions_plot = hourly_questions[top_users_indices]
                logger.info(f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике вопросов.")
            else:
                hourly_questions_plot = hourly_questions

            if hourly_questions_plot.empty:
                logger.warning("Нет данных для отображения после фильтрации пользователей (вопросы).")
            else:
                # Построение графика
                plt.figure(figsize=(14, 7))
                hourly_questions_plot.plot(figsize=(14, 7), ax=plt.gca(), colormap='coolwarm', marker='.')
                plt.title('Количество вопросительных сообщений по часам (локальное время)', fontsize=16)
                plt.xlabel('Час дня', fontsize=12)
                plt.ylabel('Количество вопросов', fontsize=12)

                if len(hourly_questions_plot.columns) > 5:
                    plt.legend(title='Участник', fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
                else:
                    plt.legend(title='Участник', fontsize=10)

                plt.grid(True, linestyle='--', alpha=0.7)
                plt.xticks(range(24))
                plt.xlim(-0.5, 23.5)
                plt.tight_layout(rect=[0, 0, 0.85 if len(hourly_questions_plot.columns) > 5 else 1, 1])

                # Сохранение графика
                if save_path:
                    try:
                        plt.savefig(save_path, dpi=300, bbox_inches='tight')
                        logger.info(f"График вопросительных сообщений сохранен в {save_path}")
                    except Exception as e:
                        logger.error(f"Не удалось сохранить график вопросительных сообщений в {save_path}: {e}")
                # plt.show()
                plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе вопросительных сообщений: {e}", exc_info=True)
        plt.close()


def analyze_short_long_messages(df: pd.DataFrame, length_threshold: int = 50, save_path: Optional[str] = None,
                                max_legend_items: int = 10) -> None:
    """Анализирует распределение коротких и длинных сообщений."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа коротких/длинных сообщений.")
        return

    required_columns = ['text_length', 'from', 'hour']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_short_long_messages: {required_columns}")
        return

    try:
        df_copy = df.assign()
        # Классификация сообщений
        df_copy['message_type'] = df_copy['text_length'].apply(lambda
                                                                   x: f'Короткое (<= {length_threshold})' if x <= length_threshold else f'Длинное (> {length_threshold})')

        # Подсчет по типам сообщений и участникам
        message_type_counts = df_copy.groupby(['from', 'message_type'], observed=False).size().unstack(fill_value=0)

        # Подсчет по часам
        hourly_counts = df_copy.groupby(['hour', 'from', 'message_type'], observed=False).size().unstack(level=[1, 2],
                                                                                                         fill_value=0)
        # Добавляем недостающие часы
        all_hours = pd.Index(range(24), name='hour')
        hourly_counts = hourly_counts.reindex(all_hours, fill_value=0)

        logger.info("\n--- Статистика коротких и длинных сообщений ---")
        logger.info(f"Порог длины: {length_threshold} символов")
        try:
            logger.info(message_type_counts.to_string())
        except Exception:
            logger.info(message_type_counts)

        # Ограничение числа участников для отображения
        num_users = df['from'].nunique()
        participants_to_plot = df['from'].unique()
        if num_users > max_legend_items:
            top_users_indices = df['from'].value_counts().nlargest(max_legend_items).index
            participants_to_plot = top_users_indices
            logger.info(
                f"Отображено топ-{max_legend_items} пользователей из {num_users} на графике коротких/длинных сообщений.")

        if hourly_counts.empty:
            logger.warning("Нет почасовых данных для графика коротких/длинных сообщений.")
        else:
            plt.figure(figsize=(14, 7))
            plot_has_data = False
            # Линейный график активности по часам
            for participant in participants_to_plot:
                for msg_type in [f'Короткое (<= {length_threshold})', f'Длинное (> {length_threshold})']:
                    # Проверяем, существует ли комбинация (participant, msg_type) в колонках
                    col_tuple = (participant, msg_type)  # Уровень 1 - from, Уровень 2 - message_type
                    if col_tuple in hourly_counts.columns:
                        label_short = f'{participant} (Короткое)'
                        label_long = f'{participant} (Длинное)'
                        linestyle = '-' if 'Короткое' in msg_type else '--'
                        label = label_short if 'Короткое' in msg_type else label_long

                        # Проверяем, есть ли ненулевые данные для этого среза
                        if hourly_counts[col_tuple].sum() > 0:
                            plt.plot(hourly_counts.index, hourly_counts[col_tuple], label=label, linestyle=linestyle,
                                     marker='.')
                            plot_has_data = True
                        # else:
                        # logger.debug(f"Нет данных для {label} на графике коротких/длинных сообщений.")

            if not plot_has_data:
                logger.warning("Нет данных для отображения на графике коротких/длинных сообщений после фильтрации.")
                plt.close()
            else:
                plt.title(f'Активность коротких (<= {length_threshold}) и длинных сообщений по часам (локальное время)',
                          fontsize=16)
                plt.xlabel('Час дня', fontsize=12)
                plt.ylabel('Количество сообщений', fontsize=12)

                num_plotted_items = len(plt.gca().get_lines())  # Количество отрисованных линий
                if num_plotted_items > 10:  # Эвристика для размещения легенды
                    plt.legend(title='Участник (Тип)', fontsize=9, loc='upper left', bbox_to_anchor=(1.02, 1))
                elif num_plotted_items > 0:
                    plt.legend(title='Участник (Тип)', fontsize=10)

                plt.grid(True, linestyle='--', alpha=0.7)
                plt.xticks(range(24))
                plt.xlim(-0.5, 23.5)
                plt.tight_layout(rect=[0, 0, 0.85 if num_plotted_items > 10 else 1, 1])

                # Сохранение графика
                if save_path:
                    try:
                        plt.savefig(save_path, dpi=300, bbox_inches='tight')
                        logger.info(f"График коротких/длинных сообщений сохранен в {save_path}")
                    except Exception as e:
                        logger.error(f"Не удалось сохранить график коротких/длинных сообщений в {save_path}: {e}")
                # plt.show()
                plt.close()
        logger.info("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе коротких/длинных сообщений: {e}", exc_info=True)
        plt.close()

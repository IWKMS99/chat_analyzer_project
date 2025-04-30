# === Standard library ===
import argparse
import logging
import os
import sys
import time

# === Project specific imports ===
from chat_analyzer.data_loader import load_and_process_chat_data
from chat_analyzer.utils import setup_logging, ensure_dir

# Import analysis functions (можно импортировать весь модуль или конкретные функции)
from chat_analyzer.analysis import summary as summary_analysis
from chat_analyzer.analysis import activity as activity_analysis
from chat_analyzer.analysis import temporal as temporal_analysis
from chat_analyzer.analysis import user as user_analysis
from chat_analyzer.analysis import nlp as nlp_analysis
from chat_analyzer.analysis import message as message_analysis
from chat_analyzer.analysis import dialog as dialog_analysis
from chat_analyzer.analysis import anomaly as anomaly_analysis

# Получаем корневой логгер
logger = logging.getLogger(__name__)


def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(description="Анализатор JSON экспорта чатов Telegram.")
    parser.add_argument(
        "input_file",
        type=str,
        help="Путь к входному JSON файлу (result.json)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="output",
        help="Директория для сохранения графиков и отчетов (по умолчанию: output)."
    )
    parser.add_argument(
        "-tz", "--timezone",
        type=str,
        default="Europe/Moscow",  # Изменено на Москву как более частый вариант
        help="Временная зона для отображения дат в сводке (по умолчанию: Europe/Moscow)."
    )
    parser.add_argument(
        "-log", "--log-level",
        type=str,
        default="INFO",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Уровень логирования (по умолчанию: INFO)."
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,  # "output/analysis.log", # По умолчанию не пишем в файл
        help="Файл для записи логов (по умолчанию: None)."
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Пропустить генерацию и сохранение всех графиков."
    )
    parser.add_argument(
        "--max-legend",
        type=int,
        default=10,
        help="Максимальное количество элементов в легендах графиков (по умолчанию: 10)."
    )
    # Добавьте другие аргументы для управления параметрами анализа при необходимости
    # Например, пороги для аномалий, временные окна и т.д.
    parser.add_argument(
        "--anomaly-threshold",
        type=float,
        default=2.0,
        help="Порог Z-score для аномальной дневной активности (по умолчанию: 2.0)."
    )
    parser.add_argument(
        "--response-time-limit",
        type=float,
        default=60.0,
        help="Максимальный интервал (минуты) для учета времени ответа (по умолчанию: 60.0)."
    )
    parser.add_argument(
        "--session-gap",
        type=float,
        default=30.0,
        help="Максимальный разрыв (минуты) для определения новой сессии диалога (по умолчанию: 30.0)."
    )

    args = parser.parse_args()

    # 1. Настройка логирования
    log_filepath = os.path.join(args.output_dir, "analysis.log") if args.log_file else None
    setup_logging(log_level=args.log_level, log_file=log_filepath)

    logger.info("Запуск анализа чата...")
    logger.info(f"Входной файл: {args.input_file}")
    logger.info(f"Выходная директория: {args.output_dir}")
    logger.info(f"Временная зона: {args.timezone}")

    # 2. Создание выходной директории
    ensure_dir(args.output_dir)

    # 3. Загрузка и обработка данных
    logger.info("Загрузка и обработка данных...")
    df = load_and_process_chat_data(args.input_file)

    if df is None or df.empty:
        logger.critical("Не удалось загрузить или обработать данные. Анализ прерван.")
        sys.exit(1)  # Выход с кодом ошибки

    logger.info(f"Данные успешно загружены. Обнаружено {len(df)} сообщений.")
    logger.debug(f"Колонки DataFrame: {df.columns.tolist()}")
    logger.debug(f"Первые 5 строк:\n{df.head().to_string()}")

    # 4. Выполнение анализа (с возможностью пропуска графиков)

    # --- Базовая сводка ---
    logger.info("Генерация базовой сводки...")
    summary_analysis.summarize_chat(
        df,
        timezone=args.timezone,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '01_top_authors.png')
    )

    # --- Анализ активности ---
    logger.info("Анализ активности по времени...")
    activity_analysis.plot_hourly_activity(
        df, percentage=True,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '02_activity_hourly_percent.png'),
        max_legend_items=args.max_legend
    )
    activity_analysis.plot_hourly_activity(
        df, percentage=False,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '03_activity_hourly_absolute.png'),
        max_legend_items=args.max_legend
    )
    activity_analysis.plot_weekday_activity(
        df, stacked=False,  # Сначала сгруппированный
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '04_activity_weekday_grouped.png'),
        max_legend_items=args.max_legend
    )
    activity_analysis.plot_weekday_activity(
        df, stacked=True,  # Потом stacked
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '05_activity_weekday_stacked.png'),
        max_legend_items=args.max_legend
    )
    activity_analysis.plot_monthly_activity(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '06_activity_monthly.png'),
        max_legend_items=args.max_legend
    )
    activity_analysis.analyze_time_periods(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '07_activity_time_periods.png'),
        max_legend_items=args.max_legend
    )

    # --- Временной анализ ---
    logger.info("Временной анализ...")
    _ = temporal_analysis.calculate_response_time(df,
                                                  max_interval_minutes=args.response_time_limit)  # Выводим статистику
    temporal_analysis.plot_response_time_distribution(
        df, max_interval_minutes=args.response_time_limit,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '08_response_time_distribution.png')
    )
    daily_counts = temporal_analysis.plot_daily_activity_with_moving_averages(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '09_daily_activity_ma.png')
    )
    if daily_counts is not None:  # Проверяем, что данные для декомпозиции есть
        temporal_analysis.perform_seasonal_decomposition(
            daily_counts, period=7, model='additive',  # Недельная сезонность
            save_path=None if args.skip_plots else os.path.join(args.output_dir, '10_seasonal_decomp_weekly.png')
        )
        # Можно добавить и месячную, если данных достаточно
        if len(daily_counts) > 60:
            temporal_analysis.perform_seasonal_decomposition(
                daily_counts, period=30, model='additive',  # Месячная сезонность
                save_path=None if args.skip_plots else os.path.join(args.output_dir, '11_seasonal_decomp_monthly.png')
            )
    temporal_analysis.analyze_message_intervals(
        df, max_interval_seconds=3600,  # Интервалы до часа
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '12_message_intervals.png')
    )

    # --- Анализ пользователей ---
    logger.info("Анализ пользователей...")
    user_analysis.plot_user_message_counts(
        df, top_n=args.max_legend,  # Используем max_legend для консистентности
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '13_user_message_counts.png')
    )
    user_analysis.plot_user_avg_message_length(
        df, top_n=args.max_legend,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '14_user_avg_length.png')
    )
    user_analysis.analyze_message_chains(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '15_message_chains.png'),
        max_legend_items=args.max_legend
    )
    user_analysis.analyze_most_active_days(
        df, top_n=5,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '16_most_active_days.png'),
        max_legend_items=args.max_legend
    )

    # --- Анализ сообщений ---
    logger.info("Анализ характеристик сообщений...")
    message_analysis.analyze_message_length(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '17_message_length_distribution.png'),
        max_legend_items=args.max_legend
    )
    message_analysis.analyze_question_messages(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '18_question_messages.png'),
        max_legend_items=args.max_legend
    )
    message_analysis.analyze_short_long_messages(
        df, length_threshold=50,  # Пример порога
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '19_short_long_messages.png'),
        max_legend_items=args.max_legend
    )

    # --- Анализ диалогов ---
    logger.info("Анализ диалогов...")
    dialog_analysis.analyze_dialog_sessions(
        df, max_gap_minutes=args.session_gap,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '20_dialog_sessions.png')
    )
    dialog_analysis.analyze_dialog_balance(
        df, max_gap_minutes=args.session_gap,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '21_dialog_balance.png')
    )
    dialog_analysis.analyze_dialog_intensity(
        df, time_window='1H',  # Анализ по часам
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '22_dialog_intensity.png'),
        max_legend_items=args.max_legend
    )
    dialog_analysis.analyze_dialog_initiators(
        df, max_gap_minutes=args.session_gap,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '23_dialog_initiators.png')
    )

    # --- NLP Анализ ---
    logger.info("NLP анализ (ключевые слова, облако, словарь, эмодзи)...")
    nlp_analysis.analyze_keywords(
        df, top_n=50,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '24_keywords_barplot.png')
    )
    nlp_analysis.generate_word_cloud(
        df, max_words=150,  # Больше слов для облака
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '25_word_cloud.png')
    )
    nlp_analysis.analyze_vocabulary(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '26_vocabulary_analysis.png')
    )
    nlp_analysis.analyze_emoji_usage(
        df,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '27_emoji_usage.png')
    )

    # --- Анализ аномалий ---
    logger.info("Анализ аномалий...")
    anomaly_analysis.analyze_anomalous_days(
        df, threshold=args.anomaly_threshold,
        save_path=None if args.skip_plots else os.path.join(args.output_dir, '28_anomalous_days.png')
    )

    end_time = time.time()
    logger.info(f"Анализ завершен за {end_time - start_time:.2f} секунд.")
    logger.info(f"Результаты сохранены в директории: {args.output_dir}")


if __name__ == "__main__":
    main()

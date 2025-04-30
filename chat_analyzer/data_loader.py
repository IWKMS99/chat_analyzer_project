# === Standard library ===
import json
import logging
from typing import Optional

# === Data handling ===
import pandas as pd

logger = logging.getLogger(__name__)


def load_and_process_chat_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    Загружает JSON экспорт чата и преобразует в DataFrame.

    Args:
        file_path: Путь к JSON-файлу с экспортом чата.
                   Ожидаемая структура: {'messages': [{'date': str, 'from': str, 'text': str/list, 'type': str}, ...]}

    Returns:
        DataFrame с полями date, date_only, hour, from, text, day_of_week, text_length, from_id
        или None в случае ошибки.
    """
    try:
        with open(file_path, encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при чтении файла {file_path}: {e}")
        return None

    messages = raw.get('messages', [])
    if not messages:
        logger.warning("JSON не содержит ключ 'messages' или список сообщений пуст.")
        # Попробуем найти сообщения в корне, если 'messages' нет (на всякий случай)
        if isinstance(raw, list):
            messages = raw
        else:
            logger.warning("Не найдено сообщений для анализа.")
            return None

    # Фильтруем только сообщения с текстом и типом 'message'
    msgs = [
        m for m in messages
        if isinstance(m, dict) and m.get('type') == 'message' and 'text' in m and m.get('from')
    ]
    if not msgs:
        logger.warning("Нет текстовых сообщений типа 'message' с отправителем для анализа.")
        return None

    df = pd.DataFrame(msgs)

    # Оставляем только нужные колонки на раннем этапе
    df = df[['date', 'from', 'text', 'from_id']]  # Добавим 'from_id' если он есть

    # Нормализация текста для обработки составных сообщений
    def normalize_text(x):
        if isinstance(x, str):
            return x
        if isinstance(x, list):
            # Собираем текст из частей, обрабатывая строки и словари
            parts = []
            for part in x:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and 'text' in part:
                    parts.append(str(part['text']))  # Убедимся, что текст - строка
            return ''.join(parts)
        return str(x)  # Преобразуем в строку на всякий случай

    df['text'] = df['text'].apply(normalize_text)
    df = df[df['text'].astype(str).str.strip() != '']  # Удаляем сообщения с пустым текстом после нормализации

    if df.empty:
        logger.warning("Нет сообщений с непустым текстом после нормализации.")
        return None

    # Преобразование дат
    try:
        # Пробуем разные форматы, если стандартный не сработал
        df['date'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
        # Удаляем строки, где дата не распозналась
        df.dropna(subset=['date'], inplace=True)
        if df.empty:
            logger.error("Не удалось распознать даты ни в одном сообщении.")
            return None
    except Exception as e:  # Ловим более общие ошибки парсинга дат
        logger.error(f"Критическая ошибка преобразования дат: {e}")
        return None

    df['date_only'] = df['date'].dt.date
    df['hour'] = df['date'].dt.hour
    df['day_of_week'] = df['date'].dt.day_name()
    df['text_length'] = df['text'].astype(str).str.len()  # Длина сообщения

    # Обработка анонимных пользователей (если 'from' пустой или специфический символ)
    df['from'] = df['from'].replace(['', ' ', 'ㅤ', None], 'UnknownUser')
    df['from'] = df['from'].fillna('UnknownUser')  # Обработка NaN

    # Убедимся, что from_id существует, если нет - создадим на основе 'from'
    if 'from_id' not in df.columns:
        df['from_id'] = df['from']  # Используем 'from' как ID, если ID нет

    logger.info(f"Загружено и обработано {len(df)} сообщений.")
    return df[['date', 'date_only', 'hour', 'from', 'from_id', 'text', 'day_of_week', 'text_length']]

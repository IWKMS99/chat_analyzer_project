# === Standard library ===
import json
import logging
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

# === Third-party ===
import pandas as pd

try:
    import ijson
except ImportError:  # pragma: no cover
    ijson = None

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Базовая ошибка загрузки данных чата."""


class EmptyDataError(DataLoadError):
    """Не найдено сообщений для анализа."""


class InvalidSchemaError(DataLoadError):
    """JSON имеет неожиданную структуру."""


@dataclass
class MessageRecord:
    date: pd.Timestamp
    sender: str
    sender_id: str
    text: str
    is_forwarded: bool
    is_edited: bool
    is_deleted: bool
    reactions: List[str]


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: List[str] = []
        for part in value:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
        return "".join(parts)
    return str(value)


def _extract_reactions(message: Dict[str, Any]) -> List[str]:
    reactions = message.get("reactions")
    if reactions is None:
        return []
    extracted: List[str] = []
    if isinstance(reactions, list):
        for item in reactions:
            if isinstance(item, str):
                extracted.append(item)
            elif isinstance(item, dict):
                value = item.get("reaction") or item.get("emoji") or item.get("text")
                if value:
                    extracted.append(str(value))
        return extracted

    if isinstance(reactions, dict):
        candidates = reactions.get("recent") or reactions.get("results") or reactions.get("items") or []
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    value = item.get("reaction") or item.get("emoji") or item.get("text")
                    if value:
                        extracted.append(str(value))
                elif isinstance(item, str):
                    extracted.append(item)
        return extracted

    return []


def _iter_messages_streaming(file_path: str) -> Iterator[Dict[str, Any]]:
    if ijson is None:
        raise DataLoadError("Библиотека ijson не установлена.")

    with open(file_path, "rb") as f:
        try:
            yielded = False
            for message in ijson.items(f, "messages.item"):
                yielded = True
                if isinstance(message, dict):
                    yield message
            if yielded:
                return
        except Exception as exc:  # pragma: no cover
            raise DataLoadError(f"Ошибка чтения JSON (streaming messages.item): {exc}") from exc

    with open(file_path, "rb") as f:
        try:
            yielded = False
            for message in ijson.items(f, "item"):
                yielded = True
                if isinstance(message, dict):
                    yield message
            if yielded:
                return
        except Exception as exc:  # pragma: no cover
            raise DataLoadError(f"Ошибка чтения JSON (streaming item): {exc}") from exc

    raise InvalidSchemaError("Ожидался JSON-объект с ключом 'messages' или список сообщений.")


def _iter_messages_fallback(file_path: str) -> Iterator[Dict[str, Any]]:
    try:
        with open(file_path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Файл {file_path} не найден.") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Ошибка парсинга JSON: {exc}") from exc

    if isinstance(raw, dict):
        messages = raw.get("messages")
        if messages is None:
            raise InvalidSchemaError("В JSON отсутствует ключ 'messages'.")
        if not isinstance(messages, list):
            raise InvalidSchemaError("Поле 'messages' должно быть списком.")
        for message in messages:
            if isinstance(message, dict):
                yield message
        return

    if isinstance(raw, list):
        for message in raw:
            if isinstance(message, dict):
                yield message
        return

    raise InvalidSchemaError("Ожидался JSON-объект с ключом 'messages' или список сообщений.")


def _iter_messages(file_path: str) -> Iterator[Dict[str, Any]]:
    if ijson is None:
        logger.warning("ijson недоступен, используется fallback через json.load().")
        yield from _iter_messages_fallback(file_path)
        return

    try:
        yield from _iter_messages_streaming(file_path)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Файл {file_path} не найден.") from exc
    except DataLoadError as exc:
        logger.warning("Streaming-парсинг не удался (%s), используется fallback через json.load().", exc)
        yield from _iter_messages_fallback(file_path)


def _normalize_message_record(message: Dict[str, Any]) -> Optional[MessageRecord]:
    if message.get("type") != "message":
        return None

    author = message.get("from")
    if not author:
        return None

    text = _normalize_text(message.get("text", ""))
    if not text.strip():
        return None

    parsed_date = pd.to_datetime(message.get("date"), errors="coerce", utc=True)
    if pd.isna(parsed_date):
        return None

    return MessageRecord(
        date=parsed_date,
        sender=str(author).strip() or "UnknownUser",
        sender_id=str(message.get("from_id") or author),
        text=text,
        is_forwarded=bool(message.get("forwarded_from")),
        is_edited=bool(message.get("edited") or message.get("edited_unixtime")),
        is_deleted=bool(message.get("is_deleted") or message.get("deleted") or message.get("media_type") == "deleted_message"),
        reactions=_extract_reactions(message),
    )


def iter_chat_messages(file_path: str, normalize: bool = True) -> Iterator[MessageRecord | Dict[str, Any]]:
    """Итерирует сообщения чата в потоковом режиме."""
    for message in _iter_messages(file_path):
        if not normalize:
            yield message
            continue
        record = _normalize_message_record(message)
        if record is not None:
            yield record


def _rows_to_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date_only"] = df["date"].dt.date
    df["hour"] = df["date"].dt.hour.astype("int8")
    df["day_of_week"] = df["date"].dt.day_name().astype("category")
    df["text_length"] = df["text"].str.len().astype("int32")

    for col in ("from", "from_id"):
        df[col] = df[col].replace(["", " ", "ㅤ", None], "UnknownUser").fillna("UnknownUser").astype("category")

    for col in ("is_forwarded", "is_edited", "is_deleted"):
        df[col] = df[col].astype("bool")

    return df[
        [
            "date",
            "date_only",
            "hour",
            "from",
            "from_id",
            "text",
            "day_of_week",
            "text_length",
            "is_forwarded",
            "is_edited",
            "is_deleted",
            "reactions",
        ]
    ]


def iter_chat_chunks(file_path: str, chunk_size: int = 50_000) -> Iterator[pd.DataFrame]:
    """Итерирует чанки DataFrame с нормализованными сообщениями."""
    if chunk_size <= 0:
        raise ValueError("chunk_size должен быть положительным")

    rows: List[Dict[str, Any]] = []
    for record in iter_chat_messages(file_path, normalize=True):
        rows.append(
            {
                "date": record.date,
                "from": record.sender,
                "from_id": record.sender_id,
                "text": record.text,
                "is_forwarded": record.is_forwarded,
                "is_edited": record.is_edited,
                "is_deleted": record.is_deleted,
                "reactions": record.reactions,
            }
        )
        if len(rows) >= chunk_size:
            yield _rows_to_dataframe(rows)
            rows = []

    if rows:
        yield _rows_to_dataframe(rows)


def load_and_process_chat_data(file_path: str, chunk_size: int = 50_000) -> pd.DataFrame:
    """Deprecated: используйте iter_chat_messages/iter_chat_chunks."""
    warnings.warn(
        "load_and_process_chat_data устарела, используйте iter_chat_chunks/iter_chat_messages",
        DeprecationWarning,
        stacklevel=2,
    )

    chunks = [chunk for chunk in iter_chat_chunks(file_path=file_path, chunk_size=chunk_size) if not chunk.empty]
    if not chunks:
        raise EmptyDataError("Нет текстовых сообщений типа 'message' с отправителем для анализа.")

    df = pd.concat(chunks, ignore_index=True)
    if df.empty:
        raise EmptyDataError("Не найдено сообщений после фильтрации.")

    logger.info("Загружено и обработано %s сообщений.", len(df))
    return df

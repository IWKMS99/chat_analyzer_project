from .nlp_processor import (
    NlpBatchResult,
    default_workers,
    extract_emojis_from_text,
    process_texts_spacy,
    update_emoji_counter,
)

__all__ = [
    "NlpBatchResult",
    "default_workers",
    "extract_emojis_from_text",
    "process_texts_spacy",
    "update_emoji_counter",
]

# === Standard library ===
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Sequence

import emoji

try:
    import spacy
except ImportError:  # pragma: no cover
    spacy = None

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\w\-']+", flags=re.UNICODE)
_URL_RE = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
_EMAIL_RE = re.compile(r"\S+@\S+")

RU_POSITIVE = {
    "круто", "класс", "отлично", "хорошо", "люблю", "супер", "рад", "счастлив", "спасибо", "красиво",
}
RU_NEGATIVE = {
    "плохо", "ужас", "ненавижу", "токс", "злюсь", "грустно", "печально", "бесит", "отстой", "мерзко",
}
EN_POSITIVE = {
    "good", "great", "awesome", "love", "nice", "happy", "thanks", "excellent", "amazing", "beautiful",
}
EN_NEGATIVE = {
    "bad", "awful", "hate", "toxic", "angry", "sad", "terrible", "annoying", "worst", "ugly",
}


@dataclass
class NlpBatchResult:
    tokens_per_text: List[List[str]]
    sentiment_scores: List[float]


def _clean_text(text: str) -> str:
    text = _URL_RE.sub(" ", str(text))
    return _EMAIL_RE.sub(" ", text)


def _load_model(model_name: str):
    if spacy is None:
        return None
    try:
        return spacy.load(model_name, disable=["parser", "ner", "textcat"])
    except Exception:
        logger.warning("spaCy model %s недоступна, используется fallback tokenizer.", model_name)
        return None


@lru_cache(maxsize=1)
def get_nlp_models() -> tuple:
    if spacy is None:
        logger.warning("spaCy не установлен. NLP будет работать в fallback режиме.")
        return (None, None)

    ru = _load_model("ru_core_news_sm")
    en = _load_model("en_core_web_sm")

    if ru is None and en is None:
        # fallback на blank-токенизатор, чтобы пайплайн не падал
        ru = spacy.blank("ru")
        en = spacy.blank("en")
    return (ru, en)


def _score_sentiment_tokens(tokens: Sequence[str]) -> float:
    if not tokens:
        return 0.0
    pos = 0
    neg = 0
    for token in tokens:
        lower = token.lower()
        if lower in RU_POSITIVE or lower in EN_POSITIVE:
            pos += 1
        elif lower in RU_NEGATIVE or lower in EN_NEGATIVE:
            neg += 1
    return (pos - neg) / max(len(tokens), 1)


def _fallback_tokenize(texts: Iterable[str], min_len: int = 3) -> NlpBatchResult:
    tokens_per_text: List[List[str]] = []
    sentiments: List[float] = []
    for text in texts:
        cleaned = _clean_text(text).lower()
        tokens = [tok for tok in _TOKEN_RE.findall(cleaned) if len(tok) >= min_len]
        tokens_per_text.append(tokens)
        sentiments.append(_score_sentiment_tokens(tokens))
    return NlpBatchResult(tokens_per_text=tokens_per_text, sentiment_scores=sentiments)


def process_texts_spacy(
    texts: Sequence[str],
    batch_size: int = 1000,
    n_process: int | None = None,
    min_len: int = 3,
) -> NlpBatchResult:
    if not texts:
        return NlpBatchResult(tokens_per_text=[], sentiment_scores=[])

    ru_model, en_model = get_nlp_models()
    if ru_model is None and en_model is None:
        return _fallback_tokenize(texts, min_len=min_len)

    # Простая эвристика роутинга: кириллица -> ru, иначе en.
    ru_indices: List[int] = []
    en_indices: List[int] = []
    clean_texts = [_clean_text(t) for t in texts]
    for idx, text in enumerate(clean_texts):
        if any("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in text):
            ru_indices.append(idx)
        else:
            en_indices.append(idx)

    tokens_per_text: List[List[str]] = [[] for _ in texts]

    def _consume(indices: List[int], model):
        if not indices or model is None:
            return
        selected = [clean_texts[i] for i in indices]
        kwargs = {"batch_size": batch_size}
        if n_process is not None and n_process > 1:
            kwargs["n_process"] = n_process
        for original_idx, doc in zip(indices, model.pipe(selected, **kwargs)):
            tokens: List[str] = []
            for token in doc:
                if token.is_space or token.is_punct or token.is_stop:
                    continue
                if not token.is_alpha:
                    continue
                lemma = (token.lemma_ or token.text).lower().strip()
                if len(lemma) < min_len:
                    continue
                tokens.append(lemma)
            tokens_per_text[original_idx] = tokens

    _consume(ru_indices, ru_model)
    _consume(en_indices, en_model)

    sentiments = [_score_sentiment_tokens(tokens) for tokens in tokens_per_text]
    return NlpBatchResult(tokens_per_text=tokens_per_text, sentiment_scores=sentiments)


def extract_emojis_from_text(text: str) -> List[str]:
    return [item["emoji"] for item in emoji.emoji_list(str(text))]


def update_emoji_counter(counter: Counter, texts: Sequence[str]) -> None:
    for text in texts:
        counter.update(extract_emojis_from_text(text))


def default_workers() -> int:
    cpu = os.cpu_count() or 2
    return max(cpu - 1, 1)

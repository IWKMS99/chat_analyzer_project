from chat_analyzer.analysis.nlp_spacy import extract_emojis_from_text, process_texts_spacy


def test_spacy_processing_returns_lemmas_or_tokens():
    result = process_texts_spacy(["Я делал и она делала, будем делать.", "This is very good and awesome"], batch_size=8, n_process=1)
    assert len(result.tokens_per_text) == 2
    assert any(token.startswith("дел") for token in result.tokens_per_text[0]) or result.tokens_per_text[0]


def test_emoji_extraction_handles_combined_emoji():
    items = extract_emojis_from_text("Ок 👍🏽 и 😄")
    assert "👍🏽" in items
    assert "😄" in items


def test_sentiment_keeps_negations():
    result = process_texts_spacy(["не хорошо", "not good"], batch_size=8, n_process=1)
    assert result.sentiment_scores[0] < 0
    assert result.sentiment_scores[1] < 0

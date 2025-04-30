# === Standard library ===
import logging
import re
from collections import Counter
from typing import Optional, List, Dict

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt
from wordcloud import WordCloud

logger = logging.getLogger(__name__)


# --- Простая замена для pymorphy2 ---
class SimpleWord:
    def __init__(self, word: str, normal_form: str):
        self.word = word
        self._normal_form = normal_form

    @property
    def normal_form(self) -> str:
        return self._normal_form

    # Добавляем методы, чтобы имитировать объект Parse из pymorphy2
    def __getitem__(self, index):
        if index == 0:
            return self
        raise IndexError("SimpleWord only supports index 0")

    def __iter__(self):
        yield self


class SimpleMorphAnalyzer:
    def __init__(self):
        # Простой кеш для ускорения (хотя нормализация тут тривиальная)
        self.cache: Dict[str, List[SimpleWord]] = {}
        # Очень базовый список стоп-слов (можно расширить)
        self.stop_words = {'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она',
                           'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее',
                           'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда',
                           'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас',
                           'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может',
                           'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам',
                           'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто',
                           'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один',
                           'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда',
                           'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот',
                           'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя',
                           'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя',
                           'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между'}

    def parse(self, word: str) -> List[SimpleWord]:
        # Приводим к нижнему регистру перед поиском в кеше
        lower_word = word.lower()
        if lower_word in self.cache:
            return self.cache[lower_word]

        # Простая нормализация: просто возвращаем слово в нижнем регистре
        # В реальном сценарии здесь был бы сложный морфологический анализ
        # Исключаем стоп-слова и короткие слова на этом этапе
        if len(lower_word) > 2 and lower_word not in self.stop_words:
            normalized = lower_word
        else:
            normalized = ""  # Возвращаем пустую строку для стоп-слов или коротких слов

        result = [SimpleWord(word, normalized)]
        self.cache[lower_word] = result
        return result


# Глобальный экземпляр анализатора
morph = SimpleMorphAnalyzer()


def preprocess_text_for_nlp(text: str) -> List[str]:
    """Очищает текст, токенизирует и нормализует слова для NLP задач."""
    # 1. Приведение к нижнему регистру
    text = str(text).lower()
    # 2. Удаление URL
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # 3. Удаление email адресов
    text = re.sub(r'\S+@\S+', '', text)
    # 4. Удаление пунктуации (кроме дефисов внутри слов, если нужно) и цифр
    # Оставляем только буквы и пробелы (можно добавить апострофы/дефисы при необходимости)
    text = re.sub(r'[^а-яa-z\s]', '', text)  # Только кириллица, латиница и пробелы
    # 5. Токенизация по пробелам
    words = text.split()
    # 6. Нормализация и фильтрация стоп-слов/коротких слов с помощью SimpleMorphAnalyzer
    processed_words = [
        parsed[0].normal_form
        for word in words
        # Проверяем, что parse вернул непустой список и normal_form не пустая строка
        if (parsed := morph.parse(word)) and parsed[0].normal_form
    ]
    return processed_words


def analyze_keywords(df: pd.DataFrame, top_n: int = 50, save_path: Optional[str] = None) -> None:
    """Находит и визуализирует наиболее частые слова (кроме стоп-слов)."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа ключевых слов.")
        return

    required_columns = ['text']
    if 'text' not in df:
        logger.error(f"Отсутствует необходимый столбец для analyze_keywords: 'text'")
        return

    try:
        print("\n--- Анализ ключевых слов ---")
        # Сбор всех слов с предобработкой
        all_words = []
        total_messages = len(df['text'])
        processed_count = 0
        # Используем .dropna() перед итерацией
        for i, text in enumerate(df['text'].dropna()):
            all_words.extend(preprocess_text_for_nlp(text))
            processed_count += 1
            if (i + 1) % 1000 == 0:
                logger.info(f"Обработано {i + 1}/{total_messages} сообщений для ключевых слов...")

        logger.info(f"Завершено: Обработано {processed_count}/{total_messages} сообщений для ключевых слов.")

        if not all_words:
            logger.warning("Не найдено слов для анализа после предобработки.")
            print("Не найдено слов для анализа после предобработки.")
            print("-" * 20)
            return

        # Самые частые слова
        word_counts = Counter(all_words)
        common_words = word_counts.most_common(top_n)

        if not common_words:
            logger.warning("Список самых частых слов пуст.")
            print("Список самых частых слов пуст.")
            print("-" * 20)
            return

        print(f"Топ-{len(common_words)} слов (после предобработки и удаления стоп-слов):")
        # Вывод в более читаемом формате
        for word, count in common_words:
            print(f"- {word}: {count}")

        # Визуализация
        top_words_series = pd.Series(dict(common_words))
        plt.figure(figsize=(12, max(6, top_n // 4)))  # Динамическая высота
        top_words_series.sort_values(ascending=True).plot(kind='barh',
                                                          color='teal')  # Горизонтальный график лучше для слов

        plt.title(f'Топ-{len(common_words)} наиболее частых слов', fontsize=16)
        plt.xlabel('Частота', fontsize=12)
        plt.ylabel('Слово', fontsize=12)
        plt.grid(True, axis='x', linestyle='--', alpha=0.7)  # Сетка по X
        plt.tight_layout()

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"График ключевых слов сохранен в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить график ключевых слов в {save_path}: {e}")
        # plt.show()
        plt.close()
        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе ключевых слов: {e}", exc_info=True)
        plt.close()


def generate_word_cloud(df: pd.DataFrame, max_words: int = 100, save_path: Optional[str] = None) -> None:
    """Генерирует облако слов на основе текстов сообщений."""
    if df is None or df.empty:
        logger.warning("Нет данных для генерации облака слов.")
        return

    required_columns = ['text']
    if 'text' not in df:
        logger.error(f"Отсутствует необходимый столбец для generate_word_cloud: 'text'")
        return

    try:
        print("\n--- Генерация облака слов ---")
        # Сбор всех слов с предобработкой (аналогично analyze_keywords)
        all_words = []
        total_messages = len(df['text'])
        processed_count = 0
        for i, text in enumerate(df['text'].dropna()):
            all_words.extend(preprocess_text_for_nlp(text))
            processed_count += 1
            if (i + 1) % 1000 == 0:
                logger.info(f"Обработано {i + 1}/{total_messages} сообщений для облака слов...")
        logger.info(f"Завершено: Обработано {processed_count}/{total_messages} сообщений для облака слов.")

        if not all_words:
            logger.warning("Нет слов для генерации облака после предобработки.")
            print("Нет слов для генерации облака после предобработки.")
            print("-" * 20)
            return

        # Подсчет частот
        word_counts = Counter(all_words)

        if not word_counts:
            logger.warning("Счетчик слов пуст для облака слов.")
            print("Счетчик слов пуст для облака слов.")
            print("-" * 20)
            return

        # Создание облака слов
        # Убедимся, что max_words не больше реального количества уникальных слов
        actual_max_words = min(max_words, len(word_counts))
        logger.info(f"Генерация облака слов из {len(word_counts)} уникальных слов (макс. {actual_max_words}).")

        wordcloud = WordCloud(width=1200, height=600, background_color='white', max_words=actual_max_words,
                              colormap='viridis').generate_from_frequencies(word_counts)

        plt.figure(figsize=(15, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        plt.tight_layout(pad=0)  # Убираем лишние поля

        if save_path:
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Облако слов сохранено в {save_path}")
            except Exception as e:
                logger.error(f"Не удалось сохранить облако слов в {save_path}: {e}")
        # plt.show()
        plt.close()
        print("-" * 20)

    except ImportError:
        logger.error(
            "Библиотека wordcloud не установлена. Невозможно сгенерировать облако слов. Установите: pip install wordcloud")
    except Exception as e:
        logger.error(f"Ошибка при генерации облака слов: {e}", exc_info=True)
        plt.close()


def analyze_vocabulary(df: pd.DataFrame, save_path: Optional[str] = None) -> None:
    """Анализирует словарный запас каждого участника."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа словарного запаса.")
        return

    required_columns = ['text', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_vocabulary: {required_columns}")
        return

    try:
        print("\n--- Анализ словарного запаса ---")
        vocab_stats = {}
        participants = df['from'].unique()

        # Подсчет слов для каждого участника
        for participant in participants:
            participant_texts = df[df['from'] == participant]['text'].dropna()
            logger.info(f"Анализ словаря для {participant} ({len(participant_texts)} сообщений)...")

            participant_words = []
            for text in participant_texts:
                participant_words.extend(preprocess_text_for_nlp(text))

            if not participant_words:
                logger.warning(f"Не найдено слов для участника {participant} после предобработки.")
                vocab_stats[participant] = {
                    'total_words': 0,
                    'unique_words': 0,
                    'lexical_diversity': 0,
                    'top_5_words': []
                }
                continue

            word_counts = Counter(participant_words)
            total_words = sum(word_counts.values())
            unique_words = len(word_counts)
            lexical_diversity = unique_words / total_words if total_words > 0 else 0

            vocab_stats[participant] = {
                'total_words': total_words,
                'unique_words': unique_words,
                'lexical_diversity': lexical_diversity,  # Лексическое разнообразие
                'top_5_words': word_counts.most_common(5)
            }

        # Вывод статистики
        for participant, stats in vocab_stats.items():
            print(f"\n{participant}:")
            print(f"  Общее количество слов (после обработки): {stats['total_words']}")
            print(f"  Уникальные слова: {stats['unique_words']}")
            print(f"  Лексическое разнообразие: {stats['lexical_diversity']:.3f}")  # TTR - Type-Token Ratio
            top_words_str = ', '.join([f"{word} ({count})" for word, count in stats['top_5_words']]) if stats[
                'top_5_words'] else "N/A"
            print(f"  Топ-5 слов: {top_words_str}")

        # График: количество уникальных слов
        if vocab_stats:
            participants_list = list(vocab_stats.keys())
            unique_counts = [stats['unique_words'] for stats in vocab_stats.values()]
            total_counts = [stats['total_words'] for stats in vocab_stats.values()]
            diversity_scores = [stats['lexical_diversity'] for stats in vocab_stats.values()]

            fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
            fig.suptitle('Анализ словарного запаса по участникам', fontsize=16, y=1.01)

            # График 1: Уникальные слова
            axes[0].bar(participants_list, unique_counts, color='cornflowerblue')
            axes[0].set_title('Количество уникальных слов', fontsize=14)
            axes[0].set_ylabel('Количество', fontsize=12)
            axes[0].grid(True, axis='y', linestyle='--', alpha=0.7)

            # График 2: Общее количество слов
            axes[1].bar(participants_list, total_counts, color='lightcoral')
            axes[1].set_title('Общее количество слов (после обработки)', fontsize=14)
            axes[1].set_ylabel('Количество', fontsize=12)
            axes[1].grid(True, axis='y', linestyle='--', alpha=0.7)

            # График 3: Лексическое разнообразие
            axes[2].bar(participants_list, diversity_scores, color='mediumseagreen')
            axes[2].set_title('Лексическое разнообразие (Уникальные / Всего)', fontsize=14)
            axes[2].set_ylabel('Коэффициент', fontsize=12)
            axes[2].set_xlabel('Участник', fontsize=12)
            axes[2].grid(True, axis='y', linestyle='--', alpha=0.7)
            axes[2].tick_params(axis='x', rotation=45)  # Поворот меток на последнем графике

            plt.tight_layout(rect=[0, 0, 1, 0.98])

            # Сохранение графика
            if save_path:
                try:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    logger.info(f"График анализа словарного запаса сохранен в {save_path}")
                except Exception as e:
                    logger.error(f"Не удалось сохранить график анализа словарного запаса в {save_path}: {e}")
            # plt.show()
            plt.close()
        else:
            logger.warning("Нет данных для построения графика словарного запаса.")

        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе словарного запаса: {e}", exc_info=True)
        plt.close()


def analyze_emoji_usage(df: pd.DataFrame, save_path: Optional[str] = None) -> None:
    """Анализирует использование эмодзи."""
    if df is None or df.empty:
        logger.warning("Нет данных для анализа использования эмодзи.")
        return

    required_columns = ['text', 'from']
    if not all(col in df for col in required_columns):
        logger.error(f"Отсутствуют необходимые столбцы для analyze_emoji_usage: {required_columns}")
        return

    try:
        # Улучшенное регулярное выражение для поиска эмодзи (охватывает больше диапазонов)
        # Источник: https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python
        emoji_pattern = re.compile(
            "["
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"
            "\U00002600-\U000026FF"  # Miscellaneous Symbols
            # Вариации и модификаторы пропускаем (пока)
            # "\U0000FE00-\U0000FE0F"  # variation selectors
            # "\U0001F004"            # Mahjong tile red dragon
            # "\U0001F0CF"            # Playing card black joker
            # "\U0000200D"            # Zero width joiner
            # "\U000020E3"            # Combining enclosing keycap
            "]+",
            flags=re.UNICODE)

        def extract_emojis(text: str) -> List[str]:
            if not isinstance(text, str):  # Проверка типа
                return []
            return emoji_pattern.findall(text)

        print("\n--- Анализ использования эмодзи ---")
        # Подсчет эмодзи для каждого участника
        emoji_stats = {}
        total_emojis_found = 0
        participants = df['from'].unique()

        for participant in participants:
            participant_texts = df[df['from'] == participant]['text'].dropna()
            logger.info(f"Анализ эмодзи для {participant} ({len(participant_texts)} сообщений)...")

            participant_emojis = [
                emoji for text in participant_texts for emoji in extract_emojis(text)
            ]

            if not participant_emojis:
                logger.warning(f"Не найдено эмодзи для участника {participant}.")
                emoji_stats[participant] = {
                    'total_emojis': 0,
                    'unique_emojis': 0,
                    'top_5_emojis': [],
                    'emoji_per_message': 0.0
                }
                continue

            emoji_counts = Counter(participant_emojis)
            total_emojis = sum(emoji_counts.values())
            total_emojis_found += total_emojis
            unique_emojis = len(emoji_counts)
            emoji_per_message = total_emojis / len(participant_texts) if len(participant_texts) > 0 else 0

            emoji_stats[participant] = {
                'total_emojis': total_emojis,
                'unique_emojis': unique_emojis,
                'top_5_emojis': emoji_counts.most_common(5),
                'emoji_per_message': emoji_per_message  # Эмодзи на сообщение
            }

        if total_emojis_found == 0:
            print("Эмодзи в чате не найдены.")
            print("-" * 20)
            return

        # Вывод статистики
        for participant, stats in emoji_stats.items():
            print(f"\n{participant}:")
            print(f"  Общее количество эмодзи: {stats['total_emojis']}")
            print(f"  Уникальные эмодзи: {stats['unique_emojis']}")
            print(f"  Эмодзи на сообщение (в среднем): {stats['emoji_per_message']:.3f}")
            top_emojis_str = ', '.join([f"{emoji} ({count})" for emoji, count in stats['top_5_emojis']]) if stats[
                'top_5_emojis'] else "N/A"
            print(f"  Топ-5 эмодзи: {top_emojis_str}")

        # График: общее количество эмодзи
        if emoji_stats:
            participants_list = list(emoji_stats.keys())
            total_counts = [stats['total_emojis'] for stats in emoji_stats.values()]
            unique_counts = [stats['unique_emojis'] for stats in emoji_stats.values()]
            per_message_counts = [stats['emoji_per_message'] for stats in emoji_stats.values()]

            fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
            fig.suptitle('Анализ использования эмодзи по участникам', fontsize=16, y=1.01)

            axes[0].bar(participants_list, total_counts, color='gold')
            axes[0].set_title('Общее количество использованных эмодзи', fontsize=14)
            axes[0].set_ylabel('Количество', fontsize=12)
            axes[0].grid(True, axis='y', linestyle='--', alpha=0.7)

            axes[1].bar(participants_list, unique_counts, color='lightsalmon')
            axes[1].set_title('Количество уникальных эмодзи', fontsize=14)
            axes[1].set_ylabel('Количество', fontsize=12)
            axes[1].grid(True, axis='y', linestyle='--', alpha=0.7)

            axes[2].bar(participants_list, per_message_counts, color='orchid')
            axes[2].set_title('Среднее количество эмодзи на сообщение', fontsize=14)
            axes[2].set_ylabel('Среднее', fontsize=12)
            axes[2].set_xlabel('Участник', fontsize=12)
            axes[2].grid(True, axis='y', linestyle='--', alpha=0.7)
            axes[2].tick_params(axis='x', rotation=45)

            plt.tight_layout(rect=[0, 0, 1, 0.98])

            # Сохранение графика
            if save_path:
                try:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    logger.info(f"График использования эмодзи сохранен в {save_path}")
                except Exception as e:
                    logger.error(f"Не удалось сохранить график эмодзи в {save_path}: {e}")
            # plt.show()
            plt.close()
        else:
            logger.warning("Нет данных для построения графика эмодзи.")

        print("-" * 20)

    except Exception as e:
        logger.error(f"Ошибка при анализе использования эмодзи: {e}", exc_info=True)
        plt.close()

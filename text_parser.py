"""Парсер текстового формата вопросов для массового импорта."""

import re
from models import Question


# Паттерны для определения категорий из заголовков
CATEGORY_PATTERNS = [
    (r"картин|визуальн", "Визуальные подсказки"),
    (r"ветхи[йм]\s*завет", "Ветхий Завет"),
    (r"новы[йм]\s*завет", "Новый Завет"),
]

# Паттерн для строки вопроса: СЛОВО: текст подсказки
# Поддерживаемые форматы:
#   СЛОВО: подсказка
#   СЛОВО: (Подсказка: текст).
#   СЛОВО: [что-то в скобках] (Подсказка: текст).
QUESTION_RE = re.compile(
    r"^([А-ЯЁA-Z]{2,})\s*:\s*(.+)$",
    re.IGNORECASE,
)


def parse_questions_text(text: str) -> list[Question]:
    """
    Парсит текстовый блок с вопросами.

    Распознаёт:
    - Заголовки категорий (строки с ключевыми словами)
    - Вопросы в формате ОТВЕТ: подсказка
    - Подсказки в скобках (Подсказка: ...) извлекаются как чистый текст

    Возвращает список Question.
    """
    lines = text.strip().splitlines()
    questions: list[Question] = []
    current_category = "Общие"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Проверяем, является ли строка заголовком категории
        cat = _detect_category(line)
        if cat:
            current_category = cat
            continue

        # Пробуем распарсить как вопрос
        m = QUESTION_RE.match(line)
        if m:
            answer = m.group(1).upper().strip()
            hint_raw = m.group(2).strip()
            hint = _clean_hint(hint_raw)

            if hint and len(answer) >= 2:
                questions.append(Question(
                    answer=answer,
                    hint=hint,
                    category=current_category,
                ))

    return questions


def _detect_category(line: str) -> str | None:
    """Определяет категорию из строки-заголовка. Возвращает None если не заголовок."""
    # Убираем эмодзи и спецсимволы для анализа
    clean = re.sub(r"[^\w\s]", "", line).strip().lower()

    if not clean:
        return None

    # Если строка содержит ":", это скорее вопрос, а не заголовок
    # Но только если перед ":" стоит одно слово из заглавных букв
    if QUESTION_RE.match(line):
        return None

    # Проверяем паттерны категорий
    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, clean):
            return category

    # Строки без ":" и без паттернов — пропускаем (описательный текст)
    return None


def _clean_hint(raw: str) -> str:
    """Очищает подсказку от лишних скобок и разметки."""
    text = raw

    # Убираем [...] (описания картинок)
    text = re.sub(r"\[.*?\]", "", text)

    # Извлекаем текст из (Подсказка: ...) если есть
    hint_match = re.search(r"\((?:Подсказка|подсказка)\s*:\s*(.+?)\)", text)
    if hint_match:
        text = hint_match.group(1)

    # Убираем (Или ...) — альтернативные варианты
    text = re.sub(r"\(Или\s+\w+.*?\)", "", text, flags=re.IGNORECASE)

    # Очистка
    text = text.strip().rstrip(".").strip()

    # Если после очистки пусто, берём оригинал
    if not text:
        text = raw.strip().rstrip(".").strip()
        text = re.sub(r"\[.*?\]", "", text).strip()

    return text

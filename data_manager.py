"""Сохранение и загрузка наборов вопросов в JSON."""

import json
import os
from models import Question


def save_questions(questions: list[Question], filepath: str) -> None:
    """Сохраняет список вопросов в JSON-файл."""
    data = []
    for q in questions:
        item = {
            "answer": q.answer,
            "hint": q.hint,
            "category": q.category,
        }
        if q.image_path:
            item["image_path"] = q.image_path
        data.append(item)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_questions(filepath: str) -> list[Question]:
    """Загружает список вопросов из JSON-файла."""
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    for item in data:
        q = Question(
            answer=item["answer"],
            hint=item["hint"],
            image_path=item.get("image_path"),
            category=item.get("category", "Общие"),
        )
        questions.append(q)

    return questions

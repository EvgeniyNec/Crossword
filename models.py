"""Модели данных для генератора кроссвордов."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Question:
    """Вопрос для кроссворда."""
    answer: str
    hint: str
    image_path: Optional[str] = None
    category: str = "Общие"

    def __post_init__(self):
        self.answer = self.answer.upper().strip()


@dataclass
class CrosswordWord:
    """Слово, размещённое в кроссворде."""
    question: Question
    row: int
    col: int
    direction: str  # 'across' или 'down'
    number: int = 0


@dataclass
class Crossword:
    """Сгенерированный кроссворд."""
    words: list[CrosswordWord] = field(default_factory=list)
    grid: list[list[str]] = field(default_factory=list)
    rows: int = 0
    cols: int = 0
    title: str = "Кроссворд"
    unplaced: list[Question] = field(default_factory=list)
    puzzle_type: str = "classic"
    extra_data: dict = field(default_factory=dict)

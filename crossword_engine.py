"""Движок генерации кроссворда — размещение слов на 2D-сетке."""

import random
from models import Question, CrosswordWord, Crossword


class CrosswordEngine:
    """Генерирует кроссворд из списка вопросов."""

    def __init__(self, padding: int = 1):
        self.padding = padding

    def generate(self, questions: list[Question], title: str = "Кроссворд",
                 orientation: str = "auto") -> Crossword:
        """Генерирует кроссворд.
        
        orientation: 'horizontal' — шире, 'vertical' — выше, 'auto' — компактный.
        """
        if not questions:
            return Crossword(title=title)

        self._orientation = orientation

        # Сортируем: длинные слова первыми
        sorted_qs = sorted(questions, key=lambda q: len(q.answer), reverse=True)

        placed: list[_PlacedWord] = []
        unplaced: list[Question] = []

        # Первое слово — направление зависит от ориентации
        first = sorted_qs[0]
        first_dir = 'down' if orientation == 'vertical' else 'across'
        placed.append(_PlacedWord(first, 0, 0, first_dir))

        # Размещаем остальные слова
        remaining = sorted_qs[1:]
        max_retries = 3
        for retry in range(max_retries):
            still_remaining = []
            for q in remaining:
                pw = self._find_best_placement(q, placed)
                if pw:
                    placed.append(pw)
                else:
                    still_remaining.append(q)
            remaining = still_remaining
            if not remaining:
                break

        unplaced = remaining

        # Нормализуем координаты (сдвигаем всё в положительную область)
        min_row = min(pw.row for pw in placed)
        min_col = min(pw.col for pw in placed)
        for pw in placed:
            pw.row -= min_row
            pw.col -= min_col

        # Определяем размер сетки
        max_row = 0
        max_col = 0
        for pw in placed:
            if pw.direction == 'across':
                end_row = pw.row
                end_col = pw.col + len(pw.question.answer) - 1
            else:
                end_row = pw.row + len(pw.question.answer) - 1
                end_col = pw.col
            max_row = max(max_row, end_row)
            max_col = max(max_col, end_col)

        rows = max_row + 1
        cols = max_col + 1

        # Строим сетку
        grid = [[''] * cols for _ in range(rows)]
        for pw in placed:
            for i, ch in enumerate(pw.question.answer):
                if pw.direction == 'across':
                    grid[pw.row][pw.col + i] = ch
                else:
                    grid[pw.row + i][pw.col] = ch

        # Нумеруем слова (по позиции: сверху вниз, слева направо)
        placed.sort(key=lambda pw: (pw.row, pw.col))
        number = 1
        assigned: dict[tuple[int, int], int] = {}
        for pw in placed:
            key = (pw.row, pw.col)
            if key in assigned:
                pw.number = assigned[key]
            else:
                pw.number = number
                assigned[key] = number
                number += 1

        # Строим результат
        words = [
            CrosswordWord(
                question=pw.question,
                row=pw.row,
                col=pw.col,
                direction=pw.direction,
                number=pw.number,
            )
            for pw in placed
        ]

        return Crossword(
            words=words,
            grid=grid,
            rows=rows,
            cols=cols,
            title=title,
            unplaced=unplaced,
        )

    def _find_best_placement(
        self, question: Question, placed: list['_PlacedWord']
    ) -> '_PlacedWord | None':
        """Ищет лучшее место для слова среди всех возможных пересечений."""
        word = question.answer
        candidates: list[_PlacedWord] = []

        for pw in placed:
            existing = pw.question.answer
            for i, ch_new in enumerate(word):
                for j, ch_ex in enumerate(existing):
                    if ch_new != ch_ex:
                        continue
                    # Пересечение: буква word[i] совпадает с existing[j]
                    if pw.direction == 'across':
                        # Существующее слово горизонтально → новое вертикально
                        new_row = pw.row - i
                        new_col = pw.col + j
                        new_dir = 'down'
                    else:
                        # Существующее слово вертикально → новое горизонтально
                        new_row = pw.row + j
                        new_col = pw.col - i
                        new_dir = 'across'

                    candidate = _PlacedWord(question, new_row, new_col, new_dir)
                    if self._is_valid_placement(candidate, placed):
                        candidates.append(candidate)

        if not candidates:
            return None

        # Выбираем наиболее компактное расположение
        best = min(candidates, key=lambda c: self._score_placement(c, placed))
        return best

    def _is_valid_placement(
        self, candidate: '_PlacedWord', placed: list['_PlacedWord']
    ) -> bool:
        """Проверяет, что размещение не конфликтует с другими словами."""
        word = candidate.question.answer
        cells: dict[tuple[int, int], str] = {}

        # Собираем все занятые клетки
        for pw in placed:
            for i, ch in enumerate(pw.question.answer):
                if pw.direction == 'across':
                    cells[(pw.row, pw.col + i)] = ch
                else:
                    cells[(pw.row + i, pw.col)] = ch

        # Собираем клетки кандидата
        new_cells: list[tuple[int, int, str]] = []
        for i, ch in enumerate(word):
            if candidate.direction == 'across':
                r, c = candidate.row, candidate.col + i
            else:
                r, c = candidate.row + i, candidate.col
            new_cells.append((r, c, ch))

        # Проверяем конфликты
        for r, c, ch in new_cells:
            if (r, c) in cells:
                if cells[(r, c)] != ch:
                    return False  # Конфликт букв

        # Проверяем соседние клетки (параллельное соседство нежелательно)
        occupied = set(cells.keys())
        new_positions = {(r, c) for r, c, _ in new_cells}
        intersections = new_positions & occupied

        for r, c, ch in new_cells:
            if (r, c) in intersections:
                continue  # Пересечение — ОК

            # Проверяем параллельное соседство
            if candidate.direction == 'across':
                # Для горизонтального слова проверяем верх и низ
                if (r - 1, c) in occupied and (r - 1, c) not in new_positions:
                    return False
                if (r + 1, c) in occupied and (r + 1, c) not in new_positions:
                    return False
            else:
                # Для вертикального — лево и право
                if (r, c - 1) in occupied and (r, c - 1) not in new_positions:
                    return False
                if (r, c + 1) in occupied and (r, c + 1) not in new_positions:
                    return False

        # Проверяем клетку до и после слова (не должно быть "слипания")
        if candidate.direction == 'across':
            before = (candidate.row, candidate.col - 1)
            after = (candidate.row, candidate.col + len(word))
        else:
            before = (candidate.row - 1, candidate.col)
            after = (candidate.row + len(word), candidate.col)

        if before in occupied or after in occupied:
            return False

        return True

    def _score_placement(
        self, candidate: '_PlacedWord', placed: list['_PlacedWord']
    ) -> float:
        """Оценка компактности: меньше — лучше."""
        all_words = placed + [candidate]
        min_r = float('inf')
        min_c = float('inf')
        max_r = float('-inf')
        max_c = float('-inf')

        for pw in all_words:
            r1, c1 = pw.row, pw.col
            if pw.direction == 'across':
                r2 = r1
                c2 = c1 + len(pw.question.answer) - 1
            else:
                r2 = r1 + len(pw.question.answer) - 1
                c2 = c1
            min_r = min(min_r, r1)
            min_c = min(min_c, c1)
            max_r = max(max_r, r2)
            max_c = max(max_c, c2)

        height = max_r - min_r + 1
        width = max_c - min_c + 1
        area = height * width

        # Штраф за нежелательное соотношение сторон
        if self._orientation == 'horizontal':
            # Предпочитаем ширину > высоты
            ratio_penalty = max(0, height - width) * 2
        elif self._orientation == 'vertical':
            # Предпочитаем высоту > ширины
            ratio_penalty = max(0, width - height) * 2
        else:
            ratio_penalty = 0

        return area + ratio_penalty


class _PlacedWord:
    """Вспомогательный класс для размещённого слова на этапе генерации."""
    __slots__ = ('question', 'row', 'col', 'direction', 'number')

    def __init__(self, question: Question, row: int, col: int, direction: str):
        self.question = question
        self.row = row
        self.col = col
        self.direction = direction
        self.number = 0

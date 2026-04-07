"""Движки генерации разных типов головоломок."""

import math
import random
from models import Question, CrosswordWord, Crossword
from crossword_engine import CrosswordEngine

CYRILLIC = "АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ"


# ---------------------------------------------------------------------------
# 1. Филворд (венгерский) — поиск слов в заполненной сетке
# ---------------------------------------------------------------------------

def generate_filword(questions: list[Question], title: str = "Филворд") -> Crossword:
    if not questions:
        return Crossword(title=title, puzzle_type="filword")

    words_data = [(q, q.answer.upper().replace("Ё", "Е")) for q in questions]
    total_chars = sum(len(w) for _, w in words_data)

    size = max(12, int(math.sqrt(total_chars) * 1.8))
    rows, cols = size, size
    grid = [['' for _ in range(cols)] for _ in range(rows)]

    # Направления: →, ↓, ↘, ↗, ←, ↑, ↖, ↙
    directions = [(0, 1), (1, 0), (1, 1), (-1, 1),
                  (0, -1), (-1, 0), (-1, -1), (1, -1)]

    placed_list: list[tuple[Question, list[tuple[int, int]]]] = []
    unplaced = []

    sorted_data = sorted(words_data, key=lambda x: len(x[1]), reverse=True)

    for q, word in sorted_data:
        ok = False
        for _ in range(500):
            dr, dc = random.choice(directions)
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            er = r + dr * (len(word) - 1)
            ec = c + dc * (len(word) - 1)
            if not (0 <= er < rows and 0 <= ec < cols):
                continue
            valid = True
            for i, ch in enumerate(word):
                gr, gc = r + dr * i, c + dc * i
                if grid[gr][gc] and grid[gr][gc] != ch:
                    valid = False
                    break
            if valid:
                cells = []
                for i, ch in enumerate(word):
                    gr, gc = r + dr * i, c + dc * i
                    grid[gr][gc] = ch
                    cells.append((gr, gc))
                placed_list.append((q, cells))
                ok = True
                break
        if not ok:
            unplaced.append(q)

    # Заполняем пустые клетки случайными буквами
    for r in range(rows):
        for c in range(cols):
            if not grid[r][c]:
                grid[r][c] = random.choice(CYRILLIC)

    cw_words = []
    word_cells = {}
    for num, (q, cells) in enumerate(placed_list, 1):
        r0, c0 = cells[0]
        cw_words.append(CrosswordWord(question=q, row=r0, col=c0,
                                      direction='across', number=num))
        word_cells[num] = cells

    return Crossword(
        words=cw_words, grid=grid, rows=rows, cols=cols,
        title=title, unplaced=unplaced,
        puzzle_type="filword",
        extra_data={"word_cells": word_cells},
    )


# ---------------------------------------------------------------------------
# 2. Крисс-кросс (американский) — тот же кроссворд, но без номеров
# ---------------------------------------------------------------------------

def generate_crisscross(questions: list[Question], title: str = "Крисс-кросс",
                        orientation: str = "auto") -> Crossword:
    engine = CrosswordEngine()
    cw = engine.generate(questions, title=title, orientation=orientation)
    cw.puzzle_type = "crisscross"
    # Группируем слова по длине для подсказки
    by_len: dict[int, list[str]] = {}
    for w in cw.words:
        L = len(w.question.answer)
        by_len.setdefault(L, []).append(w.question.answer)
    cw.extra_data = {"words_by_length": by_len}
    return cw


# ---------------------------------------------------------------------------
# 3. Кейворд — буквы заменены числами
# ---------------------------------------------------------------------------

def generate_codeword(questions: list[Question], title: str = "Кейворд",
                      orientation: str = "auto") -> Crossword:
    engine = CrosswordEngine()
    cw = engine.generate(questions, title=title, orientation=orientation)
    cw.puzzle_type = "codeword"

    unique_letters = sorted({ch for row in cw.grid for ch in row if ch})
    shuffled = list(unique_letters)
    random.shuffle(shuffled)
    letter_map = {ch: i + 1 for i, ch in enumerate(shuffled)}

    hint_count = min(3, len(shuffled))
    hint_letters = random.sample(shuffled, hint_count)

    cw.extra_data = {"letter_map": letter_map, "hint_letters": hint_letters}
    return cw


# ---------------------------------------------------------------------------
# 4. Сканворд (скандинавский) — подсказки в ячейках сетки
# ---------------------------------------------------------------------------

def generate_scanword(questions: list[Question], title: str = "Сканворд",
                      orientation: str = "auto") -> Crossword:
    engine = CrosswordEngine()
    cw = engine.generate(questions, title=title, orientation=orientation)
    cw.puzzle_type = "scanword"

    # Расширяем сетку на 1 в каждую сторону для размещения ячеек-подсказок
    old_grid = cw.grid
    new_rows = cw.rows + 2
    new_cols = cw.cols + 2
    new_grid = [['' for _ in range(new_cols)] for _ in range(new_rows)]

    for r in range(cw.rows):
        for c in range(cw.cols):
            new_grid[r + 1][c + 1] = old_grid[r][c]

    # Сдвигаем слова
    for w in cw.words:
        w.row += 1
        w.col += 1

    clue_cells = []  # (row, col, hint_text, arrow_dir)
    for w in cw.words:
        if w.direction == 'across':
            cr, cc = w.row, w.col - 1
            arrow = 'right'
        else:
            cr, cc = w.row - 1, w.col
            arrow = 'down'
        # Проверяем, что ячейка свободна
        if 0 <= cr < new_rows and 0 <= cc < new_cols:
            if not new_grid[cr][cc]:
                new_grid[cr][cc] = '#CLUE#'
                hint = w.question.hint
                if len(hint) > 30:
                    hint = hint[:28] + ".."
                clue_cells.append((cr, cc, hint, arrow))

    cw.grid = new_grid
    cw.rows = new_rows
    cw.cols = new_cols
    cw.extra_data = {"clue_cells": clue_cells}
    return cw


# ---------------------------------------------------------------------------
# 5. Циклический (круглый) — слова по кольцам и радиусам
# ---------------------------------------------------------------------------

def generate_circular(questions: list[Question], title: str = "Циклический") -> Crossword:
    if not questions:
        return Crossword(title=title, puzzle_type="circular")

    sorted_qs = sorted(questions, key=lambda q: len(q.answer), reverse=True)
    max_len = len(sorted_qs[0].answer)

    n_sectors = max(max_len + 2, 12)
    n_rings = max(max_len + 1, len(sorted_qs) // 2 + 2, 5)

    grid = [['' for _ in range(n_sectors)] for _ in range(n_rings)]
    placed: list[tuple[Question, int, int, str, list[tuple[int, int]]]] = []
    unplaced = []

    use_ring_dir = True  # Чередуем: по кольцу / радиально

    for q in sorted_qs:
        word = q.answer.upper().replace("Ё", "Е")
        ok = False

        if use_ring_dir:
            # По кольцу (clockwise)
            for _ in range(100):
                ring = random.randint(0, n_rings - 1)
                start = random.randint(0, n_sectors - 1)
                valid = True
                cells = []
                for i, ch in enumerate(word):
                    sec = (start + i) % n_sectors
                    if grid[ring][sec] and grid[ring][sec] != ch:
                        valid = False
                        break
                    cells.append((ring, sec))
                if valid:
                    for i, ch in enumerate(word):
                        sec = (start + i) % n_sectors
                        grid[ring][sec] = ch
                    placed.append((q, ring, start, 'ring', cells))
                    ok = True
                    break
        else:
            # Радиально (от внешнего к внутреннему)
            for _ in range(100):
                sec = random.randint(0, n_sectors - 1)
                start_ring = random.randint(0, n_rings - len(word))
                valid = True
                cells = []
                for i, ch in enumerate(word):
                    r = start_ring + i
                    if grid[r][sec] and grid[r][sec] != ch:
                        valid = False
                        break
                    cells.append((r, sec))
                if valid:
                    for i, ch in enumerate(word):
                        grid[start_ring + i][sec] = ch
                    placed.append((q, start_ring, sec, 'radial', cells))
                    ok = True
                    break

        if not ok:
            # Пробуем другое направление
            alt_dir = not use_ring_dir
            if alt_dir:
                for _ in range(100):
                    ring = random.randint(0, n_rings - 1)
                    start = random.randint(0, n_sectors - 1)
                    valid = True
                    cells = []
                    for i, ch in enumerate(word):
                        sec = (start + i) % n_sectors
                        if grid[ring][sec] and grid[ring][sec] != ch:
                            valid = False
                            break
                        cells.append((ring, sec))
                    if valid:
                        for i, ch in enumerate(word):
                            sec = (start + i) % n_sectors
                            grid[ring][sec] = ch
                        placed.append((q, ring, start, 'ring', cells))
                        ok = True
                        break
            else:
                for _ in range(100):
                    sec = random.randint(0, n_sectors - 1)
                    start_ring = random.randint(0, n_rings - len(word))
                    valid = True
                    cells = []
                    for i, ch in enumerate(word):
                        r = start_ring + i
                        if grid[r][sec] and grid[r][sec] != ch:
                            valid = False
                            break
                        cells.append((r, sec))
                    if valid:
                        for i, ch in enumerate(word):
                            grid[start_ring + i][sec] = ch
                        placed.append((q, start_ring, sec, 'radial', cells))
                        ok = True
                        break

            if not ok:
                unplaced.append(q)

        use_ring_dir = not use_ring_dir

    cw_words = []
    word_cells = {}
    for num, (q, r, c, direction, cells) in enumerate(placed, 1):
        d = 'across' if direction == 'ring' else 'down'
        cw_words.append(CrosswordWord(question=q, row=r, col=c,
                                      direction=d, number=num))
        word_cells[num] = cells

    return Crossword(
        words=cw_words, grid=grid, rows=n_rings, cols=n_sectors,
        title=title, unplaced=unplaced,
        puzzle_type="circular",
        extra_data={"n_rings": n_rings, "n_sectors": n_sectors,
                    "word_cells": word_cells},
    )


# ---------------------------------------------------------------------------
# 6. Сотовый — гексагональная сетка
# ---------------------------------------------------------------------------

def _hex_neighbors(r: int, c: int) -> list[tuple[int, int]]:
    """Соседи hex-клетки (offset-координаты, odd-r)."""
    if r % 2 == 0:
        return [(r-1, c-1), (r-1, c), (r, c-1), (r, c+1), (r+1, c-1), (r+1, c)]
    else:
        return [(r-1, c), (r-1, c+1), (r, c-1), (r, c+1), (r+1, c), (r+1, c+1)]


def generate_honeycomb(questions: list[Question],
                       title: str = "Сотовый") -> Crossword:
    if not questions:
        return Crossword(title=title, puzzle_type="honeycomb")

    words_data = [(q, q.answer.upper().replace("Ё", "Е")) for q in questions]
    total_chars = sum(len(w) for _, w in words_data)

    size = max(8, int(math.sqrt(total_chars) * 1.5))
    rows, cols = size, size
    grid = [['' for _ in range(cols)] for _ in range(rows)]

    placed_list: list[tuple[Question, list[tuple[int, int]]]] = []
    unplaced = []

    sorted_data = sorted(words_data, key=lambda x: len(x[1]), reverse=True)

    for q, word in sorted_data:
        ok = False
        for _ in range(300):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)

            # Строим путь через соседние hex-клетки
            path = [(r, c)]
            used = {(r, c)}
            valid = True

            if grid[r][c] and grid[r][c] != word[0]:
                continue

            for idx in range(1, len(word)):
                neighbors = _hex_neighbors(path[-1][0], path[-1][1])
                random.shuffle(neighbors)
                found = False
                for nr, nc in neighbors:
                    if (nr, nc) in used:
                        continue
                    if not (0 <= nr < rows and 0 <= nc < cols):
                        continue
                    if grid[nr][nc] and grid[nr][nc] != word[idx]:
                        continue
                    path.append((nr, nc))
                    used.add((nr, nc))
                    found = True
                    break
                if not found:
                    valid = False
                    break

            if valid and len(path) == len(word):
                for i, (pr, pc) in enumerate(path):
                    grid[pr][pc] = word[i]
                placed_list.append((q, list(path)))
                ok = True
                break

        if not ok:
            unplaced.append(q)

    # Заполняем пустые клетки
    for r in range(rows):
        for c in range(cols):
            if not grid[r][c]:
                grid[r][c] = random.choice(CYRILLIC)

    cw_words = []
    word_cells = {}
    for num, (q, cells) in enumerate(placed_list, 1):
        r0, c0 = cells[0]
        cw_words.append(CrosswordWord(question=q, row=r0, col=c0,
                                      direction='across', number=num))
        word_cells[num] = cells

    return Crossword(
        words=cw_words, grid=grid, rows=rows, cols=cols,
        title=title, unplaced=unplaced,
        puzzle_type="honeycomb",
        extra_data={"word_cells": word_cells},
    )


# ---------------------------------------------------------------------------
# 7. Японский (нонограмма) — чёрно-белая сетка из формы кроссворда
# ---------------------------------------------------------------------------

def generate_japanese(questions: list[Question], title: str = "Японский",
                      orientation: str = "auto") -> Crossword:
    """Генерирует нонограмму из формы классического кроссворда.
    Ребёнок решает нонограмму → узнаёт форму сетки → заполняет слова."""
    engine = CrosswordEngine()
    cw = engine.generate(questions, title=title, orientation=orientation)
    cw.puzzle_type = "japanese"

    # Генерируем числовые подсказки для строк и столбцов
    row_clues = []
    for r in range(cw.rows):
        runs = []
        count = 0
        for c in range(cw.cols):
            if cw.grid[r][c]:
                count += 1
            else:
                if count > 0:
                    runs.append(count)
                count = 0
        if count > 0:
            runs.append(count)
        row_clues.append(runs if runs else [0])

    col_clues = []
    for c in range(cw.cols):
        runs = []
        count = 0
        for r in range(cw.rows):
            if cw.grid[r][c]:
                count += 1
            else:
                if count > 0:
                    runs.append(count)
                count = 0
        if count > 0:
            runs.append(count)
        col_clues.append(runs if runs else [0])

    cw.extra_data = {"row_clues": row_clues, "col_clues": col_clues}
    return cw

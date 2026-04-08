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
# 4. Сканворд (скандинавский) — подсказки внутри ячеек сетки
# ---------------------------------------------------------------------------

def _scanword_find_clue_cell(w, letter_cells, clue_occupied, new_rows, new_cols, new_grid):
    """Ищет свободную ячейку (или блок NxM) для подсказки рядом с началом слова.
    
    Возвращает (row, col, arrow_direction, span_r, span_c, target_r, target_c) или None.
    
    arrow указывает направление от блока подсказки к первой букве:
      - 'right'      → блок слева, стрелка вправо
      - 'down'       ↓ блок сверху, стрелка вниз
      - 'down_right' ↓→ блок сверху-слева, стрелка ломаная вниз-вправо
      - 'right_down' →↓ блок сверху-слева, стрелка ломаная вправо-вниз
    target_r, target_c — координаты первой буквы слова (куда указывает стрелка).
    """
    # Только 2×2 блоки для подсказок
    shapes = [(2, 2)]
    occupied_set = set(letter_cells) | set(clue_occupied.keys())

    def _can_span(start_r, start_c, span_r, span_c):
        for dr in range(span_r):
            for dc in range(span_c):
                r, c = start_r + dr, start_c + dc
                if r < 0 or r >= new_rows or c < 0 or c >= new_cols:
                    return False
                if (r, c) in occupied_set:
                    return False
        return True

    def _calc_arrow(cr, cc, sr, sc):
        """Определяет тип стрелки по положению блока подсказки
        относительно первой буквы слова И направлению слова.
        
        Стрелка должна показывать путь от подсказки к первой букве
        И направление, в котором читается слово.
        """
        block_bottom = cr + sr - 1
        block_right = cc + sc - 1
        tr, tc = w.row, w.col

        # Первая буква справа от блока (та же строка или блок содержит строку)
        directly_right = (block_right == tc - 1) and (cr <= tr <= block_bottom)
        # Первая буква снизу от блока (тот же столбец или блок содержит столбец)
        directly_below = (block_bottom == tr - 1) and (cc <= tc <= block_right)

        if directly_right and directly_below:
            # Угловой случай — выбираем по направлению слова
            return 'right' if w.direction == 'across' else 'down'
        if directly_right:
            # Блок слева от первой буквы
            if w.direction == 'across':
                return 'right'       # слово идёт вправо — простая стрелка
            else:
                return 'right_down'  # слово идёт вниз — ломаная →↓
        if directly_below:
            # Блок сверху от первой буквы
            if w.direction == 'down':
                return 'down'        # слово идёт вниз — простая стрелка
            else:
                return 'down_right'  # слово идёт вправо — ломаная ↓→

        # Первая буква ниже И правее блока — ломаная стрелка
        if tr > block_bottom and tc > block_right:
            return 'down_right' if w.direction == 'across' else 'right_down'
        # Первая буква правее (но не на той же строке)
        if tc > block_right:
            return 'down_right' if w.direction == 'across' else 'right_down'
        # Первая буква ниже (но не на том же столбце)
        if tr > block_bottom:
            return 'down_right' if w.direction == 'across' else 'right_down'

        # Фоллбэк
        return 'right' if w.direction == 'across' else 'down'

    tr, tc = w.row, w.col

    # Генерируем кандидатов: для каждого размера блока — позиции,
    # которые обеспечивают правый или нижний край блока рядом с (tr, tc).
    candidates = []
    for sr, sc in shapes:
        # --- Прямо слева (стрелка right) ---
        for row_off in range(sr):
            cand_r = tr - row_off
            cand_c = tc - sc
            candidates.append((cand_r, cand_c, sr, sc))

        # --- Прямо сверху (стрелка down) ---
        for col_off in range(sc):
            cand_r = tr - sr
            cand_c = tc - col_off
            candidates.append((cand_r, cand_c, sr, sc))

        # --- По диагонали сверху-слева (ломаная стрелка) ---
        cand_r = tr - sr
        cand_c = tc - sc
        candidates.append((cand_r, cand_c, sr, sc))

        # --- Дополнительные позиции: снизу-слева, сверху-справа ---
        if sr > 1 or sc > 1:
            # Снизу-слева
            for row_off in range(sr):
                candidates.append((tr + 1 - row_off, tc - sc, sr, sc))
            # Сверху-справа
            for col_off in range(sc):
                candidates.append((tr - sr, tc + 1 - col_off, sr, sc))

    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    for cr, cc, sr, sc in unique:
        if _can_span(cr, cc, sr, sc):
            arrow = _calc_arrow(cr, cc, sr, sc)
            return cr, cc, arrow, sr, sc, tr, tc

    # Фоллбэк: пробуем все формы в расширенном наборе позиций
    fb_offsets = [
        (0, -1), (-1, 0), (-1, -1), (1, -1), (-1, 1),
        (0, -2), (-2, 0), (1, 0), (0, 1),
    ]
    for sr, sc in shapes:
        for dr, dc in fb_offsets:
            cr, cc = tr + dr, tc + dc
            if _can_span(cr, cc, sr, sc):
                arrow = _calc_arrow(cr, cc, sr, sc)
                return cr, cc, arrow, sr, sc, tr, tc

    return None


def generate_scanword(questions: list[Question], title: str = "Сканворд",
                      orientation: str = "auto") -> Crossword:
    """Генерирует сканворд — кроссворд с подсказками внутри ячеек сетки.
    
    Все пустые ячейки заполняются тёмными блоками (#BLOCK#).
    Стрелки рисуются ВНУТРИ ячейки-подсказки.
    """
    if not questions:
        return Crossword(title=title, puzzle_type="scanword")

    engine = CrosswordEngine(padding=1)
    cw = engine.generate(questions, title=title, orientation=orientation)
    cw.puzzle_type = "scanword"

    if not cw.words:
        return cw

    # --- Шаг 1: Расширяем сетку на 4 клетки в каждую сторону (для 2×2 блоков) ---
    pad = 4
    old_grid = cw.grid
    new_rows = cw.rows + pad * 2
    new_cols = cw.cols + pad * 2
    new_grid = [['' for _ in range(new_cols)] for _ in range(new_rows)]

    for r in range(cw.rows):
        for c in range(cw.cols):
            new_grid[r + pad][c + pad] = old_grid[r][c]

    for w in cw.words:
        w.row += pad
        w.col += pad

    # --- Шаг 2: Собираем множество ячеек с буквами ---
    letter_cells = set()
    for r in range(new_rows):
        for c in range(new_cols):
            if new_grid[r][c] and new_grid[r][c] != '#CLUE#':
                letter_cells.add((r, c))

    # --- Шаг 3: Размещаем ячейки-подсказки ---
    clue_cells = []
    clue_occupied = {}

    for w in cw.words:
        result = _scanword_find_clue_cell(
            w, letter_cells, clue_occupied, new_rows, new_cols, new_grid
        )
        if result is None:
            continue

        cr, cc, arrow, span_r, span_c, target_r, target_c = result
        hint = w.question.hint

        for dr in range(span_r):
            for dc in range(span_c):
                new_grid[cr + dr][cc + dc] = '#CLUE#'
                clue_occupied[(cr + dr, cc + dc)] = True

        clue_cells.append((cr, cc, hint, arrow, span_r, span_c, target_r, target_c))

    # --- Шаг 4: Обрезаем пустые строки/столбцы по краям ---
    used_rows = set()
    used_cols = set()
    for r in range(new_rows):
        for c in range(new_cols):
            if new_grid[r][c]:
                used_rows.add(r)
                used_cols.add(c)

    if not used_rows or not used_cols:
        cw.grid = new_grid
        cw.rows = new_rows
        cw.cols = new_cols
        cw.extra_data = {"clue_cells": clue_cells}
        return cw

    min_r, max_r = min(used_rows), max(used_rows)
    min_c, max_c = min(used_cols), max(used_cols)

    trim_grid = []
    for r in range(min_r, max_r + 1):
        row = []
        for c in range(min_c, max_c + 1):
            row.append(new_grid[r][c])
        trim_grid.append(row)

    for w in cw.words:
        w.row -= min_r
        w.col -= min_c

    trimmed_clues = []
    for cr, cc, hint, arrow, sr, sc, t_r, t_c in clue_cells:
        trimmed_clues.append((cr - min_r, cc - min_c, hint, arrow, sr, sc, t_r - min_r, t_c - min_c))

    final_rows = max_r - min_r + 1
    final_cols = max_c - min_c + 1

    # --- Шаг 5: Заполняем ВСЕ пустые ячейки тёмными блоками ---
    for r in range(final_rows):
        for c in range(final_cols):
            if not trim_grid[r][c]:
                trim_grid[r][c] = '#BLOCK#'

    cw.grid = trim_grid
    cw.rows = final_rows
    cw.cols = final_cols
    cw.extra_data = {"clue_cells": trimmed_clues}
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

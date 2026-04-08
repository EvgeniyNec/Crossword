"""Экспорт кроссворда в SVG (векторный формат — открывается в CorelDRAW, Illustrator, Inkscape)."""

import html
from models import Crossword


# Размеры (в пикселях, но SVG масштабируется)
CELL_SIZE = 40
MARGIN = 30
FONT_FAMILY = "Arial, sans-serif"

# Цвета
COLOR_CELL_BG = "#ffffff"
COLOR_CELL_BORDER = "#333333"
COLOR_EMPTY = "#e0e0e0"
COLOR_NUMBER = "#1a73e8"
COLOR_LETTER = "#333333"
COLOR_TITLE = "#333333"
COLOR_CATEGORY = "#1a73e8"


def _svg_scanword_arrow(x, y, bw, bh, arrow, tx, ty, cell_sz=40):
    """Генерирует SVG-разметку стрелки от края блока подсказки к целевой ячейке.
    
    tx, ty — левый верхний угол целевой ячейки.
    cell_sz — размер ячейки для вычисления центра и наконечника.
    """
    ac = "#f2cc8f"
    aw = cell_sz * 0.15   # размер наконечника
    sw = max(1, cell_sz * 0.04)
    # Края целевой ячейки
    t_left = tx
    t_top = ty
    t_cx = tx + cell_sz / 2
    t_cy = ty + cell_sz / 2

    if arrow == 'right':
        # ──▶  остриё на левом краю ячейки
        sx = x + bw
        sy = y + bh / 2
        return (f'  <line x1="{sx}" y1="{sy}" x2="{t_left}" y2="{t_cy}" '
                f'stroke="{ac}" stroke-width="{sw}"/>\n'
                f'  <polygon points="{t_left},{t_cy - aw} {t_left + aw},{t_cy} {t_left},{t_cy + aw}" '
                f'fill="{ac}"/>\n')
    elif arrow == 'down':
        # │▼  остриё на верхнем краю ячейки
        sx = x + bw / 2
        sy = y + bh
        return (f'  <line x1="{sx}" y1="{sy}" x2="{t_cx}" y2="{t_top}" '
                f'stroke="{ac}" stroke-width="{sw}"/>\n'
                f'  <polygon points="{t_cx - aw},{t_top} {t_cx},{t_top + aw} {t_cx + aw},{t_top}" '
                f'fill="{ac}"/>\n')
    elif arrow == 'down_right':
        # ↓→▶  вниз, потом вправо, остриё на левом краю
        sx = x + bw / 2
        sy = y + bh
        # Изгиб ЛЕВЕЕ t_left, чтобы последний отрезок шёл ВПРАВО
        bend_x = min(sx, t_left - aw * 2)
        bend_y = t_cy
        return (f'  <polyline points="{sx},{sy} {bend_x},{bend_y} {t_left},{t_cy}" '
                f'stroke="{ac}" stroke-width="{sw}" fill="none"/>\n'
                f'  <polygon points="{t_left},{t_cy - aw} {t_left + aw},{t_cy} {t_left},{t_cy + aw}" '
                f'fill="{ac}"/>\n')
    elif arrow == 'right_down':
        # →↓▼  вправо, потом вниз, остриё на верхнем краю
        sx = x + bw
        sy = y + bh / 2
        bend_x = t_cx
        # Изгиб ВЫШЕ t_top, чтобы последний отрезок шёл ВНИЗ
        bend_y = min(sy, t_top - aw * 2)
        return (f'  <polyline points="{sx},{sy} {bend_x},{bend_y} {t_cx},{t_top}" '
                f'stroke="{ac}" stroke-width="{sw}" fill="none"/>\n'
                f'  <polygon points="{t_cx - aw},{t_top} {t_cx},{t_top + aw} {t_cx + aw},{t_top}" '
                f'fill="{ac}"/>\n')
    return ''


def export_svg(crossword: Crossword, filepath: str, show_answers: bool = False,
               cell_size: int = CELL_SIZE) -> None:
    """Экспортирует сетку кроссворда в SVG-файл."""
    cw = crossword
    grid_w = cw.cols * cell_size
    grid_h = cw.rows * cell_size
    CELL_SIZE = cell_size

    # Общий размер: сетка + отступы + место под заголовок
    title_height = 60
    svg_w = grid_w + 2 * MARGIN
    svg_h = grid_h + 2 * MARGIN + title_height

    parts: list[str] = []

    # SVG заголовок
    parts.append(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}">\n'
    )

    # Фон
    parts.append(f'  <rect width="{svg_w}" height="{svg_h}" fill="#fafafa"/>\n')

    # Заголовок
    title = html.escape(cw.title)
    if show_answers:
        title += " (ОТВЕТЫ)"
    parts.append(
        f'  <text x="{svg_w / 2}" y="{MARGIN + 20}" '
        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
        f'font-size="18" font-weight="bold" fill="{COLOR_TITLE}">'
        f'{title}</text>\n'
    )
    parts.append(
        f'  <text x="{svg_w / 2}" y="{MARGIN + 40}" '
        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
        f'font-size="10" fill="#666666">'
        f'Кроссворд для воскресной школы</text>\n'
    )

    # Номера по позициям
    numbers: dict[tuple[int, int], int] = {}
    for w in cw.words:
        key = (w.row, w.col)
        if key not in numbers:
            numbers[key] = w.number

    # Данные сканворда
    clue_cells = {}
    clue_skip = set()
    if cw.puzzle_type == "scanword":
        for item in cw.extra_data.get("clue_cells", []):
            cr, cc, hint_text, arrow = item[0], item[1], item[2], item[3]
            sr = item[4] if len(item) > 4 else 1
            sc = item[5] if len(item) > 5 else 1
            t_r = item[6] if len(item) > 6 else None
            t_c = item[7] if len(item) > 7 else None
            clue_cells[(cr, cc)] = (hint_text, arrow, sr, sc, t_r, t_c)
            for dr in range(sr):
                for dc in range(sc):
                    if dr != 0 or dc != 0:
                        clue_skip.add((cr + dr, cc + dc))

    ox = MARGIN
    oy = MARGIN + title_height

    # Рисуем ячейки
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = ox + col * CELL_SIZE
            y = oy + row * CELL_SIZE
            ch = cw.grid[row][col]

            # Сканворд: пропуск span-продолжений
            if cw.puzzle_type == "scanword" and (row, col) in clue_skip:
                continue

            # Сканворд: ячейка-подсказка (с span)
            if cw.puzzle_type == "scanword" and (row, col) in clue_cells:
                hint_text, arrow, sr, sc, t_r, t_c = clue_cells[(row, col)]
                bw = sc * CELL_SIZE
                bh = sr * CELL_SIZE
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{bw}" height="{bh}" '
                    f'fill="#3d5a80" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )
                disp = html.escape(hint_text)
                fs = max(4, CELL_SIZE * 0.14)
                parts.append(
                    f'  <foreignObject x="{x + 1}" y="{y + 1}" width="{bw - 2}" height="{bh - 8}">'
                    f'<div xmlns="http://www.w3.org/1999/xhtml" style="'
                    f'font-family:{FONT_FAMILY};font-size:{fs:.1f}px;color:white;'
                    f'text-align:center;overflow:hidden;word-wrap:break-word;'
                    f'display:flex;align-items:center;justify-content:center;height:100%">'
                    f'{disp}</div></foreignObject>\n'
                )
                # Стрелка от блока к целевой ячейке
                if t_r is not None and t_c is not None:
                    target_x = ox + t_c * CELL_SIZE
                    target_y = oy + t_r * CELL_SIZE
                    parts.append(_svg_scanword_arrow(x, y, bw, bh, arrow, target_x, target_y, CELL_SIZE))
                continue

            # Тёмные блоки (сканворд)
            if ch == '#BLOCK#' and cw.puzzle_type == "scanword":
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="#3d5a80" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )
                continue

            # Пустые ячейки — не рисуем
            if not ch or ch in ('#CLUE#', '#BLOCK#'):
                continue

            # Белая ячейка с рамкой
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="{COLOR_CELL_BG}" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )

                # Номер (не для сканворда)
                if cw.puzzle_type != "scanword" and (row, col) in numbers:
                    num = numbers[(row, col)]
                    num_fs = max(5, CELL_SIZE * 0.25)
                    parts.append(
                        f'  <text x="{x + 3}" y="{y + num_fs * 1.2}" '
                        f'font-family="{FONT_FAMILY}" font-size="{num_fs:.1f}" '
                        f'font-weight="bold" fill="{COLOR_NUMBER}">'
                        f'{num}</text>\n'
                    )

                # Буква
                if show_answers:
                    letter_fs = max(8, CELL_SIZE * 0.45)
                    esc_ch = html.escape(ch)
                    parts.append(
                        f'  <text x="{x + CELL_SIZE / 2}" y="{y + CELL_SIZE * 0.7}" '
                        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
                        f'font-size="{letter_fs:.1f}" font-weight="bold" fill="{COLOR_LETTER}">'
                        f'{esc_ch}</text>\n'
                    )

    parts.append('</svg>\n')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))


def export_svg_with_clues(crossword: Crossword, filepath: str, show_answers: bool = False,
                          cell_size: int = CELL_SIZE) -> None:
    """Экспортирует кроссворд + вопросы в один SVG-файл."""
    cw = crossword
    grid_w = cw.cols * cell_size
    grid_h = cw.rows * cell_size
    CELL_SIZE = cell_size

    # Готовим вопросы
    across = sorted([w for w in cw.words if w.direction == 'across'], key=lambda w: w.number)
    down = sorted([w for w in cw.words if w.direction == 'down'], key=lambda w: w.number)

    clue_line_h = 20
    clues_height = (
        40  # заголовок "Вопросы"
        + (30 if across else 0) + len(across) * clue_line_h
        + 20  # отступ
        + (30 if down else 0) + len(down) * clue_line_h
    )

    title_height = 60
    svg_w = max(grid_w + 2 * MARGIN, 600)
    svg_h = grid_h + 2 * MARGIN + title_height + 40 + clues_height

    parts: list[str] = []

    parts.append(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}">\n'
    )
    parts.append(f'  <rect width="{svg_w}" height="{svg_h}" fill="#fafafa"/>\n')

    # Заголовок
    title = html.escape(cw.title)
    if show_answers:
        title += " (ОТВЕТЫ)"
    parts.append(
        f'  <text x="{svg_w / 2}" y="{MARGIN + 20}" '
        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
        f'font-size="18" font-weight="bold" fill="{COLOR_TITLE}">'
        f'{title}</text>\n'
    )

    # Номера по позициям
    numbers: dict[tuple[int, int], int] = {}
    for w in cw.words:
        key = (w.row, w.col)
        if key not in numbers:
            numbers[key] = w.number

    # Данные сканворда
    clue_cells2 = {}
    clue_skip2 = set()
    if cw.puzzle_type == "scanword":
        for item in cw.extra_data.get("clue_cells", []):
            cr, cc, hint_text, arrow = item[0], item[1], item[2], item[3]
            sr = item[4] if len(item) > 4 else 1
            sc = item[5] if len(item) > 5 else 1
            t_r = item[6] if len(item) > 6 else None
            t_c = item[7] if len(item) > 7 else None
            clue_cells2[(cr, cc)] = (hint_text, arrow, sr, sc, t_r, t_c)
            for dr in range(sr):
                for dc in range(sc):
                    if dr != 0 or dc != 0:
                        clue_skip2.add((cr + dr, cc + dc))

    ox = (svg_w - grid_w) / 2
    oy = MARGIN + title_height

    # Сетка
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = ox + col * CELL_SIZE
            y = oy + row * CELL_SIZE
            ch = cw.grid[row][col]

            if cw.puzzle_type == "scanword" and (row, col) in clue_skip2:
                continue

            # Сканворд: подсказка (с span)
            if cw.puzzle_type == "scanword" and (row, col) in clue_cells2:
                hint_text, arrow, sr, sc, t_r, t_c = clue_cells2[(row, col)]
                bw = sc * CELL_SIZE
                bh = sr * CELL_SIZE
                disp = html.escape(hint_text)
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{bw}" height="{bh}" '
                    f'fill="#3d5a80" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )
                fs = max(4, CELL_SIZE * 0.14)
                parts.append(
                    f'  <foreignObject x="{x + 1}" y="{y + 1}" width="{bw - 2}" height="{bh - 8}">'
                    f'<div xmlns="http://www.w3.org/1999/xhtml" style="'
                    f'font-family:{FONT_FAMILY};font-size:{fs:.1f}px;color:white;'
                    f'text-align:center;overflow:hidden;word-wrap:break-word;'
                    f'display:flex;align-items:center;justify-content:center;height:100%">'
                    f'{disp}</div></foreignObject>\n'
                )
                if t_r is not None and t_c is not None:
                    target_x = ox + t_c * CELL_SIZE
                    target_y = oy + t_r * CELL_SIZE
                    parts.append(_svg_scanword_arrow(x, y, bw, bh, arrow, target_x, target_y, CELL_SIZE))
                continue

            # Тёмные блоки (сканворд)
            if ch == '#BLOCK#' and cw.puzzle_type == "scanword":
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="#3d5a80" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )
                continue

            # Пустые — не рисуем
            if not ch or ch in ('#CLUE#', '#BLOCK#'):
                continue

            if ch and ch not in ('#CLUE#', '#BLOCK#'):
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="{COLOR_CELL_BG}" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )
                if cw.puzzle_type != "scanword" and (row, col) in numbers:
                    num_fs = max(5, CELL_SIZE * 0.25)
                    parts.append(
                        f'  <text x="{x + 3}" y="{y + num_fs * 1.2}" '
                        f'font-family="{FONT_FAMILY}" font-size="{num_fs:.1f}" '
                        f'font-weight="bold" fill="{COLOR_NUMBER}">'
                        f'{numbers[(row, col)]}</text>\n'
                    )
                if show_answers:
                    letter_fs = max(8, CELL_SIZE * 0.45)
                    esc_ch = html.escape(ch)
                    parts.append(
                        f'  <text x="{x + CELL_SIZE / 2}" y="{y + CELL_SIZE * 0.7}" '
                        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
                        f'font-size="{letter_fs:.1f}" font-weight="bold" fill="{COLOR_LETTER}">'
                        f'{esc_ch}</text>\n'
                    )

    # Вопросы
    clue_y = oy + grid_h + 40
    clue_x = MARGIN + 10

    parts.append(
        f'  <text x="{svg_w / 2}" y="{clue_y}" '
        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
        f'font-size="14" font-weight="bold" fill="{COLOR_TITLE}">'
        f'Вопросы к кроссворду</text>\n'
    )
    clue_y += 25

    if across:
        parts.append(
            f'  <text x="{clue_x}" y="{clue_y}" '
            f'font-family="{FONT_FAMILY}" font-size="12" '
            f'font-weight="bold" fill="{COLOR_CATEGORY}">'
            f'По горизонтали →</text>\n'
        )
        clue_y += 22
        for w in across:
            hint_text = html.escape(w.question.hint[:80])
            parts.append(
                f'  <text x="{clue_x + 10}" y="{clue_y}" '
                f'font-family="{FONT_FAMILY}" font-size="10">'
                f'<tspan font-weight="bold" fill="{COLOR_NUMBER}">{w.number}.</tspan> '
                f'{hint_text}</text>\n'
            )
            clue_y += clue_line_h

    clue_y += 15

    if down:
        parts.append(
            f'  <text x="{clue_x}" y="{clue_y}" '
            f'font-family="{FONT_FAMILY}" font-size="12" '
            f'font-weight="bold" fill="{COLOR_CATEGORY}">'
            f'По вертикали ↓</text>\n'
        )
        clue_y += 22
        for w in down:
            hint_text = html.escape(w.question.hint[:80])
            parts.append(
                f'  <text x="{clue_x + 10}" y="{clue_y}" '
                f'font-family="{FONT_FAMILY}" font-size="10">'
                f'<tspan font-weight="bold" fill="{COLOR_NUMBER}">{w.number}.</tspan> '
                f'{hint_text}</text>\n'
            )
            clue_y += clue_line_h

    parts.append('</svg>\n')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))

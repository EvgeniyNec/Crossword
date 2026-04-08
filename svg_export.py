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


def _svg_scanword_arrow(x, y, bw, bh, arrow, tx, ty, cell_sz=40, off_x=0, off_y=0):
    """Генерирует SVG стрелку от края блока подсказки к целевой ячейке.

    tx, ty — левый верхний угол целевой ячейки.
    off_x, off_y — смещение наконечника для избежания наложений.
    Изгиб ломаных стрелок — ВНУТРИ целевой ячейки.
    """
    ac = "#f2cc8f"
    aw = cell_sz * 0.08
    sw = max(1, cell_sz * 0.04)
    t_cx = tx + cell_sz / 2 + off_x
    t_cy = ty + cell_sz / 2 + off_y

    if arrow == 'right':
        sx = x + bw
        sy = y + bh / 2
        return (f'  <line x1="{sx}" y1="{sy}" x2="{t_cx - aw}" y2="{t_cy}" '
                f'stroke="{ac}" stroke-width="{sw}"/>\n'
                f'  <polygon points="{t_cx - aw},{t_cy - aw} {t_cx},{t_cy} {t_cx - aw},{t_cy + aw}" '
                f'fill="{ac}"/>\n')
    elif arrow == 'down':
        sx = x + bw / 2
        sy = y + bh
        return (f'  <line x1="{sx}" y1="{sy}" x2="{t_cx}" y2="{t_cy - aw}" '
                f'stroke="{ac}" stroke-width="{sw}"/>\n'
                f'  <polygon points="{t_cx - aw},{t_cy - aw} {t_cx},{t_cy} {t_cx + aw},{t_cy - aw}" '
                f'fill="{ac}"/>\n')
    elif arrow == 'down_right':
        sx = x + bw - bw * 0.3
        sy = y + bh
        bend_x = tx + cell_sz * 0.2
        bend_y = t_cy
        return (f'  <polyline points="{sx},{sy} {bend_x},{bend_y} {t_cx - aw},{t_cy}" '
                f'stroke="{ac}" stroke-width="{sw}" fill="none"/>\n'
                f'  <polygon points="{t_cx - aw},{t_cy - aw} {t_cx},{t_cy} {t_cx - aw},{t_cy + aw}" '
                f'fill="{ac}"/>\n')
    elif arrow == 'right_down':
        sx = x + bw
        sy = y + bh - bh * 0.3
        bend_x = t_cx
        bend_y = ty + cell_sz * 0.2
        return (f'  <polyline points="{sx},{sy} {bend_x},{bend_y} {t_cx},{t_cy - aw}" '
                f'stroke="{ac}" stroke-width="{sw}" fill="none"/>\n'
                f'  <polygon points="{t_cx - aw},{t_cy - aw} {t_cx},{t_cy} {t_cx + aw},{t_cy - aw}" '
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

    # Отложенные стрелки сканворда
    _svg_arrows = []

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
                # Авто-масштаб: оценка размера шрифта чтобы текст влез полностью
                pad_svg = 3
                aw_svg = bw - pad_svg * 2
                ah_svg = bh - pad_svg * 2
                # Оцениваем: средняя ширина символа ~0.55 * fs, высота строки ~1.3 * fs
                # Подбираем fs от большого к малому
                best_svg_fs = 3
                for tfs in range(max(3, int(CELL_SIZE * 0.30)), 2, -1):
                    chars_per_line = max(1, int(aw_svg / (tfs * 0.55)))
                    # Простая оценка количества строк
                    words_sv = hint_text.split()
                    nlines = 1
                    cur_len = 0
                    for ww in words_sv:
                        if cur_len == 0:
                            cur_len = len(ww)
                        elif cur_len + 1 + len(ww) <= chars_per_line:
                            cur_len += 1 + len(ww)
                        else:
                            nlines += 1
                            cur_len = len(ww)
                    max_lines_svg = max(1, int(ah_svg / (tfs * 1.3)))
                    if nlines <= max_lines_svg:
                        best_svg_fs = tfs
                        break
                parts.append(
                    f'  <foreignObject x="{x + pad_svg}" y="{y + pad_svg}" '
                    f'width="{aw_svg}" height="{ah_svg}">'
                    f'<div xmlns="http://www.w3.org/1999/xhtml" style="'
                    f'font-family:{FONT_FAMILY};font-size:{best_svg_fs}px;color:white;'
                    f'text-align:center;overflow:hidden;word-wrap:break-word;'
                    f'display:flex;align-items:center;justify-content:center;height:100%">'
                    f'{disp}</div></foreignObject>\n'
                )
                # Стрелка от блока к целевой ячейке (отложенная)
                if t_r is not None and t_c is not None:
                    _svg_arrows.append((x, y, bw, bh, arrow, t_r, t_c))
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

    # Сканворд: рисуем стрелки с учётом наложений
    if cw.puzzle_type == "scanword" and _svg_arrows:
        from collections import defaultdict
        _tg = defaultdict(list)
        for _i, _a in enumerate(_svg_arrows):
            _tg[(_a[5], _a[6])].append(_i)
        _aoff = {}
        for _, _idxs in _tg.items():
            _n = len(_idxs)
            for _j, _idx in enumerate(_idxs):
                if _n <= 1:
                    _aoff[_idx] = (0, 0)
                else:
                    _arr = _svg_arrows[_idx][4]
                    _pos = _j - (_n - 1) / 2
                    _sp = CELL_SIZE * 0.15
                    if _arr in ('right', 'right_down'):
                        _aoff[_idx] = (0, _pos * _sp)
                    else:
                        _aoff[_idx] = (_pos * _sp, 0)
        for _i, (ax, ay, abw, abh, arrow, at_r, at_c) in enumerate(_svg_arrows):
            target_x = ox + at_c * CELL_SIZE
            target_y = oy + at_r * CELL_SIZE
            _ox2, _oy2 = _aoff.get(_i, (0, 0))
            parts.append(_svg_scanword_arrow(ax, ay, abw, abh, arrow,
                                              target_x, target_y, CELL_SIZE, _ox2, _oy2))

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

    # Отложенные стрелки сканворда
    _svg_arrows2 = []

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
                pad2 = 3
                aw2 = bw - pad2 * 2
                ah2 = bh - pad2 * 2
                best_fs2 = 3
                for tfs2 in range(max(3, int(CELL_SIZE * 0.30)), 2, -1):
                    cpl2 = max(1, int(aw2 / (tfs2 * 0.55)))
                    ws2 = hint_text.split()
                    nl2 = 1
                    cl2 = 0
                    for ww2 in ws2:
                        if cl2 == 0:
                            cl2 = len(ww2)
                        elif cl2 + 1 + len(ww2) <= cpl2:
                            cl2 += 1 + len(ww2)
                        else:
                            nl2 += 1
                            cl2 = len(ww2)
                    ml2 = max(1, int(ah2 / (tfs2 * 1.3)))
                    if nl2 <= ml2:
                        best_fs2 = tfs2
                        break
                parts.append(
                    f'  <foreignObject x="{x + pad2}" y="{y + pad2}" width="{aw2}" height="{ah2}">'
                    f'<div xmlns="http://www.w3.org/1999/xhtml" style="'
                    f'font-family:{FONT_FAMILY};font-size:{best_fs2}px;color:white;'
                    f'text-align:center;overflow:hidden;word-wrap:break-word;'
                    f'display:flex;align-items:center;justify-content:center;height:100%">'
                    f'{disp}</div></foreignObject>\n'
                )
                if t_r is not None and t_c is not None:
                    _svg_arrows2.append((x, y, bw, bh, arrow, t_r, t_c))
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

    # Сканворд: рисуем стрелки с учётом наложений
    if cw.puzzle_type == "scanword" and _svg_arrows2:
        from collections import defaultdict
        _tg2 = defaultdict(list)
        for _i, _a in enumerate(_svg_arrows2):
            _tg2[(_a[5], _a[6])].append(_i)
        _aoff2 = {}
        for _, _idxs in _tg2.items():
            _n = len(_idxs)
            for _j, _idx in enumerate(_idxs):
                if _n <= 1:
                    _aoff2[_idx] = (0, 0)
                else:
                    _arr = _svg_arrows2[_idx][4]
                    _pos = _j - (_n - 1) / 2
                    _sp = CELL_SIZE * 0.15
                    if _arr in ('right', 'right_down'):
                        _aoff2[_idx] = (0, _pos * _sp)
                    else:
                        _aoff2[_idx] = (_pos * _sp, 0)
        for _i, (ax, ay, abw, abh, arrow, at_r, at_c) in enumerate(_svg_arrows2):
            target_x = ox + at_c * CELL_SIZE
            target_y = oy + at_r * CELL_SIZE
            _ox3, _oy3 = _aoff2.get(_i, (0, 0))
            parts.append(_svg_scanword_arrow(ax, ay, abw, abh, arrow,
                                              target_x, target_y, CELL_SIZE, _ox3, _oy3))

    parts.append('</svg>\n')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))

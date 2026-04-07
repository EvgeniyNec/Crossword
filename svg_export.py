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


def export_svg(crossword: Crossword, filepath: str, show_answers: bool = False) -> None:
    """Экспортирует сетку кроссворда в SVG-файл."""
    cw = crossword
    grid_w = cw.cols * CELL_SIZE
    grid_h = cw.rows * CELL_SIZE

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

    ox = MARGIN
    oy = MARGIN + title_height

    # Рисуем ячейки
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = ox + col * CELL_SIZE
            y = oy + row * CELL_SIZE
            ch = cw.grid[row][col]

            if ch:
                # Белая ячейка с рамкой
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="{COLOR_CELL_BG}" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )

                # Номер
                if (row, col) in numbers:
                    num = numbers[(row, col)]
                    parts.append(
                        f'  <text x="{x + 3}" y="{y + 10}" '
                        f'font-family="{FONT_FAMILY}" font-size="8" '
                        f'font-weight="bold" fill="{COLOR_NUMBER}">'
                        f'{num}</text>\n'
                    )

                # Буква
                if show_answers:
                    esc_ch = html.escape(ch)
                    parts.append(
                        f'  <text x="{x + CELL_SIZE / 2}" y="{y + CELL_SIZE * 0.7}" '
                        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
                        f'font-size="16" font-weight="bold" fill="{COLOR_LETTER}">'
                        f'{esc_ch}</text>\n'
                    )

    parts.append('</svg>\n')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))


def export_svg_with_clues(crossword: Crossword, filepath: str, show_answers: bool = False) -> None:
    """Экспортирует кроссворд + вопросы в один SVG-файл."""
    cw = crossword
    grid_w = cw.cols * CELL_SIZE
    grid_h = cw.rows * CELL_SIZE

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

    ox = (svg_w - grid_w) / 2
    oy = MARGIN + title_height

    # Сетка
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = ox + col * CELL_SIZE
            y = oy + row * CELL_SIZE
            ch = cw.grid[row][col]

            if ch:
                parts.append(
                    f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="{COLOR_CELL_BG}" stroke="{COLOR_CELL_BORDER}" stroke-width="1"/>\n'
                )
                if (row, col) in numbers:
                    parts.append(
                        f'  <text x="{x + 3}" y="{y + 10}" '
                        f'font-family="{FONT_FAMILY}" font-size="8" '
                        f'font-weight="bold" fill="{COLOR_NUMBER}">'
                        f'{numbers[(row, col)]}</text>\n'
                    )
                if show_answers:
                    esc_ch = html.escape(ch)
                    parts.append(
                        f'  <text x="{x + CELL_SIZE / 2}" y="{y + CELL_SIZE * 0.7}" '
                        f'text-anchor="middle" font-family="{FONT_FAMILY}" '
                        f'font-size="16" font-weight="bold" fill="{COLOR_LETTER}">'
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

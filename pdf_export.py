"""Экспорт кроссворда в PDF через reportlab."""

import math
import os
import platform
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white, HexColor

from models import Crossword

# Размеры
PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
CELL_SIZE = 7 * mm
FONT_NAME = "CyrFont"

# Цвета
COLOR_CELL_BG = white
COLOR_CELL_BORDER = black
COLOR_BLOCKED = HexColor("#2c2c2c")
COLOR_NUMBER = HexColor("#1a73e8")
COLOR_LETTER = black
COLOR_TITLE = HexColor("#333333")
COLOR_CATEGORY = HexColor("#1a73e8")


def _register_font() -> None:
    """Регистрирует шрифт с поддержкой кириллицы."""
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return

    # Пути к шрифтам по ОС
    candidates = []
    system = platform.system()

    if system == "Windows":
        fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        candidates = [
            os.path.join(fonts_dir, "arial.ttf"),
            os.path.join(fonts_dir, "calibri.ttf"),
            os.path.join(fonts_dir, "tahoma.ttf"),
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(FONT_NAME, path))
            return

    raise RuntimeError(
        "Не найден шрифт с поддержкой кириллицы. "
        "Установите Arial или DejaVuSans."
    )


def export_pdf(crossword: Crossword, filepath: str, show_answers: bool = False) -> None:
    """Экспортирует кроссворд в PDF-файл."""
    _register_font()

    c = canvas.Canvas(filepath, pagesize=A4)
    c.setTitle(crossword.title)

    _draw_crossword_page(c, crossword, show_answers)
    c.showPage()
    _draw_clues_page(c, crossword)
    c.showPage()

    c.save()


def _draw_crossword_page(c: canvas.Canvas, cw: Crossword, show_answers: bool) -> None:
    """Рисует страницу с сеткой кроссворда."""
    # Заголовок
    c.setFont(FONT_NAME, 18)
    c.setFillColor(COLOR_TITLE)
    title = cw.title
    if show_answers:
        title += " (ОТВЕТЫ)"
    c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN - 10 * mm, title)

    c.setFont(FONT_NAME, 10)
    c.setFillColor(HexColor("#666666"))
    c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN - 17 * mm, "Кроссворд для воскресной школы")

    ptype = cw.puzzle_type

    if ptype == "circular":
        _draw_circular_page(c, cw, show_answers)
    elif ptype == "honeycomb":
        _draw_honeycomb_page(c, cw, show_answers)
    elif ptype == "japanese":
        _draw_japanese_page(c, cw, show_answers)
    else:
        _draw_grid_page(c, cw, show_answers)


def _draw_grid_page(c: canvas.Canvas, cw: Crossword, show_answers: bool) -> None:
    """Рисует сеточные типы: classic, filword, crisscross, codeword, scanword."""
    ptype = cw.puzzle_type

    # Вычисляем размер ячейки чтобы сетка поместилась
    available_w = PAGE_W - 2 * MARGIN
    available_h = PAGE_H - MARGIN - 30 * mm - MARGIN

    cell = min(CELL_SIZE, available_w / cw.cols, available_h / cw.rows)
    cell = min(cell, 10 * mm)

    grid_w = cw.cols * cell
    grid_h = cw.rows * cell

    start_x = (PAGE_W - grid_w) / 2
    start_y = PAGE_H - MARGIN - 25 * mm

    # Данные для специальных типов
    clue_cells = {}
    if ptype == "scanword":
        for cr, cc, hint, arrow in cw.extra_data.get("clue_cells", []):
            clue_cells[(cr, cc)] = (hint, arrow)

    letter_map = cw.extra_data.get("letter_map", {})
    hint_letters = cw.extra_data.get("hint_letters", [])

    # Рисуем клетки
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = start_x + col * cell
            y = start_y - (row + 1) * cell

            ch = cw.grid[row][col]

            # Сканворд: ячейка-подсказка
            if ptype == "scanword" and (row, col) in clue_cells:
                hint, arrow = clue_cells[(row, col)]
                c.setFillColor(HexColor("#3d5a80"))
                c.rect(x, y, cell, cell, fill=1, stroke=1)
                c.setFillColor(white)
                fs = max(3, min(5, cell / mm * 0.18))
                c.setFont(FONT_NAME, fs)
                c.drawCentredString(x + cell / 2, y + cell * 0.35, hint[:12])
                # Стрелка
                c.setFillColor(HexColor("#f2cc8f"))
                c.setFont(FONT_NAME, fs + 1)
                if arrow == 'right':
                    c.drawString(x + cell - fs * 1.2, y + cell * 0.5, "→")
                else:
                    c.drawCentredString(x + cell / 2, y + 2, "↓")
                continue

            if not ch:
                # Филворд: все клетки заполнены, рисуем пустые лёгким фоном
                if ptype == "filword":
                    c.setFillColor(HexColor("#f0ede8"))
                    c.rect(x, y, cell, cell, fill=1, stroke=1)
                continue

            # Обычная белая клетка
            c.setFillColor(COLOR_CELL_BG)
            c.rect(x, y, cell, cell, fill=1, stroke=1)

            # Филворд: всегда показываем букву
            if ptype == "filword":
                c.setFillColor(COLOR_LETTER)
                fs = max(5, min(12, cell / mm * 0.5))
                c.setFont(FONT_NAME, fs)
                c.drawCentredString(x + cell / 2, y + cell * 0.25, ch)
                continue

            # Кейворд: номер вместо буквы
            if ptype == "codeword":
                num_val = letter_map.get(ch, 0)
                c.setFillColor(HexColor("#3d5a80"))
                fs = max(4, min(7, cell / mm * 0.25))
                c.setFont(FONT_NAME, fs)
                c.drawString(x + 1, y + cell - fs - 1, str(num_val))
                if show_answers or ch in hint_letters:
                    c.setFillColor(COLOR_LETTER if show_answers else HexColor("#e07a5f"))
                    fs2 = max(5, min(11, cell / mm * 0.4))
                    c.setFont(FONT_NAME, fs2)
                    c.drawCentredString(x + cell / 2, y + cell * 0.2, ch)
                continue

            # Буква (classic, crisscross, scanword)
            if show_answers:
                c.setFillColor(COLOR_LETTER)
                font_size = max(6, min(14, cell / mm * 0.55))
                c.setFont(FONT_NAME, font_size)
                c.drawCentredString(x + cell / 2, y + cell * 0.25, ch)

    # Номера (не для крисс-кросса и кейворда)
    if ptype not in ("crisscross", "codeword", "filword"):
        c.setFillColor(COLOR_NUMBER)
        number_font_size = max(4, min(7, cell / mm * 0.3))
        c.setFont(FONT_NAME, number_font_size)

        numbers: dict[tuple[int, int], int] = {}
        for w in cw.words:
            key = (w.row, w.col)
            if key not in numbers:
                numbers[key] = w.number

        for (row, col), num in numbers.items():
            x = start_x + col * cell
            y = start_y - (row + 1) * cell
            c.drawString(x + 1, y + cell - number_font_size - 0.5, str(num))

    # Рамки
    c.setStrokeColor(COLOR_CELL_BORDER)
    c.setLineWidth(0.5)
    for row in range(cw.rows):
        for col in range(cw.cols):
            if cw.grid[row][col]:
                x = start_x + col * cell
                y = start_y - (row + 1) * cell
                c.rect(x, y, cell, cell, fill=0, stroke=1)

    # Крисс-кросс: список слов под сеткой
    if ptype == "crisscross":
        words_by_len = cw.extra_data.get("words_by_length", {})
        y_pos = start_y - cw.rows * cell - 10 * mm
        c.setFillColor(COLOR_TITLE)
        c.setFont(FONT_NAME, 11)
        c.drawString(start_x, y_pos, "Слова для заполнения:")
        y_pos -= 6 * mm
        for length in sorted(words_by_len.keys()):
            c.setFont(FONT_NAME, 9)
            c.setFillColor(COLOR_NUMBER)
            c.drawString(start_x, y_pos, f"{length} букв:")
            x_pos = start_x + 15 * mm
            c.setFillColor(COLOR_LETTER)
            for w in sorted(words_by_len[length]):
                c.drawString(x_pos, y_pos, w)
                x_pos += len(w) * 3 * mm + 5 * mm
                if x_pos > PAGE_W - MARGIN:
                    y_pos -= 5 * mm
                    x_pos = start_x + 15 * mm
            y_pos -= 5 * mm

    # Кейворд: таблица подсказок
    if ptype == "codeword" and hint_letters:
        y_pos = start_y - cw.rows * cell - 8 * mm
        c.setFillColor(COLOR_TITLE)
        c.setFont(FONT_NAME, 10)
        c.drawString(start_x, y_pos, "Подсказки:")
        x_pos = start_x + 25 * mm
        c.setFont(FONT_NAME, 11)
        c.setFillColor(HexColor("#e07a5f"))
        for ch in hint_letters:
            num = letter_map.get(ch, "?")
            c.drawString(x_pos, y_pos, f"{num} = {ch}")
            x_pos += 20 * mm


def _draw_clues_page(c: canvas.Canvas, cw: Crossword) -> None:
    """Рисует страницу с вопросами."""
    y = PAGE_H - MARGIN

    ptype = cw.puzzle_type

    # Филворд: список слов для поиска
    if ptype == "filword":
        c.setFont(FONT_NAME, 16)
        c.setFillColor(COLOR_TITLE)
        c.drawCentredString(PAGE_W / 2, y - 5 * mm, "Найдите слова")
        y -= 15 * mm
        c.setFont(FONT_NAME, 11)
        c.setFillColor(black)
        for w in sorted(cw.words, key=lambda w: w.question.answer):
            c.drawString(MARGIN, y, f"• {w.question.answer} — {w.question.hint}")
            y -= 6 * mm
            if y < MARGIN + 10 * mm:
                c.showPage()
                y = PAGE_H - MARGIN
        return

    # Японский: вопросы к кроссворду (после решения нонограммы)
    if ptype == "japanese":
        c.setFont(FONT_NAME, 16)
        c.setFillColor(COLOR_TITLE)
        c.drawCentredString(PAGE_W / 2, y - 5 * mm, "Разгадайте нонограмму, затем заполните слова")
        y -= 15 * mm

    # Стандартная страница вопросов
    if ptype != "filword":
        c.setFont(FONT_NAME, 16)
        c.setFillColor(COLOR_TITLE)
        c.drawCentredString(PAGE_W / 2, y - 5 * mm, "Вопросы к кроссворду")
        y -= 15 * mm

    across = [w for w in cw.words if w.direction == 'across']
    down = [w for w in cw.words if w.direction == 'down']
    across.sort(key=lambda w: w.number)
    down.sort(key=lambda w: w.number)

    # По горизонтали
    if across:
        y = _draw_clue_section(c, "По горизонтали →", across, y)

    y -= 5 * mm

    # По вертикали
    if down:
        y = _draw_clue_section(c, "По вертикали ↓", down, y)


def _draw_clue_section(
    c: canvas.Canvas, title: str, words: list, y: float
) -> float:
    """Рисует секцию вопросов (горизонталь или вертикаль)."""
    c.setFont(FONT_NAME, 13)
    c.setFillColor(COLOR_CATEGORY)
    c.drawString(MARGIN, y, title)
    y -= 8 * mm

    max_text_width = PAGE_W - 2 * MARGIN - 15 * mm
    line_height = 5 * mm

    for w in words:
        if y < MARGIN + 10 * mm:
            c.showPage()
            y = PAGE_H - MARGIN

        # Номер
        c.setFont(FONT_NAME, 11)
        c.setFillColor(COLOR_NUMBER)
        c.drawString(MARGIN, y, f"{w.number}.")

        # Подсказка
        c.setFillColor(black)
        hint_text = w.question.hint

        # Если есть картинка — добавляем её
        if w.question.image_path and os.path.exists(w.question.image_path):
            try:
                img_size = 50 * mm  # Аж6-подобный размер
                # Проверка места на странице
                if y - img_size < MARGIN + 10 * mm:
                    c.showPage()
                    y = PAGE_H - MARGIN
                # Текст подсказки под номером
                _draw_wrapped_text(
                    c, hint_text, MARGIN + 12 * mm, y,
                    max_text_width, line_height
                )
                y -= line_height + 2 * mm
                # Картинка под текстом, по центру
                img_x = MARGIN + 12 * mm
                c.drawImage(
                    w.question.image_path,
                    img_x, y - img_size,
                    width=img_size, height=img_size,
                    preserveAspectRatio=True,
                    mask='auto',
                )
                y -= img_size + 3 * mm
            except Exception:
                _draw_wrapped_text(
                    c, hint_text, MARGIN + 12 * mm, y, max_text_width, line_height
                )
                y -= line_height + 2 * mm
        else:
            lines = _draw_wrapped_text(
                c, hint_text, MARGIN + 12 * mm, y, max_text_width, line_height
            )
            y -= (lines * line_height) + 2 * mm

        # Категория мелким шрифтом
        if w.question.category:
            c.setFont(FONT_NAME, 7)
            c.setFillColor(HexColor("#999999"))
            c.drawString(MARGIN + 12 * mm, y + 1 * mm, f"[{w.question.category}]")
            y -= 3 * mm

    return y


def _draw_wrapped_text(
    c: canvas.Canvas, text: str, x: float, y: float,
    max_width: float, line_height: float, font_name: str = FONT_NAME, font_size: int = 10
) -> int:
    """Рисует текст с переносом строк. Возвращает количество строк."""
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_height, line)

    return max(1, len(lines))


def _draw_circular_page(c: canvas.Canvas, cw: Crossword, show_answers: bool) -> None:
    """Рисует циклический кроссворд в PDF."""
    n_rings = cw.extra_data.get("n_rings", 4)
    n_sectors = cw.extra_data.get("n_sectors", 12)

    cx = PAGE_W / 2
    cy = PAGE_H / 2 - 10 * mm
    max_radius = min(PAGE_W, PAGE_H) / 2 - MARGIN - 20 * mm
    ring_width = max_radius / (n_rings + 1)
    inner_r = ring_width

    for ring in range(n_rings):
        r_inner = inner_r + ring * ring_width
        r_outer = r_inner + ring_width

        for sec in range(n_sectors):
            angle_start = sec * (360 / n_sectors)
            angle_extent = 360 / n_sectors

            ch = cw.grid[ring][sec]
            if ch:
                c.setStrokeColor(COLOR_CELL_BORDER)
                c.setFillColor(COLOR_CELL_BG)
            else:
                c.setStrokeColor(HexColor("#cccccc"))
                c.setFillColor(HexColor("#f0ede8"))

            # Внешняя дуга
            c.arc(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                  angle_start, angle_extent)
            # Внутренняя дуга
            c.arc(cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
                  angle_start, angle_extent)

            # Радиальные линии
            for angle_deg in [angle_start, angle_start + angle_extent]:
                rad = math.radians(angle_deg)
                c.line(cx + r_inner * math.cos(rad), cy + r_inner * math.sin(rad),
                       cx + r_outer * math.cos(rad), cy + r_outer * math.sin(rad))

            if ch and show_answers:
                mid_r = (r_inner + r_outer) / 2
                mid_angle = math.radians(angle_start + angle_extent / 2)
                tx = cx + mid_r * math.cos(mid_angle)
                ty = cy + mid_r * math.sin(mid_angle)
                fs = max(4, min(8, ring_width / mm * 0.4))
                c.setFillColor(COLOR_LETTER)
                c.setFont(FONT_NAME, fs)
                c.drawCentredString(tx, ty - fs / 3, ch)

    # Центральный круг
    c.setFillColor(white)
    c.circle(cx, cy, inner_r, fill=1, stroke=1)


def _draw_honeycomb_page(c: canvas.Canvas, cw: Crossword, show_answers: bool) -> None:
    """Рисует сотовый кроссворд в PDF."""
    available_w = PAGE_W - 2 * MARGIN
    available_h = PAGE_H - MARGIN - 30 * mm - MARGIN

    hex_w = available_w / (cw.cols + 0.5)
    hex_h = available_h / (cw.rows * 0.75 + 0.25)
    hex_size = min(hex_w / math.sqrt(3), hex_h / 2, 10 * mm)

    ox = MARGIN + 10 * mm
    oy_base = PAGE_H - MARGIN - 30 * mm

    for row in range(cw.rows):
        for col in range(cw.cols):
            ch = cw.grid[row][col]
            if not ch:
                continue

            x_offset = (hex_size * math.sqrt(3) * 0.5) if row % 2 else 0
            hx = ox + col * hex_size * math.sqrt(3) + x_offset + hex_size
            hy = oy_base - row * hex_size * 1.5

            # Рисуем гексагон
            path = c.beginPath()
            for i in range(6):
                angle = math.radians(60 * i - 30)
                px = hx + hex_size * math.cos(angle)
                py = hy + hex_size * math.sin(angle)
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            path.close()
            c.setFillColor(COLOR_CELL_BG)
            c.setStrokeColor(COLOR_CELL_BORDER)
            c.drawPath(path, fill=1, stroke=1)

            if show_answers:
                fs = max(4, min(8, hex_size / mm * 0.5))
                c.setFillColor(COLOR_LETTER)
                c.setFont(FONT_NAME, fs)
                c.drawCentredString(hx, hy - fs / 3, ch)


def _draw_japanese_page(c: canvas.Canvas, cw: Crossword, show_answers: bool) -> None:
    """Рисует японский кроссворд (нонограмму) в PDF."""
    row_clues = cw.extra_data.get("row_clues", [])
    col_clues = cw.extra_data.get("col_clues", [])

    max_row_clue = max((len(rc) for rc in row_clues), default=1)
    max_col_clue = max((len(cc) for cc in col_clues), default=1)

    clue_w = max_row_clue * 6 * mm + 5 * mm
    clue_h = max_col_clue * 5 * mm + 5 * mm

    available_w = PAGE_W - 2 * MARGIN - clue_w
    available_h = PAGE_H - MARGIN - 30 * mm - MARGIN - clue_h

    cell = min(available_w / max(cw.cols, 1), available_h / max(cw.rows, 1))
    cell = min(cell, 8 * mm)

    sx = MARGIN + clue_w
    sy = PAGE_H - MARGIN - 25 * mm - clue_h

    # Подсказки по строкам
    c.setFont(FONT_NAME, 7)
    c.setFillColor(COLOR_TITLE)
    for r, clues in enumerate(row_clues):
        y = sy - r * cell - cell * 0.6
        txt = "  ".join(str(v) for v in clues)
        c.drawRightString(sx - 2 * mm, y, txt)

    # Подсказки по столбцам
    for col_i, clues in enumerate(col_clues):
        x = sx + col_i * cell + cell * 0.5
        for ci, val in enumerate(clues):
            y = sy + (max_col_clue - len(clues) + ci) * (-5 * mm) + 5 * mm
            c.drawCentredString(x, y, str(val))

    # Сетка
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = sx + col * cell
            y = sy - (row + 1) * cell
            ch = cw.grid[row][col]

            if show_answers and ch:
                c.setFillColor(HexColor("#5b7fc7"))
                c.rect(x, y, cell, cell, fill=1, stroke=1)
                fs = max(4, min(7, cell / mm * 0.45))
                c.setFillColor(white)
                c.setFont(FONT_NAME, fs)
                c.drawCentredString(x + cell / 2, y + cell * 0.25, ch)
            else:
                c.setFillColor(white)
                c.setStrokeColor(HexColor("#cccccc"))
                c.rect(x, y, cell, cell, fill=1, stroke=1)

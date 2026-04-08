"""Экспорт кроссворда в растровые изображения: PNG (прозрачный фон) и JPG."""

from PIL import Image, ImageDraw, ImageFont
import platform
import os

from models import Crossword

# Размеры
CELL_SIZE = 60
MARGIN = 40
TITLE_HEIGHT = 80

# Цвета
COLOR_CELL_BG = (255, 255, 255, 255)
COLOR_CELL_BORDER = (51, 51, 51, 255)
COLOR_NUMBER = (26, 115, 232, 255)
COLOR_LETTER = (51, 51, 51, 255)
COLOR_TITLE = (51, 51, 51, 255)
COLOR_SUBTITLE = (102, 102, 102, 255)
COLOR_TRANSPARENT = (0, 0, 0, 0)
COLOR_WHITE_BG = (255, 255, 255, 255)


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Находит системный шрифт с кириллицей."""
    candidates = []
    system = platform.system()

    if system == "Windows":
        fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        candidates = [
            os.path.join(fonts_dir, "arial.ttf"),
            os.path.join(fonts_dir, "calibri.ttf"),
            os.path.join(fonts_dir, "tahoma.ttf"),
        ]
    elif system == "Darwin":
        candidates = [
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def _get_bold_font(size: int) -> ImageFont.FreeTypeFont:
    """Находит жирный шрифт с кириллицей."""
    candidates = []
    system = platform.system()

    if system == "Windows":
        fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        candidates = [
            os.path.join(fonts_dir, "arialbd.ttf"),
            os.path.join(fonts_dir, "calibrib.ttf"),
        ]
    elif system == "Darwin":
        candidates = [
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return _get_font(size)


def _render_grid(cw: Crossword, show_answers: bool, transparent: bool,
                 cell_size: int = CELL_SIZE, scale: int = 3) -> Image.Image:
    """Рендерит сетку кроссворда в изображение с увеличенным разрешением (scale)."""
    S = scale  # множитель разрешения
    CELL_SIZE = cell_size * S
    _MARGIN = MARGIN * S
    _TITLE_HEIGHT = TITLE_HEIGHT * S

    grid_w = cw.cols * CELL_SIZE
    grid_h = cw.rows * CELL_SIZE

    img_w = grid_w + 2 * _MARGIN
    img_h = grid_h + 2 * _MARGIN + _TITLE_HEIGHT

    bg = COLOR_TRANSPARENT if transparent else COLOR_WHITE_BG
    img = Image.new("RGBA", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    font_title = _get_bold_font(int(22 * S))
    font_subtitle = _get_font(int(12 * S))
    font_number = _get_bold_font(max(8, int(CELL_SIZE * 0.25)))
    font_letter = _get_bold_font(max(10, int(CELL_SIZE * 0.45)))

    # Заголовок
    title = cw.title
    if show_answers:
        title += " (ОТВЕТЫ)"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) / 2, _MARGIN), title, fill=COLOR_TITLE, font=font_title)

    subtitle = "Кроссворд для воскресной школы"
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    sw = bbox2[2] - bbox2[0]
    draw.text(((img_w - sw) / 2, _MARGIN + 32 * S), subtitle, fill=COLOR_SUBTITLE, font=font_subtitle)

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

    ox = _MARGIN
    oy = _MARGIN + _TITLE_HEIGHT

    font_clue = _get_font(max(8, int(CELL_SIZE * 0.18)))
    font_clue_small = _get_font(max(6, int(CELL_SIZE * 0.14)))
    font_arrow = _get_bold_font(max(10 * S, CELL_SIZE // 4))

    # Отложенные стрелки сканворда (рисуем поверх всех ячеек)
    deferred_arrows = []

    # Ячейки
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = ox + col * CELL_SIZE
            y = oy + row * CELL_SIZE
            ch = cw.grid[row][col]

            # Сканворд: пропуск span-продолжений
            if cw.puzzle_type == "scanword" and (row, col) in clue_skip:
                continue

            # Сканворд: подсказка (с span)
            if cw.puzzle_type == "scanword" and (row, col) in clue_cells:
                hint, arrow, sr, sc, t_r, t_c = clue_cells[(row, col)]
                bw = sc * CELL_SIZE
                bh = sr * CELL_SIZE

                draw.rectangle(
                    [x, y, x + bw, y + bh],
                    fill=(61, 90, 128, 255), outline=(51, 51, 51, 255), width=max(1, S),
                )

                # Выбираем шрифт по размеру блока
                use_font = font_clue if sr * sc > 1 else font_clue_small

                # Перенос текста по строкам
                words_list = hint.split()
                max_text_w = bw - 6 * S
                lines = []
                current = ""
                for word in words_list:
                    test = (current + " " + word).strip()
                    tbbox = draw.textbbox((0, 0), test, font=use_font)
                    if tbbox[2] - tbbox[0] <= max_text_w:
                        current = test
                    else:
                        if current:
                            lines.append(current)
                        current = word
                if current:
                    lines.append(current)

                line_h = use_font.size + 2
                total_h = len(lines) * line_h
                start_y = y + (bh - total_h) / 2 - 2 * S
                for i, line in enumerate(lines):
                    lbbox = draw.textbbox((0, 0), line, font=use_font)
                    lw = lbbox[2] - lbbox[0]
                    draw.text(
                        (x + (bw - lw) / 2, start_y + i * line_h),
                        line, fill=(255, 255, 255, 255), font=use_font
                    )

                # Запоминаем стрелку для отрисовки поверх всех ячеек
                if t_r is not None and t_c is not None:
                    deferred_arrows.append((x, y, bw, bh, arrow, t_r, t_c))
                continue

            # Тёмные блоки (сканворд)
            if ch == '#BLOCK#' and cw.puzzle_type == "scanword":
                draw.rectangle(
                    [x, y, x + CELL_SIZE, y + CELL_SIZE],
                    fill=(61, 90, 128, 255), outline=(51, 51, 51, 255), width=max(1, S),
                )
                continue

            # Пустые ячейки — не рисуем
            if not ch or ch in ('#CLUE#', '#BLOCK#'):
                continue

            # Белая ячейка
            draw.rectangle(
                [x, y, x + CELL_SIZE, y + CELL_SIZE],
                fill=COLOR_CELL_BG,
                outline=COLOR_CELL_BORDER,
                width=max(1, S),
            )

            # Номер (не для сканворда)
            if cw.puzzle_type != "scanword" and (row, col) in numbers:
                draw.text(
                    (x + 3 * S, y + 1 * S),
                    str(numbers[(row, col)]),
                    fill=COLOR_NUMBER,
                    font=font_number,
                )

            # Буква
            if show_answers:
                lbbox = draw.textbbox((0, 0), ch, font=font_letter)
                lw = lbbox[2] - lbbox[0]
                lh = lbbox[3] - lbbox[1]
                draw.text(
                    (x + (CELL_SIZE - lw) / 2, y + (CELL_SIZE - lh) / 2 + 2 * S),
                    ch,
                    fill=COLOR_LETTER,
                    font=font_letter,
                )

    # Сканворд: рисуем стрелки ПОВЕРХ всех ячеек
    if cw.puzzle_type == "scanword" and deferred_arrows:
        ac = (242, 204, 143, 255)
        lw_line = max(1, int(CELL_SIZE * 0.03))
        asz = int(CELL_SIZE * 0.15)

        for (bx, by, bw, bh, arrow, at_r, at_c) in deferred_arrows:
            # Края целевой ячейки
            t_left = int(ox + at_c * CELL_SIZE)
            t_top = int(oy + at_r * CELL_SIZE)
            t_cx = int(t_left + CELL_SIZE / 2)
            t_cy = int(t_top + CELL_SIZE / 2)

            if arrow == 'right':
                sx_a = int(bx + bw)
                sy_a = int(by + bh / 2)
                draw.line([(sx_a, sy_a), (t_left, t_cy)], fill=ac, width=lw_line)
                draw.polygon([(t_left, t_cy - asz), (t_left + asz, t_cy), (t_left, t_cy + asz)], fill=ac)
            elif arrow == 'down':
                sx_a = int(bx + bw / 2)
                sy_a = int(by + bh)
                draw.line([(sx_a, sy_a), (t_cx, t_top)], fill=ac, width=lw_line)
                draw.polygon([(t_cx - asz, t_top), (t_cx, t_top + asz), (t_cx + asz, t_top)], fill=ac)
            elif arrow == 'down_right':
                sx_a = int(bx + bw / 2)
                sy_a = int(by + bh)
                bend_x = min(sx_a, t_left - asz * 2)
                bend_y = t_cy
                draw.line([(sx_a, sy_a), (bend_x, bend_y)], fill=ac, width=lw_line)
                draw.line([(bend_x, bend_y), (t_left, t_cy)], fill=ac, width=lw_line)
                draw.polygon([(t_left, t_cy - asz), (t_left + asz, t_cy), (t_left, t_cy + asz)], fill=ac)
            elif arrow == 'right_down':
                sx_a = int(bx + bw)
                sy_a = int(by + bh / 2)
                bend_x = t_cx
                bend_y = min(sy_a, t_top - asz * 2)
                draw.line([(sx_a, sy_a), (bend_x, bend_y)], fill=ac, width=lw_line)
                draw.line([(bend_x, bend_y), (t_cx, t_top)], fill=ac, width=lw_line)
                draw.polygon([(t_cx - asz, t_top), (t_cx, t_top + asz), (t_cx + asz, t_top)], fill=ac)

    return img


def export_png(crossword: Crossword, filepath: str, show_answers: bool = False,
               cell_size: int = CELL_SIZE) -> None:
    """Экспортирует кроссворд в PNG с прозрачным фоном (высокое разрешение)."""
    img = _render_grid(crossword, show_answers, transparent=True, cell_size=cell_size)
    img.save(filepath, "PNG", dpi=(300, 300))


def export_jpg(crossword: Crossword, filepath: str, show_answers: bool = False,
               cell_size: int = CELL_SIZE) -> None:
    """Экспортирует кроссворд в JPG (белый фон, высокое разрешение)."""
    img = _render_grid(crossword, show_answers, transparent=False, cell_size=cell_size)
    # JPG не поддерживает прозрачность — конвертируем в RGB
    rgb = Image.new("RGB", img.size, (255, 255, 255))
    rgb.paste(img, mask=img.split()[3])
    rgb.save(filepath, "JPEG", quality=95, dpi=(300, 300))

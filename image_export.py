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


def _render_grid(cw: Crossword, show_answers: bool, transparent: bool) -> Image.Image:
    """Рендерит сетку кроссворда в изображение."""
    grid_w = cw.cols * CELL_SIZE
    grid_h = cw.rows * CELL_SIZE

    img_w = grid_w + 2 * MARGIN
    img_h = grid_h + 2 * MARGIN + TITLE_HEIGHT

    bg = COLOR_TRANSPARENT if transparent else COLOR_WHITE_BG
    img = Image.new("RGBA", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    font_title = _get_bold_font(22)
    font_subtitle = _get_font(12)
    font_number = _get_bold_font(11)
    font_letter = _get_bold_font(22)

    # Заголовок
    title = cw.title
    if show_answers:
        title += " (ОТВЕТЫ)"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((img_w - tw) / 2, MARGIN), title, fill=COLOR_TITLE, font=font_title)

    subtitle = "Кроссворд для воскресной школы"
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    sw = bbox2[2] - bbox2[0]
    draw.text(((img_w - sw) / 2, MARGIN + 32), subtitle, fill=COLOR_SUBTITLE, font=font_subtitle)

    # Номера по позициям
    numbers: dict[tuple[int, int], int] = {}
    for w in cw.words:
        key = (w.row, w.col)
        if key not in numbers:
            numbers[key] = w.number

    ox = MARGIN
    oy = MARGIN + TITLE_HEIGHT

    # Ячейки
    for row in range(cw.rows):
        for col in range(cw.cols):
            x = ox + col * CELL_SIZE
            y = oy + row * CELL_SIZE
            ch = cw.grid[row][col]

            if ch:
                # Белая ячейка
                draw.rectangle(
                    [x, y, x + CELL_SIZE, y + CELL_SIZE],
                    fill=COLOR_CELL_BG,
                    outline=COLOR_CELL_BORDER,
                    width=1,
                )

                # Номер
                if (row, col) in numbers:
                    draw.text(
                        (x + 3, y + 1),
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
                        (x + (CELL_SIZE - lw) / 2, y + (CELL_SIZE - lh) / 2 + 2),
                        ch,
                        fill=COLOR_LETTER,
                        font=font_letter,
                    )

    return img


def export_png(crossword: Crossword, filepath: str, show_answers: bool = False) -> None:
    """Экспортирует кроссворд в PNG с прозрачным фоном."""
    img = _render_grid(crossword, show_answers, transparent=True)
    img.save(filepath, "PNG")


def export_jpg(crossword: Crossword, filepath: str, show_answers: bool = False) -> None:
    """Экспортирует кроссворд в JPG (белый фон)."""
    img = _render_grid(crossword, show_answers, transparent=False)
    # JPG не поддерживает прозрачность — конвертируем в RGB
    rgb = Image.new("RGB", img.size, (255, 255, 255))
    rgb.paste(img, mask=img.split()[3])
    rgb.save(filepath, "JPEG", quality=95)

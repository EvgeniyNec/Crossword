"""Главное окно приложения — генератор кроссвордов для воскресной школы."""

import os
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from models import Question, Crossword
from crossword_engine import CrosswordEngine
from puzzle_engines import (generate_filword, generate_crisscross,
                            generate_codeword, generate_scanword,
                            generate_circular, generate_honeycomb,
                            generate_japanese)
from data_manager import save_questions, load_questions
from pdf_export import export_pdf
from docx_export import export_docx
from svg_export import export_svg, export_svg_with_clues
from image_export import export_png, export_jpg
from text_parser import parse_questions_text


CATEGORIES = ["Визуальные подсказки", "Ветхий Завет", "Новый Завет", "Общие"]

PUZZLE_TYPES = [
    ("Классический", "classic"),
    ("Сканворд", "scanword"),
    ("Крисс-кросс", "crisscross"),
    ("Филворд", "filword"),
    ("Циклический", "circular"),
    ("Кейворд", "codeword"),
    ("Сотовый", "honeycomb"),
    ("Японский", "japanese"),
]

# Промпт для ИИ-помощника

# Цвета — светлая тёплая палитра
BG_COLOR = "#faf7f2"          # тёплый кремовый фон
SIDEBAR_BG = "#ffffff"
ACCENT = "#5b7fc7"            # мягкий синий
ACCENT_DARK = "#3d5a80"       # тёмно-синий для текста
ACCENT_LIGHT = "#e8eef7"      # светло-голубой
WARM_ACCENT = "#e07a5f"       # тёплый коралловый
WARM_LIGHT = "#fce4d6"        # светло-коралловый
GREEN_ACCENT = "#81b29a"      # мягкий зелёный
GREEN_LIGHT = "#daf1e4"       # светло-зелёный
GOLD_ACCENT = "#f2cc8f"       # золотистый
CELL_FILLED = "#ffffff"
CELL_EMPTY = "#e8e4df"
CELL_BORDER = "#5b7fc7"
NUMBER_COLOR = "#e07a5f"
LETTER_COLOR = "#3d3d3d"
HIGHLIGHT_FILL = "#fff3cd"    # жёлтая подсветка
HIGHLIGHT_BORDER = "#f2cc8f"


class CrosswordApp:
    """Главное приложение."""

    def __init__(self, root: tk.Tk):
        self.root = root
        from main import VERSION
        self.root.title(f"✝ Кроссворд — Воскресная школа  v{VERSION}")
        self.root.geometry("1200x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG_COLOR)

        self.questions: list[Question] = []
        self.crossword: Crossword | None = None
        self.show_answers = tk.BooleanVar(value=False)
        self.orientation = tk.StringVar(value="auto")
        self.puzzle_type_var = tk.StringVar(value="classic")
        self.engine = CrosswordEngine()
        self.cell_size_var = tk.IntVar(value=40)
        # Маппинг: question answer -> номер в кроссворде (заполняется после генерации)
        self._cw_numbers: dict[int, list[int]] = {}  # question_index -> [cw_numbers]
        # Для inline-редактирования
        self._edit_widget: tk.Widget | None = None
        # Для клика по кроссворду -> выбор вопроса
        self._cell_map: dict[tuple[int, int], int] = {}  # (row,col) -> question index
        self._grid_params: dict = {}  # ox, oy, cell size для пересчёта кликов
        # Сортировка
        self._sort_col: str = ""
        self._sort_reverse: bool = False
        # Маппинг: question index -> ячейки слова в кроссворде
        self._question_cells: dict[int, list[tuple[int, int]]] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        """Строит интерфейс."""
        # Стили
        style = ttk.Style()
        style.theme_use("clam")

        # Базовые стили
        style.configure("TFrame", background=BG_COLOR)
        style.configure("Sidebar.TFrame", background=SIDEBAR_BG)
        style.configure("TLabel", background=BG_COLOR, font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"), foreground=ACCENT_DARK)

        # Кнопки — скруглённые, цветные
        style.configure("TButton", font=("Segoe UI", 9), padding=(10, 5), width=18)
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"),
                        foreground="white", background=ACCENT, padding=(10, 5), width=18)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_DARK), ("!disabled", ACCENT)])
        style.configure("Warm.TButton", font=("Segoe UI", 9),
                        foreground="white", background=WARM_ACCENT, padding=(10, 5), width=18)
        style.map("Warm.TButton",
                  background=[("active", "#c96a52"), ("!disabled", WARM_ACCENT)])
        style.configure("Green.TButton", font=("Segoe UI", 9),
                        foreground="white", background=GREEN_ACCENT, padding=(10, 5), width=18)
        style.map("Green.TButton",
                  background=[("active", "#6a9c85"), ("!disabled", GREEN_ACCENT)])

        # LabelFrame — тёплые рамки
        style.configure("TLabelframe", background=SIDEBAR_BG)
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"),
                        foreground=ACCENT_DARK, background=SIDEBAR_BG)

        # Treeview — аккуратная таблица
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26,
                        background=SIDEBAR_BG, fieldbackground=SIDEBAR_BG)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        background=ACCENT_LIGHT, foreground=ACCENT_DARK)
        style.map("Treeview", background=[("selected", ACCENT_LIGHT)],
                  foreground=[("selected", ACCENT_DARK)])

        # Checkbutton
        style.configure("TCheckbutton", background=BG_COLOR, font=("Segoe UI", 9))

        # PanedWindow
        style.configure("TPanedwindow", background=BG_COLOR)

        # Главный контейнер
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === Левая панель: вопросы ===
        left = ttk.Frame(main, style="Sidebar.TFrame", width=420)
        main.add(left, weight=1)

        self._build_left_panel(left)

        # === Правая панель: кроссворд ===
        right = ttk.Frame(main)
        main.add(right, weight=2)

        self._build_right_panel(right)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        """Левая панель — управление вопросами."""
        # Заголовок
        ttk.Label(parent, text="📝 Вопросы и ответы", style="Title.TLabel",
                  background=SIDEBAR_BG).pack(pady=(10, 5), padx=10, anchor="w")

        # Форма добавления
        form = ttk.LabelFrame(parent, text="Добавить вопрос", padding=8)
        form.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form, text="Ответ (слово):").grid(row=0, column=0, sticky="w")
        self.entry_answer = ttk.Entry(form, width=30)
        self.entry_answer.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form, text="Подсказка:").grid(row=1, column=0, sticky="w")
        self.entry_hint = ttk.Entry(form, width=30)
        self.entry_hint.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form, text="Категория:").grid(row=2, column=0, sticky="w")
        self.combo_category = ttk.Combobox(form, values=CATEGORIES, state="readonly", width=27)
        self.combo_category.set(CATEGORIES[-1])
        self.combo_category.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form, text="Картинка:").grid(row=3, column=0, sticky="w")
        img_frame = ttk.Frame(form)
        img_frame.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        self.entry_image = ttk.Entry(img_frame, width=20)
        self.entry_image.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_frame, text="📂", width=3,
                   command=self._browse_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(img_frame, text="✕", width=3,
                   command=self._clear_image).pack(side=tk.LEFT, padx=2)

        form.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btn_frame, text="Добавить", style="Green.TButton", command=self._add_question).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Добавить списком", style="Accent.TButton", command=self._batch_import).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Удалить выбранный", style="Warm.TButton", command=self._delete_question).pack(side=tk.LEFT, padx=2)

        # Список вопросов
        list_frame = ttk.LabelFrame(parent, text="Список вопросов", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("num", "cw_num", "answer", "hint", "category", "img")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        self.tree.heading("num", text="№", command=lambda: self._sort_by_column("num"))
        self.tree.heading("cw_num", text="Кр.№", command=lambda: self._sort_by_column("cw_num"))
        self.tree.heading("answer", text="Ответ", command=lambda: self._sort_by_column("answer"))
        self.tree.heading("hint", text="Подсказка", command=lambda: self._sort_by_column("hint"))
        self.tree.heading("category", text="Категория", command=lambda: self._sort_by_column("category"))
        self.tree.heading("img", text="Картинка", command=lambda: self._sort_by_column("img"))
        self.tree.column("num", width=30, anchor="center", stretch=False)
        self.tree.column("cw_num", width=40, anchor="center", stretch=False)
        self.tree.column("answer", width=80, stretch=False)
        self.tree.column("hint", width=300, stretch=True)
        self.tree.column("category", width=100, stretch=False)
        self.tree.column("img", width=50, anchor="center", stretch=False)

        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Двойной клик — inline-редактирование
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        # Выбор строки — подсветка в кроссворде
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Кнопки файлов
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(file_frame, text="Сохранить набор", style="Accent.TButton",
                   command=self._save_questions).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_frame, text="Загрузить набор", style="Accent.TButton",
                   command=self._load_questions).pack(side=tk.LEFT, padx=2)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        """Правая панель — предпросмотр и экспорт."""
        # Панель кнопок сверху
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(toolbar, text="🧩 Кроссворд", style="Title.TLabel").pack(side=tk.LEFT)

        # Кнопки справа
        btn_right = ttk.Frame(toolbar)
        btn_right.pack(side=tk.RIGHT)

        ttk.Button(btn_right, text="Сгенерировать", style="Warm.TButton",
                   command=self._generate).pack(side=tk.LEFT, padx=3)

        ttk.Checkbutton(btn_right, text="Показать ответы",
                        variable=self.show_answers,
                        command=self._redraw).pack(side=tk.LEFT, padx=3)

        # Ориентация и тип кроссворда
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=tk.X, padx=10, pady=(0, 2))

        ttk.Label(settings_frame, text="Тип:").pack(side=tk.LEFT)
        type_combo = ttk.Combobox(settings_frame, textvariable=self.puzzle_type_var,
                                  values=[name for name, _ in PUZZLE_TYPES],
                                  state="readonly", width=16)
        type_combo.set("Классический")
        type_combo.pack(side=tk.LEFT, padx=(2, 10))
        type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        ttk.Label(settings_frame, text="Ориентация:").pack(side=tk.LEFT)
        for val, label in [("auto", "Авто"), ("horizontal", "Гор."), ("vertical", "Верт.")]:
            ttk.Radiobutton(settings_frame, text=label, variable=self.orientation,
                            value=val).pack(side=tk.LEFT, padx=2)

        ttk.Separator(settings_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(settings_frame, text="Ячейка (px):").pack(side=tk.LEFT)
        cell_spin = ttk.Spinbox(settings_frame, from_=20, to=200, width=4,
                                textvariable=self.cell_size_var, command=self._redraw)
        cell_spin.pack(side=tk.LEFT, padx=2)
        cell_spin.bind("<Return>", lambda e: self._redraw())

        # Панель экспорта (вторая строка)
        export_bar = ttk.LabelFrame(parent, text="Экспорт", padding=3)
        export_bar.pack(fill=tk.X, padx=10, pady=(5, 2))

        ttk.Button(export_bar, text="PDF (пустой)", style="Accent.TButton",
                   command=lambda: self._export_pdf(False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_bar, text="PDF (ответы)", style="Accent.TButton",
                   command=lambda: self._export_pdf(True)).pack(side=tk.LEFT, padx=2)
        ttk.Separator(export_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(export_bar, text="Word (пустой)", style="Green.TButton",
                   command=lambda: self._export_docx(False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_bar, text="Word (ответы)", style="Green.TButton",
                   command=lambda: self._export_docx(True)).pack(side=tk.LEFT, padx=2)
        ttk.Separator(export_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(export_bar, text="SVG (сетка)", style="Accent.TButton",
                   command=lambda: self._export_svg(False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_bar, text="SVG (полный)", style="Accent.TButton",
                   command=lambda: self._export_svg(True)).pack(side=tk.LEFT, padx=2)
        ttk.Separator(export_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(export_bar, text="PNG", style="Warm.TButton",
                   command=self._export_png).pack(side=tk.LEFT, padx=2)
        ttk.Button(export_bar, text="JPG", style="Warm.TButton",
                   command=self._export_jpg).pack(side=tk.LEFT, padx=2)

        # Заголовок кроссворда
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, padx=10, pady=2)
        ttk.Label(title_frame, text="Заголовок:").pack(side=tk.LEFT)
        self.entry_title = ttk.Entry(title_frame, width=40)
        self.entry_title.insert(0, "Кроссворд для воскресной школы")
        self.entry_title.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Canvas для кроссворда
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(canvas_frame, bg="#fdf8f3", highlightthickness=1,
                                highlightbackground=ACCENT_LIGHT)
        scroll_x = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        scroll_y = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>",
                         lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))

        # Статусная строка
        self.status_var = tk.StringVar(value="Добавьте вопросы и нажмите «Сгенерировать»")
        ttk.Label(parent, textvariable=self.status_var,
                  foreground="#666").pack(padx=10, pady=(0, 8), anchor="w")

    # ========== Действия ==========

    def _batch_import(self) -> None:
        """Открывает окно для массового импорта вопросов из текста."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить вопросы списком")
        dialog.geometry("750x650")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Вставьте текст с вопросами в формате:\n"
                 "ОТВЕТ: подсказка\n\n"
                 "Заголовки категорий распознаются автоматически\n"
                 "(Ветхий Завет, Новый Завет, Визуальные подсказки)",
            justify="left",
            font=("Segoe UI", 9),
        ).pack(padx=15, pady=(15, 5), anchor="w")

        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Segoe UI", 10))
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scroll.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Статус
        status_var = tk.StringVar(value="")
        ttk.Label(dialog, textvariable=status_var, foreground="#666").pack(padx=15, anchor="w")

        def do_preview():
            raw = text_widget.get("1.0", tk.END)
            parsed = parse_questions_text(raw)
            if parsed:
                cats = {}
                for q in parsed:
                    cats[q.category] = cats.get(q.category, 0) + 1
                details = ", ".join(f"{cat}: {n}" for cat, n in cats.items())
                status_var.set(f"Найдено {len(parsed)} вопросов ({details})")
            else:
                status_var.set("Вопросы не найдены. Проверьте формат: ОТВЕТ: подсказка")

        def do_import():
            raw = text_widget.get("1.0", tk.END)
            parsed = parse_questions_text(raw)
            if not parsed:
                messagebox.showwarning("Внимание", "Не удалось распознать вопросы.\n\nФормат: ОТВЕТ: подсказка", parent=dialog)
                return
            self.questions.extend(parsed)
            self._refresh_tree()
            self.status_var.set(f"Импортировано {len(parsed)} вопросов.")
            dialog.destroy()

        def do_replace():
            raw = text_widget.get("1.0", tk.END)
            parsed = parse_questions_text(raw)
            if not parsed:
                messagebox.showwarning("Внимание", "Не удалось распознать вопросы.\n\nФормат: ОТВЕТ: подсказка", parent=dialog)
                return
            self.questions = parsed
            self._refresh_tree()
            self.status_var.set(f"Загружено {len(parsed)} вопросов (список заменён).")
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
        ttk.Button(btn_frame, text="Предпросмотр", style="Accent.TButton", command=do_preview).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Добавить к текущим", style="Green.TButton", command=do_import).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Заменить все", style="Warm.TButton", command=do_replace).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🤖 Промпт для ИИ", command=lambda: self._ai_prompt_dialog(dialog)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

    def _ai_prompt_dialog(self, parent_dialog=None) -> None:
        """Модальное окно с промптом для ИИ-генерации вопросов."""
        owner = parent_dialog or self.root
        dialog = tk.Toplevel(owner)
        dialog.title("Промпт для ИИ")
        dialog.geometry("750x750")
        dialog.transient(owner)
        dialog.grab_set()

        # Пояснение
        info_text = (
            "Если вы умеете работать с Иван Ивановичем \U0001f916 — передайте ему этот промпт, "
            "и он сгенерирует вопросы в нужном формате.\n"
            "Количество вопросов для каждой категории можете скорректировать ниже.\n"
            "Это базовый промпт для вашего удобства.\n\n"
            "⚠️ Помните: Иван Иванович — помощник, а не богослов! "
            "Он может ошибаться в цитатах, ссылках и даже придумывать несуществующие стихи. "
            "Качество ответов зависит от модели ИИ, которую вы используете. "
            "Пожалуйста, всегда проверяйте сгенерированные вопросы перед использованием — "
            "особенно ссылки на Библию и правильность подсказок. "
            "Доверяй, но проверяй! 😊"
        )
        ttk.Label(
            dialog, text=info_text, justify="left",
            font=("Segoe UI", 9), wraplength=650,
        ).pack(padx=15, pady=(15, 10), anchor="w")

        # Фрейм с настройками количества
        counts_frame = ttk.LabelFrame(dialog, text="Количество вопросов по категориям", padding=8)
        counts_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        cat_vars = {}
        for i, cat in enumerate(CATEGORIES):
            ttk.Label(counts_frame, text=f"{cat}:").grid(row=i, column=0, sticky="w", padx=(5, 10), pady=2)
            var = tk.IntVar(value=5)
            spin = ttk.Spinbox(counts_frame, from_=0, to=50, textvariable=var, width=5)
            spin.grid(row=i, column=1, sticky="w", pady=2)
            cat_vars[cat] = var
            var.trace_add("write", lambda *_: self.root.after_idle(refresh_prompt))

        # Сложность
        diff_frame = ttk.LabelFrame(dialog, text="Сложность подсказок", padding=8)
        diff_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        difficulty_var = tk.IntVar(value=1)
        diff_descriptions = {
            1: "Лёгкий — простые и очевидные подсказки",
            2: "Средний — требуют размышления",
            3: "Сложный — завуалированные, с отсылками",
        }
        for val, desc in diff_descriptions.items():
            ttk.Radiobutton(diff_frame, text=desc, variable=difficulty_var, value=val).pack(anchor="w", pady=1)
        difficulty_var.trace_add("write", lambda *_: self.root.after_idle(refresh_prompt))

        # Тема
        theme_frame = ttk.LabelFrame(dialog, text="Тема (необязательно)", padding=8)
        theme_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        ttk.Label(theme_frame, text="Например: о Давиде, о любви, притчи Иисуса",
                  foreground="#888", font=("Segoe UI", 8)).pack(anchor="w")
        theme_var = tk.StringVar(value="")
        theme_entry = ttk.Entry(theme_frame, textvariable=theme_var, font=("Segoe UI", 10))
        theme_entry.pack(fill=tk.X, pady=(3, 0))
        theme_var.trace_add("write", lambda *_: self.root.after_idle(refresh_prompt))

        # Кнопки внизу (фиксированные, всегда видны)
        bottom_frame = ttk.Frame(dialog)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(5, 15))

        status_lbl = ttk.Label(bottom_frame, text="", foreground="#2a7d2a")
        status_lbl.pack(side=tk.BOTTOM, anchor="w", pady=(3, 0))

        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X)

        def copy_prompt():
            dialog.clipboard_clear()
            dialog.clipboard_append(prompt_text.get("1.0", tk.END).strip())
            status_lbl.config(text="✓ Скопировано в буфер обмена!")

        ttk.Button(btn_frame, text="Копировать", style="Green.TButton", command=copy_prompt).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

        # Промпт (заполняет оставшееся пространство)
        prompt_frame = ttk.Frame(dialog)
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 5))

        prompt_text = tk.Text(prompt_frame, wrap=tk.WORD, font=("Consolas", 9))
        p_scroll = ttk.Scrollbar(prompt_frame, orient=tk.VERTICAL, command=prompt_text.yview)
        prompt_text.configure(yscrollcommand=p_scroll.set)
        prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        p_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def build_prompt():
            parts = []
            active_cats = []
            for cat in CATEGORIES:
                n = cat_vars[cat].get()
                if n > 0:
                    parts.append(f"- {cat}: {n} вопросов")
                    active_cats.append(cat)
            counts_block = "\n".join(parts) if parts else "- (не выбрано)"

            diff = difficulty_var.get()

            # Динамический шаблон — только выбранные категории
            example_refs = {
                "Ветхий Завет": "(Быт. 1:1)",
                "Новый Завет": "(Мф. 4:19)",
                "Визуальные подсказки": "(Быт. 6:14)",
                "Общие": "(Ин. 3:16)",
            }
            template_lines = []
            for cat in active_cats:
                ref = example_refs.get(cat, "")
                template_lines.append(f"\n{cat}")
                template_lines.append(f"ОТВЕТ: подсказка {ref}")
            template_block = "\n".join(template_lines) if template_lines else "\n(нет категорий)"

            # Правило про визуальные подсказки только если категория выбрана
            visual_rule = ""
            if "Визуальные подсказки" in active_cats:
                visual_rule = "Категория \"Визуальные подсказки\" — ответ описывает предмет/символ, который можно нарисовать.\n"

            # Описание сложности
            if diff == 1:
                diff_block = (
                    "Уровень сложности: 1 (лёгкий).\n"
                    "Подсказки должны быть максимально простыми и очевидными. "
                    "Ребёнок сразу должен понять ответ из подсказки.\n"
                    "Пример: РАДУГА: Какой знак завета Бог поставил на небе после потопа? (Быт. 9:13)\n"
                    "Пример: НОЙ: Кто построил ковчег, чтобы спастись от потопа? (Быт. 6:14)\n"
                )
            elif diff == 2:
                diff_block = (
                    "Уровень сложности: 2 (средний).\n"
                    "Подсказки требуют размышления, но логически ведут к ответу.\n"
                    "Пример: РАДУГА: Знамение завета Бога с Ноем, появляющееся в облаке (Быт. 9:13)\n"
                    "Пример: НОЙ: Праведник, которому Бог повелел взять в ковчег каждой твари по паре (Быт. 7:2)\n"
                )
            else:
                diff_block = (
                    "Уровень сложности: 3 (сложный).\n"
                    "Подсказки завуалированные — не называют ответ прямо, "
                    "а описывают его через контекст, метафору или косвенный признак.\n"
                    "Пример: РАДУГА: «Я полагаю дугу Мою в облаке» — о каком знамении речь? (Быт. 9:13)\n"
                    "Пример: НОЙ: Единственный в своём поколении, кого Бог назвал праведным (Быт. 7:1)\n"
                )

            theme = theme_var.get().strip()
            theme_block = ""
            if theme:
                theme_block = (
                    f"\nТема кроссворда: {theme}.\n"
                    "Все вопросы и ответы должны быть связаны с этой темой.\n"
                )

            return (
                "Сгенерируй набор вопросов для кроссворда воскресной школы.\n"
                f"{theme_block}"
                "\n"
                "Категории и количество:\n"
                f"{counts_block}\n"
                "\n"
                f"{diff_block}\n"
                "ВАЖНО: Генерируй вопросы ТОЛЬКО для перечисленных выше категорий. "
                "Категории с 0 вопросов НЕ включай в ответ.\n"
                "\n"
                "Формат вывода — простой текст, строго по шаблону:\n"
                f"{template_block}\n"
                "\n"
                "Правила:\n"
                "1. ОТВЕТ — одно слово, ЗАГЛАВНЫМИ буквами, только русские буквы (без пробелов, дефисов, цифр). "
                "Слово должно быть полным и грамматически правильным (именительный падеж, единственное число). "
                "Например: ПАВЕЛ (не ПАВЛ), МОИСЕЙ (не МОИСЕ).\n"
                "2. Подсказка НЕ ДОЛЖНА содержать слово-ответ ни в какой форме (однокоренные слова, падежи, "
                "склонения тоже запрещены). Плохо: 'ВЕРА: праведный верою жив будет' (есть 'верою'). "
                "Плохо: 'ГРЕХ: смерть через грех' (есть 'грех'). "
                "Хорошо: 'ВЕРА: Без неё невозможно угодить Богу (Евр. 11:6)'. "
                "Хорошо: 'ГРЕХ: Что вошло в мир через одного человека и принесло смерть всем? (Рим. 5:12)'.\n"
                "3. Подсказка должна ЛОГИЧЕСКИ вести к ответу — прочитав подсказку, человек должен понять, "
                "ПОЧЕМУ ответ именно это слово. Подсказка может быть длинной (1–2 предложения), "
                "если это нужно для ясности.\n"
                "4. После подсказки в скобках укажи ссылку на конкретный стих Библии: (Быт. 6:14) или (Мф. 4:19).\n"
                "5. Каждая категория начинается с заголовка на отдельной строке.\n"
                "6. Ответы должны быть ТОЛЬКО на русском языке.\n"
                f"{'7. ' + visual_rule if visual_rule else ''}"
                f"{'8' if visual_rule else '7'}. Ответы должны быть от 3 до 15 букв.\n"
                f"{'9' if visual_rule else '8'}. Не повторяй ответы.\n"
                f"{'10' if visual_rule else '9'}. Вопросы должны быть подходящими для детей воскресной школы.\n"
                f"{'11' if visual_rule else '10'}. Используй ТОЛЬКО канонические книги Синодального перевода Библии (66 книг). "
                "Неканонические/второканонические книги не использовать.\n"
                f"{'12' if visual_rule else '11'}. Если в подсказке упоминается библейская фраза или цитата — "
                "приводи её ТОЧНО по Синодальному переводу, дословно. "
                "Не пересказывай и не искажай текст Писания.\n"
                f"{'13' if visual_rule else '12'}. Проверяй правописание имён собственных: "
                "Моисей, Авраам, Павел, Пётр, Иаков, Елисей, Иезекииль и т.д.\n"
                f"{'14' if visual_rule else '13'}. Перед выводом проверь каждую подсказку: "
                "если в ней есть слово-ответ или его однокоренная форма — перепиши подсказку.\n"
                "\n"
                "Выведи только вопросы в указанном формате, без пояснений."
            )

        def refresh_prompt():
            prompt_text.delete("1.0", tk.END)
            prompt_text.insert("1.0", build_prompt())

        refresh_prompt()

    def _clear_image(self) -> None:
        """Очистка поля картинки."""
        self.entry_image.delete(0, tk.END)

    def _browse_image(self) -> None:
        """Выбор файла картинки."""
        path = filedialog.askopenfilename(
            title="Выберите картинку",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")],
        )
        if path:
            self.entry_image.delete(0, tk.END)
            self.entry_image.insert(0, path)

    def _add_question(self) -> None:
        """Добавляет вопрос в список."""
        answer = self.entry_answer.get().strip()
        hint = self.entry_hint.get().strip()
        category = self.combo_category.get()
        image = self.entry_image.get().strip() or None

        if not answer:
            messagebox.showwarning("Внимание", "Введите ответ (слово).")
            return
        if not hint:
            messagebox.showwarning("Внимание", "Введите подсказку.")
            return

        # Проверка: только буквы
        clean = answer.upper().replace("Ё", "Е")
        if not all(ch.isalpha() for ch in clean):
            messagebox.showwarning("Внимание", "Ответ должен содержать только буквы.")
            return

        q = Question(answer=answer, hint=hint, image_path=image, category=category)
        self.questions.append(q)
        self._refresh_tree()

        # Очищаем поля
        self.entry_answer.delete(0, tk.END)
        self.entry_hint.delete(0, tk.END)
        self.entry_image.delete(0, tk.END)
        self.entry_answer.focus()

    def _delete_question(self) -> None:
        """Удаляет выбранный вопрос."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Информация", "Выберите вопрос для удаления.")
            return
        idx = self.tree.index(sel[0])
        self.questions.pop(idx)
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        """Обновляет таблицу вопросов."""
        self.tree.delete(*self.tree.get_children())
        for i, q in enumerate(self.questions):
            cw_nums = self._cw_numbers.get(i, [])
            cw_str = ",".join(str(n) for n in cw_nums) if cw_nums else ""
            img_str = "📷" if q.image_path else ""
            self.tree.insert("", tk.END, values=(
                i + 1, cw_str, q.answer, q.hint, q.category, img_str
            ))

    def _save_questions(self) -> None:
        """Сохраняет вопросы в файл."""
        if not self.questions:
            messagebox.showinfo("Информация", "Нет вопросов для сохранения.")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить набор вопросов",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            save_questions(self.questions, path)
            messagebox.showinfo("Готово", f"Сохранено {len(self.questions)} вопросов.")

    def _load_questions(self) -> None:
        """Загружает вопросы из файла."""
        path = filedialog.askopenfilename(
            title="Загрузить набор вопросов",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            loaded = load_questions(path)
            if loaded:
                self.questions = loaded
                self._refresh_tree()
                self.status_var.set(f"Загружено {len(loaded)} вопросов.")
            else:
                messagebox.showwarning("Внимание", "Файл пуст или повреждён.")

    def _load_demo(self) -> None:
        """Загружает демо-набор вопросов."""
        demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_questions.json")
        if os.path.exists(demo_path):
            loaded = load_questions(demo_path)
            if loaded:
                self.questions = loaded
                self._refresh_tree()
                self.status_var.set(f"Загружен демо-набор: {len(loaded)} вопросов.")
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить демо-набор.")
        else:
            messagebox.showwarning("Внимание", f"Файл demo_questions.json не найден.")

    def _on_type_changed(self, event=None) -> None:
        """Обработка смены типа кроссворда в комбобоксе."""
        name = self.puzzle_type_var.get()
        for label, code in PUZZLE_TYPES:
            if label == name:
                self._selected_type_code = code
                return
        self._selected_type_code = "classic"

    def _generate(self) -> None:
        """Генерирует кроссворд из текущих вопросов."""
        if not self.questions:
            messagebox.showinfo("Информация", "Добавьте хотя бы один вопрос.")
            return

        title = self.entry_title.get().strip() or "Кроссворд"
        orientation = self.orientation.get()

        # Определяем тип
        ptype = getattr(self, '_selected_type_code', 'classic')
        if ptype == "classic":
            self.crossword = self.engine.generate(self.questions, title=title,
                                                  orientation=orientation)
        elif ptype == "filword":
            self.crossword = generate_filword(self.questions, title=title)
        elif ptype == "crisscross":
            self.crossword = generate_crisscross(self.questions, title=title,
                                                 orientation=orientation)
        elif ptype == "codeword":
            self.crossword = generate_codeword(self.questions, title=title,
                                               orientation=orientation)
        elif ptype == "scanword":
            self.crossword = generate_scanword(self.questions, title=title,
                                               orientation=orientation)
        elif ptype == "circular":
            self.crossword = generate_circular(self.questions, title=title)
        elif ptype == "honeycomb":
            self.crossword = generate_honeycomb(self.questions, title=title)
        elif ptype == "japanese":
            self.crossword = generate_japanese(self.questions, title=title,
                                               orientation=orientation)
        else:
            self.crossword = self.engine.generate(self.questions, title=title,
                                                  orientation=orientation)

        placed = len(self.crossword.words)
        unplaced = len(self.crossword.unplaced)
        status = f"Готово! Размещено слов: {placed}"
        if unplaced:
            status += f", не удалось разместить: {unplaced}"
            names = ", ".join(q.answer for q in self.crossword.unplaced)
            messagebox.showwarning(
                "Не все слова размещены",
                f"Не удалось разместить: {names}\n\n"
                "Попробуйте изменить набор слов или сгенерировать заново.",
            )
        # Обновляем маппинг номеров кроссворда
        self._cw_numbers.clear()
        self._cell_map.clear()
        self._question_cells.clear()

        word_cells_map = self.crossword.extra_data.get("word_cells", {})

        for w in self.crossword.words:
            for qi, q in enumerate(self.questions):
                if q is w.question:
                    self._cw_numbers.setdefault(qi, []).append(w.number)
                    # Для типов с word_cells (филворд, сотовый, циклический)
                    if w.number in word_cells_map:
                        cells_list = word_cells_map[w.number]
                    else:
                        cells_list = []
                        for ci in range(len(w.question.answer)):
                            if w.direction == 'across':
                                cell_pos = (w.row, w.col + ci)
                            else:
                                cell_pos = (w.row + ci, w.col)
                            cells_list.append(cell_pos)
                    for cell_pos in cells_list:
                        self._cell_map[cell_pos] = qi
                    self._question_cells.setdefault(qi, []).extend(cells_list)
                    break

        self.status_var.set(status)
        self._refresh_tree()
        self._redraw()

    def _redraw(self, highlight_qi: int | None = None) -> None:
        """Перерисовывает кроссворд на Canvas."""
        self.canvas.delete("all")
        if not self.crossword or not self.crossword.words:
            return

        cw = self.crossword
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w < 50 or canvas_h < 50:
            self.root.after(100, lambda: self._redraw(highlight_qi))
            return

        ptype = cw.puzzle_type
        if ptype == "circular":
            self._redraw_circular(highlight_qi, canvas_w, canvas_h)
        elif ptype == "honeycomb":
            self._redraw_honeycomb(highlight_qi, canvas_w, canvas_h)
        elif ptype == "japanese":
            self._redraw_japanese(highlight_qi, canvas_w, canvas_h)
        else:
            self._redraw_grid(highlight_qi, canvas_w, canvas_h)

    def _redraw_grid(self, highlight_qi, canvas_w, canvas_h) -> None:
        """Рисует сеточные типы: classic, filword, crisscross, codeword, scanword."""
        cw = self.crossword
        ptype = cw.puzzle_type

        pad = 30
        user_cell = self.cell_size_var.get()
        cell = user_cell
        cell = max(cell, 12)

        total_w = cw.cols * cell + 2 * pad
        total_h = cw.rows * cell + 2 * pad
        ox = pad
        oy = pad

        # Если сетка меньше canvas — центрируем
        if total_w < canvas_w:
            ox = (canvas_w - cw.cols * cell) / 2
            total_w = canvas_w
        if total_h < canvas_h:
            oy = (canvas_h - cw.rows * cell) / 2
            total_h = canvas_h

        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

        self._grid_params = {"ox": ox, "oy": oy, "cell": cell,
                             "rows": cw.rows, "cols": cw.cols}

        highlight_cells = set()
        if highlight_qi is not None:
            highlight_cells = set(self._question_cells.get(highlight_qi, []))

        # Номера по позициям
        numbers: dict[tuple[int, int], int] = {}
        for w in cw.words:
            key = (w.row, w.col)
            if key not in numbers:
                numbers[key] = w.number

        # Данные сканворда
        clue_cells = {}       # (row, col) -> [(hint, arrow, span_r, span_c)]
        clue_skip = set()     # ячейки, которые являются продолжением span-блока
        if ptype == "scanword":
            for item in cw.extra_data.get("clue_cells", []):
                cr, cc, hint, arrow = item[0], item[1], item[2], item[3]
                sr = item[4] if len(item) > 4 else 1
                sc = item[5] if len(item) > 5 else 1
                t_r = item[6] if len(item) > 6 else None
                t_c = item[7] if len(item) > 7 else None
                clue_cells.setdefault((cr, cc), []).append((hint, arrow, sr, sc, t_r, t_c))
                # Помечаем все ячейки блока кроме первой как skip
                for dr in range(sr):
                    for dc in range(sc):
                        if dr != 0 or dc != 0:
                            clue_skip.add((cr + dr, cc + dc))

        # Данные кейворда
        letter_map = cw.extra_data.get("letter_map", {})
        hint_letters = cw.extra_data.get("hint_letters", [])

        # Отложенные стрелки сканворда (рисуем поверх всех ячеек)
        deferred_arrows = []

        for row in range(cw.rows):
            for col in range(cw.cols):
                x1 = ox + col * cell
                y1 = oy + row * cell
                x2 = x1 + cell
                y2 = y1 + cell

                ch = cw.grid[row][col]

                # Сканворд: пропускаем ячейки из продолжения span
                if ptype == "scanword" and (row, col) in clue_skip:
                    continue

                # Сканворд: ячейка-подсказка (с возможным span)
                if ptype == "scanword" and (row, col) in clue_cells:
                    hints_list = clue_cells[(row, col)]
                    hint, arrow, sr, sc, t_r, t_c = hints_list[0]
                    bw = sc * cell
                    bh = sr * cell
                    bx2 = x1 + bw
                    by2 = y1 + bh

                    self.canvas.create_rectangle(x1, y1, bx2, by2,
                                                 fill=ACCENT_DARK, outline=CELL_BORDER)

                    # Авто-масштабирование: уменьшаем шрифт пока ВЕСЬ текст не влезет
                    import tkinter.font as tkfont
                    pad = 4
                    avail_w = bw - pad * 2
                    avail_h = bh - pad * 2
                    best_lines = [hint]
                    best_fs = 3

                    for try_fs in range(max(3, int(cell * 0.30)), 2, -1):
                        fobj = tkfont.Font(family="Segoe UI", size=try_fs)
                        line_h = fobj.metrics("linespace")
                        max_lines = max(1, int(avail_h / line_h))

                        # Разбиваем на строки с реальным измерением ширины
                        words = hint.split()
                        lines = []
                        cur = ""
                        for w_txt in words:
                            test = (cur + " " + w_txt).strip() if cur else w_txt
                            if fobj.measure(test) <= avail_w:
                                cur = test
                            else:
                                if cur:
                                    lines.append(cur)
                                cur = w_txt
                                # Если одно слово шире блока — принудительно разрываем
                                while fobj.measure(cur) > avail_w and len(cur) > 1:
                                    for k in range(len(cur) - 1, 0, -1):
                                        if fobj.measure(cur[:k]) <= avail_w:
                                            lines.append(cur[:k])
                                            cur = cur[k:]
                                            break
                                    else:
                                        break
                        if cur:
                            lines.append(cur)

                        if len(lines) <= max_lines:
                            best_lines = lines
                            best_fs = try_fs
                            break

                    fnt = ("Segoe UI", best_fs)
                    display_text = "\n".join(best_lines)
                    self.canvas.create_text(
                        x1 + bw / 2, y1 + bh / 2,
                        text=display_text, font=fnt,
                        fill="white", anchor="center",
                        justify="center"
                    )

                    # Запоминаем стрелку для отрисовки поверх всего
                    if t_r is not None and t_c is not None:
                        deferred_arrows.append((x1, y1, bw, bh, arrow, t_r, t_c))
                    continue

                # Тёмные блоки и пустые ячейки
                if not ch or ch == '#CLUE#':
                    if ptype in ("filword", "honeycomb") and not ch:
                        self.canvas.create_rectangle(x1, y1, x2, y2,
                                                     fill=CELL_EMPTY, outline="#ddd")
                    continue
                if ch == '#BLOCK#':
                    if ptype == "scanword":
                        self.canvas.create_rectangle(x1, y1, x2, y2,
                                                     fill=ACCENT_DARK, outline=CELL_BORDER)
                    continue

                # Подсветка
                if (row, col) in highlight_cells:
                    fill = HIGHLIGHT_FILL
                    border = HIGHLIGHT_BORDER
                    border_w = 2
                else:
                    fill = CELL_FILLED
                    border = CELL_BORDER
                    border_w = 1

                # Филворд: все клетки одинаковые, с рамкой
                if ptype == "filword":
                    self.canvas.create_rectangle(x1, y1, x2, y2,
                                                 fill=fill, outline=border, width=border_w)
                    letter_size = max(8, int(cell * 0.45))
                    self.canvas.create_text(x1 + cell / 2, y1 + cell / 2,
                                            text=ch, font=("Segoe UI", letter_size),
                                            fill=LETTER_COLOR)
                    continue

                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             fill=fill, outline=border, width=border_w)

                # Номер (не для крисс-кросса, кейворда, сканворда)
                if ptype not in ("crisscross", "codeword", "scanword") and (row, col) in numbers:
                    num_size = max(7, int(cell * 0.25))
                    self.canvas.create_text(
                        x1 + 3, y1 + 2,
                        text=str(numbers[(row, col)]),
                        anchor="nw",
                        font=("Segoe UI", num_size, "bold"),
                        fill=NUMBER_COLOR,
                    )

                # Кейворд: номер буквы вместо самой буквы
                if ptype == "codeword":
                    num_val = letter_map.get(ch, 0)
                    num_size = max(7, int(cell * 0.22))
                    self.canvas.create_text(x1 + 3, y1 + 2,
                                            text=str(num_val), anchor="nw",
                                            font=("Segoe UI", num_size),
                                            fill=ACCENT_DARK)
                    # Показываем букву только для подсказок или при show_answers
                    if self.show_answers.get() or ch in hint_letters:
                        letter_size = max(8, int(cell * 0.4))
                        self.canvas.create_text(x1 + cell / 2, y1 + cell / 2 + 3,
                                                text=ch, font=("Segoe UI", letter_size),
                                                fill=LETTER_COLOR if self.show_answers.get()
                                                else WARM_ACCENT)
                    continue

                # Буква (classic, crisscross, scanword)
                if self.show_answers.get():
                    letter_size = max(9, int(cell * 0.45))
                    self.canvas.create_text(
                        x1 + cell / 2, y1 + cell / 2 + 2,
                        text=ch,
                        font=("Segoe UI", letter_size),
                        fill=LETTER_COLOR,
                    )

        # Сканворд: рисуем стрелки ПОВЕРХ всех ячеек
        if ptype == "scanword" and deferred_arrows:
            aw = max(3, int(cell * 0.12))
            lw = max(1, int(cell * 0.04))
            ac = GOLD_ACCENT

            # Группируем стрелки по целевой ячейке для устранения наложений
            from collections import defaultdict
            _target_groups = defaultdict(list)
            for _i, _a in enumerate(deferred_arrows):
                _target_groups[(_a[5], _a[6])].append(_i)

            # Вычисляем смещения: перпендикулярно направлению стрелки
            _arrow_off = {}
            for _key, _idxs in _target_groups.items():
                _n = len(_idxs)
                for _j, _idx in enumerate(_idxs):
                    if _n <= 1:
                        _arrow_off[_idx] = (0, 0)
                    else:
                        _arr = deferred_arrows[_idx][4]
                        _pos = _j - (_n - 1) / 2
                        _sp = cell * 0.15
                        if _arr in ('right', 'right_down'):
                            _arrow_off[_idx] = (0, _pos * _sp)
                        else:
                            _arrow_off[_idx] = (_pos * _sp, 0)

            for _i, (ax1, ay1, abw, abh, arrow, at_r, at_c) in enumerate(deferred_arrows):
                abx2 = ax1 + abw
                aby2 = ay1 + abh
                # Края целевой ячейки
                t_left = ox + at_c * cell
                t_top = oy + at_r * cell
                t_cx = t_left + cell / 2
                t_cy = t_top + cell / 2
                # Смещение для избежания наложений
                _ox, _oy = _arrow_off.get(_i, (0, 0))
                t_cx += _ox
                t_cy += _oy

                if arrow == 'right':
                    # → из правого края блока в целевую ячейку
                    sx = abx2
                    sy = ay1 + abh / 2
                    self.canvas.create_line(sx, sy, t_cx - aw, t_cy, fill=ac, width=lw)
                    self.canvas.create_polygon(
                        t_cx - aw, t_cy - aw, t_cx, t_cy, t_cx - aw, t_cy + aw, fill=ac)
                elif arrow == 'down':
                    # ↓ из нижнего края блока в целевую ячейку
                    sx = ax1 + abw / 2
                    sy = aby2
                    self.canvas.create_line(sx, sy, t_cx, t_cy - aw, fill=ac, width=lw)
                    self.canvas.create_polygon(
                        t_cx - aw, t_cy - aw, t_cx, t_cy, t_cx + aw, t_cy - aw, fill=ac)
                elif arrow == 'down_right':
                    # ↓→ : вниз из блока, изгиб ВНУТРИ целевой ячейки, вправо
                    sx = abx2 - abw * 0.3
                    sy = aby2
                    bend_x = t_left + cell * 0.2
                    bend_y = t_cy
                    self.canvas.create_line(sx, sy, bend_x, bend_y, fill=ac, width=lw)
                    self.canvas.create_line(bend_x, bend_y, t_cx - aw, t_cy, fill=ac, width=lw)
                    self.canvas.create_polygon(
                        t_cx - aw, t_cy - aw, t_cx, t_cy, t_cx - aw, t_cy + aw, fill=ac)
                elif arrow == 'right_down':
                    # →↓ : вправо из блока, изгиб ВНУТРИ целевой ячейки, вниз
                    sx = abx2
                    sy = aby2 - abh * 0.3
                    bend_x = t_cx
                    bend_y = t_top + cell * 0.2
                    self.canvas.create_line(sx, sy, bend_x, bend_y, fill=ac, width=lw)
                    self.canvas.create_line(bend_x, bend_y, t_cx, t_cy - aw, fill=ac, width=lw)
                    self.canvas.create_polygon(
                        t_cx - aw, t_cy - aw, t_cx, t_cy, t_cx + aw, t_cy - aw, fill=ac)

        # Крисс-кросс: список слов справа
        if ptype == "crisscross":
            words_by_len = cw.extra_data.get("words_by_length", {})
            tx = ox + cw.cols * cell + 15
            ty = oy
            fs = max(8, int(cell * 0.35))
            self.canvas.create_text(tx, ty, text="Слова:", anchor="nw",
                                    font=("Segoe UI", fs + 1, "bold"), fill=ACCENT_DARK)
            ty += fs + 8
            for length in sorted(words_by_len.keys()):
                self.canvas.create_text(tx, ty, text=f"— {length} букв:",
                                        anchor="nw", font=("Segoe UI", fs, "bold"),
                                        fill=WARM_ACCENT)
                ty += fs + 4
                for w in sorted(words_by_len[length]):
                    self.canvas.create_text(tx + 10, ty, text=w,
                                            anchor="nw", font=("Segoe UI", fs),
                                            fill=LETTER_COLOR)
                    ty += fs + 2

        # Кейворд: таблица подсказок снизу
        if ptype == "codeword" and hint_letters:
            tx = ox
            ty = oy + cw.rows * cell + 10
            fs = max(8, int(cell * 0.3))
            self.canvas.create_text(tx, ty, text="Подсказки:",
                                    anchor="nw", font=("Segoe UI", fs + 1, "bold"),
                                    fill=ACCENT_DARK)
            tx += 80
            for ch in hint_letters:
                num = letter_map.get(ch, "?")
                self.canvas.create_text(tx, ty, text=f"{num}={ch}",
                                        anchor="nw", font=("Segoe UI", fs + 1, "bold"),
                                        fill=WARM_ACCENT)
                tx += 50

    def _redraw_circular(self, highlight_qi, canvas_w, canvas_h) -> None:
        """Рисует циклический (круглый) кроссворд."""
        cw = self.crossword
        n_rings = cw.extra_data.get("n_rings", 4)
        n_sectors = cw.extra_data.get("n_sectors", 12)
        word_cells = cw.extra_data.get("word_cells", {})

        highlight_cells = set()
        if highlight_qi is not None:
            highlight_cells = set(self._question_cells.get(highlight_qi, []))

        cx = canvas_w / 2
        cy = canvas_h / 2
        max_radius = min(canvas_w, canvas_h) / 2 - 30
        ring_width = max_radius / (n_rings + 1)
        inner_r = ring_width  # пустой центр

        # Параметры для клика
        self._grid_params = {"type": "circular", "cx": cx, "cy": cy,
                             "inner_r": inner_r, "ring_width": ring_width,
                             "n_rings": n_rings, "n_sectors": n_sectors,
                             "rows": n_rings, "cols": n_sectors}

        # Номера
        numbers: dict[tuple[int, int], int] = {}
        for w in cw.words:
            key = (w.row, w.col)
            if key not in numbers:
                numbers[key] = w.number

        # Рисуем кольца (концентрические)
        for ring in range(n_rings):
            r_inner = inner_r + ring * ring_width
            r_outer = r_inner + ring_width

            for sec in range(n_sectors):
                angle_start = sec * (360 / n_sectors) - 90  # начало с верха
                angle_extent = 360 / n_sectors

                ch = cw.grid[ring][sec]
                is_highlight = (ring, sec) in highlight_cells

                if ch:
                    fill = HIGHLIGHT_FILL if is_highlight else CELL_FILLED
                    outline = HIGHLIGHT_BORDER if is_highlight else CELL_BORDER
                else:
                    fill = CELL_EMPTY
                    outline = "#ccc"

                # Дуга (внешняя)
                self.canvas.create_arc(
                    cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                    start=angle_start, extent=angle_extent,
                    outline=outline, fill=fill, width=1, style="pieslice"
                )
                # Закрашиваем внутреннюю часть (создаём "кольцо")
                if ring > 0 or True:
                    self.canvas.create_arc(
                        cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
                        start=angle_start, extent=angle_extent,
                        outline="", fill="#fdf8f3", width=0, style="pieslice"
                    )

                # Буква/номер
                if ch:
                    mid_r = (r_inner + r_outer) / 2
                    mid_angle = math.radians(angle_start + angle_extent / 2)
                    tx = cx + mid_r * math.cos(mid_angle)
                    ty = cy - mid_r * math.sin(mid_angle)

                    if (ring, sec) in numbers:
                        ns = max(6, int(ring_width * 0.2))
                        self.canvas.create_text(
                            tx - ring_width * 0.2, ty - ring_width * 0.2,
                            text=str(numbers[(ring, sec)]),
                            font=("Segoe UI", ns, "bold"), fill=NUMBER_COLOR)

                    if self.show_answers.get():
                        fs = max(7, int(ring_width * 0.4))
                        self.canvas.create_text(tx, ty, text=ch,
                                                font=("Segoe UI", fs), fill=LETTER_COLOR)

        # Центральный круг (пустой)
        self.canvas.create_oval(cx - inner_r, cy - inner_r,
                                cx + inner_r, cy + inner_r,
                                fill="#fdf8f3", outline=CELL_BORDER)

    def _redraw_honeycomb(self, highlight_qi, canvas_w, canvas_h) -> None:
        """Рисует сотовый кроссворд (гексагональная сетка)."""
        cw = self.crossword

        highlight_cells = set()
        if highlight_qi is not None:
            highlight_cells = set(self._question_cells.get(highlight_qi, []))

        # Размер гексагона
        pad = 30
        hex_w = (canvas_w - 2 * pad) / (cw.cols + 0.5)
        hex_h = (canvas_h - 2 * pad) / (cw.rows * 0.75 + 0.25)
        hex_size = min(hex_w / math.sqrt(3), hex_h / 2, self.cell_size_var.get() * 0.6)
        hex_size = max(hex_size, 10)

        self._grid_params = {"type": "honeycomb", "hex_size": hex_size,
                             "rows": cw.rows, "cols": cw.cols,
                             "pad": pad, "canvas_w": canvas_w}

        for row in range(cw.rows):
            for col in range(cw.cols):
                ch = cw.grid[row][col]
                if not ch:
                    continue

                # Центр гексагона (offset координаты, odd-r)
                x_offset = (hex_size * math.sqrt(3) * 0.5) if row % 2 else 0
                hx = pad + col * hex_size * math.sqrt(3) + x_offset + hex_size
                hy = pad + row * hex_size * 1.5 + hex_size

                is_highlight = (row, col) in highlight_cells
                fill = HIGHLIGHT_FILL if is_highlight else CELL_FILLED
                outline = HIGHLIGHT_BORDER if is_highlight else CELL_BORDER

                # Рисуем 6-угольник
                points = []
                for i in range(6):
                    angle = math.radians(60 * i - 30)
                    px = hx + hex_size * math.cos(angle)
                    py = hy + hex_size * math.sin(angle)
                    points.extend([px, py])

                self.canvas.create_polygon(points, fill=fill, outline=outline, width=1)

                # Буква
                fs = max(7, int(hex_size * 0.55))
                self.canvas.create_text(hx, hy, text=ch,
                                        font=("Segoe UI", fs), fill=LETTER_COLOR)

    def _redraw_japanese(self, highlight_qi, canvas_w, canvas_h) -> None:
        """Рисует японский кроссворд (нонограмму)."""
        cw = self.crossword
        row_clues = cw.extra_data.get("row_clues", [])
        col_clues = cw.extra_data.get("col_clues", [])

        # Место для подсказок слева и сверху
        max_row_clue_len = max((len(rc) for rc in row_clues), default=1)
        max_col_clue_len = max((len(cc) for cc in col_clues), default=1)

        clue_w = max_row_clue_len * 18 + 10
        clue_h = max_col_clue_len * 16 + 10

        pad = 10
        avail_w = canvas_w - clue_w - 2 * pad
        avail_h = canvas_h - clue_h - 2 * pad
        cell = min(avail_w / max(cw.cols, 1), avail_h / max(cw.rows, 1))
        cell = min(cell, self.cell_size_var.get())
        cell = max(cell, 8)

        ox = clue_w + pad
        oy = clue_h + pad

        self._grid_params = {"ox": ox, "oy": oy, "cell": cell,
                             "rows": cw.rows, "cols": cw.cols}

        highlight_cells = set()
        if highlight_qi is not None:
            highlight_cells = set(self._question_cells.get(highlight_qi, []))

        # Рисуем подсказки по строкам (слева)
        fs = max(6, int(cell * 0.4))
        for r, clues in enumerate(row_clues):
            y_mid = oy + r * cell + cell / 2
            clue_text = "  ".join(str(c) for c in clues)
            self.canvas.create_text(ox - 5, y_mid, text=clue_text,
                                    anchor="e", font=("Consolas", fs), fill=ACCENT_DARK)

        # Подсказки по столбцам (сверху)
        for c, clues in enumerate(col_clues):
            x_mid = ox + c * cell + cell / 2
            for ci, val in enumerate(clues):
                y_pos = oy - (len(clues) - ci) * (fs + 4)
                self.canvas.create_text(x_mid, y_pos, text=str(val),
                                        font=("Consolas", fs), fill=ACCENT_DARK)

        # Рисуем сетку
        for row in range(cw.rows):
            for col in range(cw.cols):
                x1 = ox + col * cell
                y1 = oy + row * cell
                x2 = x1 + cell
                y2 = y1 + cell

                ch = cw.grid[row][col]
                is_highlight = (row, col) in highlight_cells

                if ch:
                    if self.show_answers.get():
                        fill = HIGHLIGHT_FILL if is_highlight else ACCENT
                    else:
                        fill = HIGHLIGHT_FILL if is_highlight else "#ddd"
                else:
                    fill = CELL_FILLED

                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             fill=fill, outline=CELL_BORDER, width=0.5)

                # При включённых ответах показываем заполненные клетки цветом
                if self.show_answers.get() and ch:
                    letter_size = max(6, int(cell * 0.4))
                    self.canvas.create_text(x1 + cell / 2, y1 + cell / 2,
                                            text=ch, font=("Segoe UI", letter_size),
                                            fill="white")

    def _export_pdf(self, with_answers: bool) -> None:
        """Экспортирует кроссворд в PDF."""
        if not self.crossword or not self.crossword.words:
            messagebox.showinfo("Информация", "Сначала сгенерируйте кроссворд.")
            return

        suffix = "ответы" if with_answers else "пустой"
        path = filedialog.asksaveasfilename(
            title=f"Сохранить PDF ({suffix})",
            defaultextension=".pdf",
            initialfile=f"crossword_{suffix}.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        try:
            export_pdf(self.crossword, path, show_answers=with_answers, cell_size=self.cell_size_var.get())
            messagebox.showinfo("Готово", f"PDF сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать PDF:\n{e}")

    def _export_docx(self, with_answers: bool) -> None:
        """Экспортирует кроссворд в DOCX (Word)."""
        if not self.crossword or not self.crossword.words:
            messagebox.showinfo("Информация", "Сначала сгенерируйте кроссворд.")
            return

        suffix = "ответы" if with_answers else "пустой"
        path = filedialog.asksaveasfilename(
            title=f"Сохранить Word ({suffix})",
            defaultextension=".docx",
            initialfile=f"crossword_{suffix}.docx",
            filetypes=[("Word", "*.docx")],
        )
        if not path:
            return

        try:
            export_docx(self.crossword, path, show_answers=with_answers, cell_size_px=self.cell_size_var.get())
            messagebox.showinfo("Готово", f"Word-документ сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать DOCX:\n{e}")

    def _export_svg(self, full: bool) -> None:
        """Экспортирует кроссворд в SVG (векторный формат для CorelDRAW/Illustrator)."""
        if not self.crossword or not self.crossword.words:
            messagebox.showinfo("Информация", "Сначала сгенерируйте кроссворд.")
            return

        label = "полный" if full else "сетка"
        path = filedialog.asksaveasfilename(
            title=f"Сохранить SVG ({label})",
            defaultextension=".svg",
            initialfile=f"crossword_{label}.svg",
            filetypes=[("SVG (вектор)", "*.svg")],
        )
        if not path:
            return

        try:
            if full:
                export_svg_with_clues(
                    self.crossword, path, show_answers=self.show_answers.get(),
                    cell_size=self.cell_size_var.get()
                )
            else:
                export_svg(
                    self.crossword, path, show_answers=self.show_answers.get(),
                    cell_size=self.cell_size_var.get()
                )
            messagebox.showinfo("Готово", f"SVG сохранён:\n{path}\n\nОткрывается в CorelDRAW, Illustrator, Inkscape")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать SVG:\n{e}")

    def _export_png(self) -> None:
        """Экспортирует кроссворд в PNG с прозрачным фоном."""
        if not self.crossword or not self.crossword.words:
            messagebox.showinfo("Информация", "Сначала сгенерируйте кроссворд.")
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить PNG",
            defaultextension=".png",
            initialfile="crossword.png",
            filetypes=[("PNG (прозрачный фон)", "*.png")],
        )
        if not path:
            return

        try:
            export_png(self.crossword, path, show_answers=self.show_answers.get(),
                       cell_size=self.cell_size_var.get())
            messagebox.showinfo("Готово", f"PNG сохранён (прозрачный фон):\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать PNG:\n{e}")

    def _export_jpg(self) -> None:
        """Экспортирует кроссворд в JPG."""
        if not self.crossword or not self.crossword.words:
            messagebox.showinfo("Информация", "Сначала сгенерируйте кроссворд.")
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить JPG",
            defaultextension=".jpg",
            initialfile="crossword.jpg",
            filetypes=[("JPEG", "*.jpg *.jpeg")],
        )
        if not path:
            return

        try:
            export_jpg(self.crossword, path, show_answers=self.show_answers.get(),
                       cell_size=self.cell_size_var.get())
            messagebox.showinfo("Готово", f"JPG сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать JPG:\n{e}")

    # ========== Клик по кроссворду → выбор вопроса ==========

    def _on_canvas_click(self, event) -> None:
        """Клик по ячейке кроссворда — выбирает соответствующий вопрос в списке."""
        if not self._grid_params or not self.crossword:
            return

        gp = self._grid_params
        ox, oy, cell_size = gp["ox"], gp["oy"], gp["cell"]

        # Определяем строку/столбец
        col = int((event.x - ox) / cell_size)
        row = int((event.y - oy) / cell_size)

        if row < 0 or col < 0 or row >= gp["rows"] or col >= gp["cols"]:
            return

        # Ищем вопрос по ячейке
        qi = self._cell_map.get((row, col))
        if qi is not None:
            self._select_question_in_tree(qi)
            self._redraw(highlight_qi=qi)

    def _select_question_in_tree(self, question_index: int) -> None:
        """Выбирает вопрос в списке по индексу (ищет по колонке №)."""
        target_num = str(question_index + 1)
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and str(values[0]) == target_num:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                return

    # ========== Inline-редактирование в списке вопросов ==========

    def _on_tree_double_click(self, event) -> None:
        """Двойной клик по ячейке таблицы — открывает редактирование."""
        self._close_edit_widget()

        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item or not column:
            return

        col_idx = int(column.replace("#", "")) - 1
        col_name = self.tree["columns"][col_idx]

        # Редактируемые колонки: answer, hint, category, img
        if col_name not in ("answer", "hint", "category", "img"):
            return

        item_index = self.tree.index(item)
        if item_index >= len(self.questions):
            return

        q = self.questions[item_index]

        # Получаем координаты ячейки
        bbox = self.tree.bbox(item, column)
        if not bbox:
            return

        x, y, w, h = bbox

        if col_name == "img":
            # Если уже есть картинка — спросить: заменить или убрать
            if q.image_path:
                choice = messagebox.askyesnocancel(
                    "Картинка",
                    f"Текущая: {os.path.basename(q.image_path)}\n\n"
                    "Да — выбрать другую\n"
                    "Нет — убрать картинку\n"
                    "Отмена — ничего не делать",
                )
                if choice is True:
                    path = filedialog.askopenfilename(
                        title="Выберите картинку",
                        filetypes=[("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")],
                    )
                    if path:
                        q.image_path = path
                        self._refresh_tree()
                elif choice is False:
                    q.image_path = ""
                    self._refresh_tree()
            else:
                path = filedialog.askopenfilename(
                    title="Выберите картинку",
                    filetypes=[("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")],
                )
                if path:
                    q.image_path = path
                    self._refresh_tree()
            return

        if col_name == "category":
            # Combobox для категории
            combo = ttk.Combobox(self.tree, values=CATEGORIES, state="readonly")
            combo.set(q.category)
            combo.place(x=x, y=y, width=w, height=h)
            combo.focus_set()

            def on_select(e):
                q.category = combo.get()
                self._close_edit_widget()
                self._refresh_tree()

            combo.bind("<<ComboboxSelected>>", on_select)
            combo.bind("<Escape>", lambda e: self._close_edit_widget())
            combo.bind("<FocusOut>", lambda e: (
                setattr(q, "category", combo.get()),
                self._close_edit_widget(),
                self._refresh_tree(),
            ))
            self._edit_widget = combo
            return

        # Entry для answer и hint
        current_value = q.answer if col_name == "answer" else q.hint
        entry = ttk.Entry(self.tree)
        entry.insert(0, current_value)
        entry.place(x=x, y=y, width=max(w, 200), height=h)
        entry.select_range(0, tk.END)
        entry.focus_set()

        def on_confirm(e=None):
            new_val = entry.get().strip()
            if new_val:
                if col_name == "answer":
                    q.answer = new_val.upper()
                else:
                    q.hint = new_val
            self._close_edit_widget()
            self._refresh_tree()

        entry.bind("<Return>", on_confirm)
        entry.bind("<Escape>", lambda e: self._close_edit_widget())
        entry.bind("<FocusOut>", on_confirm)
        self._edit_widget = entry

    def _close_edit_widget(self) -> None:
        """Закрывает текущий виджет inline-редактирования."""
        if self._edit_widget:
            try:
                self._edit_widget.destroy()
            except Exception:
                pass
            self._edit_widget = None

    # ========== Выбор строки → подсветка в кроссворде ==========

    def _on_tree_select(self, event=None) -> None:
        """При выборе строки в списке — подсвечиваем слово в кроссворде."""
        if not self.crossword or not self.crossword.words:
            return

        sel = self.tree.selection()
        if not sel:
            self._redraw()
            return

        item_index = self.tree.index(sel[0])
        # item_index — индекс в текущем порядке дерева (может быть отсортировано)
        # Нужно получить реальный индекс вопроса из значения колонки "num"
        values = self.tree.item(sel[0], "values")
        try:
            qi = int(values[0]) - 1  # колонка "num" = порядковый номер вопроса (1-based)
        except (ValueError, IndexError):
            return

        self._redraw(highlight_qi=qi)

    # ========== Сортировка по столбцам ==========

    def _sort_by_column(self, col: str) -> None:
        """Сортирует Treeview по столбцу при клике на заголовок."""
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        items = [(self.tree.set(item, col), item) for item in self.tree.get_children()]

        # Пробуем числовую сортировку
        try:
            items.sort(key=lambda t: int(t[0]) if t[0] else 0, reverse=self._sort_reverse)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=self._sort_reverse)

        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)

        # Обновляем заголовки — показываем стрелку
        arrow = " ▼" if self._sort_reverse else " ▲"
        headers = {
            "num": "№", "cw_num": "Кр.№", "answer": "Ответ",
            "hint": "Подсказка", "category": "Категория", "img": "Картинка",
        }
        for c, text in headers.items():
            display = text + (arrow if c == col else "")
            self.tree.heading(c, text=display)

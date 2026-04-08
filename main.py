"""Точка входа — Генератор кроссвордов для воскресной школы."""

VERSION = "1.2.0"

import tkinter as tk
from app import CrosswordApp


def main():
    root = tk.Tk()
    CrosswordApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

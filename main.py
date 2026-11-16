import math
import time
import tkinter as tk
from tkinter import ttk

from game import Game, SIZE, TARGET
from high_score import load_high_score, save_high_score

BACKGROUND = "#f7f3ec"
TEXT = "#40372f"
MUTED = "#84786b"
BOARD = "#b7a99b"
EMPTY = "#cbbfb2"
CELL = 92
GAP = 10
PADDING = 12
WIDTH = PADDING * 2 + SIZE * CELL + (SIZE - 1) * GAP
COLORS = {
    2: "#eee5d8", 4: "#ead8b7", 8: "#edb277", 16: "#e99059",
    32: "#e37455", 64: "#d95842", 128: "#d6ac4b", 256: "#c79a37",
    512: "#af8427", 1024: "#977020", 2048: "#795618",
}


class GameWindow:
    def __init__(self, root):
        self.root = root
        self.game = Game()
        self.high_score = load_high_score()
        self.saved_high_score = self.high_score
        self.animation = None
        self.pending_direction = None
        root.title("2048 · Собери больше")
        root.configure(bg=BACKGROUND)
        root.resizable(False, False)
        style = ttk.Style(root)
        style.configure("NewGame.TButton", font=("TkDefaultFont", 12, "bold"),
                        padding=(14, 9))

        header = tk.Frame(root, bg=BACKGROUND)
        header.pack(fill="x", padx=28, pady=(24, 8))
        tk.Label(header, text="2048", font=("TkDefaultFont", 48, "bold"),
                 bg=BACKGROUND, fg=TEXT).pack(side="left")
        scores = tk.Frame(header, bg=BACKGROUND)
        scores.pack(side="right")
        self.score = self.score_card(scores, "СЧЁТ")
        self.record = self.score_card(scores, "РЕКОРД")

        toolbar = tk.Frame(root, bg=BACKGROUND)
        toolbar.pack(fill="x", padx=28, pady=(4, 18))
        tk.Label(toolbar, text="Объединяй. Достигай большего.",
                 bg=BACKGROUND, fg=MUTED,
                 font=("TkDefaultFont", 11)).pack(side="left")
        ttk.Button(toolbar, text="Новая игра", style="NewGame.TButton",
                   command=self.restart).pack(side="right")

        self.canvas = tk.Canvas(root, width=WIDTH, height=WIDTH,
                                bg=BACKGROUND, highlightthickness=0)
        self.canvas.pack(padx=28)
        self.rounded_rect(0, 0, WIDTH, WIDTH, 18, BOARD, "base")
        for row in range(SIZE):
            for col in range(SIZE):
                x, y = self.cell_position((row, col))
                self.rounded_rect(x, y, x + CELL, y + CELL, 10, EMPTY, "base")

        self.status = tk.Label(root, bg=BACKGROUND, fg=MUTED, wraplength=WIDTH,
                               font=("TkDefaultFont", 12))
        self.status.pack(fill="x", padx=28, pady=(18, 8))
        tk.Label(root, text="↑ ↓ ← → / WASD — движение     R — новая игра",
                 bg=BACKGROUND, fg=MUTED, font=("TkDefaultFont", 10)).pack(pady=(0, 22))
        root.bind("<KeyPress>", self.on_move)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()
        root.focus_set()

    def score_card(self, parent, caption):
        card = tk.Frame(parent, bg="#e9e0d5", padx=12, pady=8)
        card.pack(side="left", padx=(8, 0))
        tk.Label(card, text=caption, bg="#e9e0d5", fg=MUTED,
                 font=("TkDefaultFont", 9, "bold")).pack()
        value = tk.Label(card, text="0", bg="#e9e0d5", fg=TEXT,
                         font=("TkDefaultFont", 19, "bold"))
        value.pack()
        return value

    def rounded_rect(self, x1, y1, x2, y2, radius, color, tag):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.canvas.create_polygon(points, smooth=True, splinesteps=16,
                                   fill=color, outline="", tags=tag)

    def cell_position(self, cell):
        row, col = cell
        return PADDING + col * (CELL + GAP), PADDING + row * (CELL + GAP)

    def tile(self, value, x, y, scale=1):
        inset = CELL * (1 - scale) / 2
        self.rounded_rect(x + inset, y + inset, x + CELL - inset,
                          y + CELL - inset, 10 * scale,
                          COLORS.get(value, "#574639"), "tiles")
        font_size = max(8, int((30 if value < 1000 else 23) * scale))
        self.canvas.create_text(
            x + CELL / 2, y + CELL / 2, text=str(value),
            fill=TEXT if value <= 4 else "#fffaf1",
            font=("TkDefaultFont", font_size, "bold"), tags="tiles",
        )

    def on_move(self, event):
        key = event.keysym.lower()
        if key == "r":
            self.restart()
            return "break"
        direction = {
            "left": "left", "a": "left", "right": "right", "d": "right",
            "up": "up", "w": "up", "down": "down", "s": "down",
        }.get(key)
        if direction is None:
            return
        if self.animation is not None:
            self.pending_direction = direction
        else:
            self.move(direction)
        return "break"

    def move(self, direction):
        if self.game.move(direction):
            self.update_scores()
            self.animate(time.perf_counter())

    def animate(self, started):
        elapsed = time.perf_counter() - started
        self.canvas.delete("tiles")
        if elapsed < 0.14:
            progress = min(1, elapsed / 0.14)
            eased = 1 - (1 - progress) ** 3
            for source, destination, value in self.game.transitions:
                x1, y1 = self.cell_position(source)
                x2, y2 = self.cell_position(destination)
                self.tile(value, x1 + (x2 - x1) * eased, y1 + (y2 - y1) * eased)
        elif elapsed < 0.26:
            progress = min(1, (elapsed - 0.14) / 0.12)
            for row, values in enumerate(self.game.board):
                for col, value in enumerate(values):
                    if not value:
                        continue
                    cell = (row, col)
                    scale = 1
                    if cell == self.game.spawned_cell:
                        scale = 0.35 + 0.65 * (1 - (1 - progress) ** 3)
                    elif cell in self.game.merged_cells:
                        scale = 1 + 0.09 * math.sin(progress * math.pi)
                    self.tile(value, *self.cell_position(cell), scale)
        else:
            self.animation = None
            self.draw()
            direction = self.pending_direction
            self.pending_direction = None
            if direction:
                self.move(direction)
            return
        self.animation = self.root.after(16, self.animate, started)

    def update_scores(self):
        self.high_score = max(self.high_score, self.game.score)
        if self.high_score > self.saved_high_score:
            if save_high_score(self.high_score):
                self.saved_high_score = self.high_score
        self.score.configure(text=str(self.game.score))
        self.record.configure(text=str(self.high_score))

    def draw(self):
        self.canvas.delete("tiles")
        for row, values in enumerate(self.game.board):
            for col, value in enumerate(values):
                if value:
                    self.tile(value, *self.cell_position((row, col)))
        self.update_scores()
        if not self.game.can_move():
            message = "Ходов больше нет. Попробуем ещё раз?"
        elif self.game.reached_target:
            message = f"Плитка {TARGET} собрана! Продолжай побивать рекорд."
        else:
            message = "Соединяй одинаковые плитки и собирай 2048"
        if self.high_score > self.saved_high_score:
            message = "Рекорд пока не сохранён. Проверь доступ к папке .2048."
        self.status.configure(text=message)

    def cancel_animation(self):
        if self.animation is not None:
            self.root.after_cancel(self.animation)
            self.animation = None
        self.pending_direction = None

    def restart(self):
        self.cancel_animation()
        self.game.reset()
        self.draw()

    def close(self):
        self.cancel_animation()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    GameWindow(root)
    root.mainloop()

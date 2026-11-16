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
CELL = 82
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
        self.selection = None
        self.first_cell = None
        self.effect_running = False
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

        powers = tk.Frame(root, bg=BACKGROUND)
        powers.pack(fill="x", padx=28, pady=(12, 0))
        self.power_buttons = {}
        descriptions = [
            ("fire", "Огонь", "256 / 1024"),
            ("ice", "Лёд", "512"),
            ("lightning", "Молния", "128 / 1024"),
        ]
        for column, (element, title, unlock) in enumerate(descriptions):
            powers.columnconfigure(column, weight=1, uniform="powers")
            button = ttk.Button(powers, command=lambda name=element: self.select_power(name))
            button.grid(row=0, column=column, padx=3, sticky="ew")
            self.power_buttons[element] = (button, title)
            tk.Label(powers, text="За " + unlock, bg=BACKGROUND, fg=MUTED,
                     font=("TkDefaultFont", 9)).grid(row=1, column=column, pady=4)
        self.ice_label = tk.Label(root, text="", bg=BACKGROUND, fg="#287698",
                                  font=("TkDefaultFont", 11, "bold"))
        self.ice_label.pack()
        self.canvas.bind("<Motion>", self.hover)
        self.canvas.bind("<Leave>", lambda event: self.canvas.delete("preview"))
        self.canvas.bind("<Button-1>", self.click)

        self.status = tk.Label(root, bg=BACKGROUND, fg=MUTED, wraplength=WIDTH, height=2,
                               font=("TkDefaultFont", 12))
        self.status.pack(fill="x", padx=28, pady=(18, 8))
        tk.Label(root, text="↑ ↓ ← → / WASD — движение     R — новая игра",
                 bg=BACKGROUND, fg=MUTED, font=("TkDefaultFont", 10)).pack(pady=(0, 22))
        root.bind("<KeyPress>", self.on_move)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()
        root.update_idletasks()
        x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
        root.geometry(f"+{x}+30")
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
        if key == "escape" and not self.effect_running:
            self.clear_selection()
            self.draw()
            return "break"
        if self.selection or self.effect_running or self.game.game_over:
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
            if self.game.ice_just_ended:
                self.game.ice_just_ended = False
                self.start_effect("thaw")
            elif direction and not self.game.game_over:
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
        self.draw_ice()
        for element, (button, title) in self.power_buttons.items():
            enabled = self.game.available(element) and not self.effect_running and self.animation is None
            if element == "ice" and self.game.ice_moves:
                enabled = False
            button.configure(text=f"{title} · {self.game.charges[element]}",
                             state="normal" if enabled else "disabled")
        self.ice_label.configure(
            text=f"ЛЁД · осталось ходов: {self.game.ice_moves}" if self.game.ice_moves else "")
        if self.selection == "fire":
            message = "Выбери область 2×2 · сгорают плитки до 32 · Esc — отмена"
        elif self.selection == "lightning":
            message = "Выбери вторую клетку · Esc — отмена" if self.first_cell else "Выбери плитку для переноса · Esc — отмена"
        elif self.game.game_over or not self.game.can_move():
            message = "Ходов больше нет. Попробуем ещё раз?"
        elif self.game.reached_target:
            message = f"Плитка {TARGET} собрана! Продолжай побивать рекорд."
        else:
            message = "Соединяй одинаковые плитки и собирай 2048"
        if self.high_score > self.saved_high_score:
            message = "Рекорд пока не сохранён. Проверь доступ к папке .2048."
        self.status.configure(text=message)
        self.canvas.tag_raise("selected")
        self.canvas.tag_raise("preview")

    def clear_selection(self):
        self.selection = None
        self.first_cell = None
        self.canvas.delete("preview")
        self.canvas.delete("selected")

    def event_cell(self, event):
        col = int((event.x - PADDING) // (CELL + GAP))
        row = int((event.y - PADDING) // (CELL + GAP))
        if not (0 <= row < SIZE and 0 <= col < SIZE):
            return None
        x, y = self.cell_position((row, col))
        if event.x >= x + CELL or event.y >= y + CELL:
            return None
        return row, col

    def select_power(self, element):
        if self.animation is not None or self.game.game_over:
            return
        self.clear_selection()
        self.pending_direction = None
        if element == "ice":
            if self.game.use_ice():
                self.start_effect("ice")
        elif self.game.available(element):
            self.selection = element
        self.draw()
        self.root.focus_set()

    def hover(self, event):
        self.canvas.delete("preview")
        cell = self.event_cell(event)
        if self.selection != "fire" or cell is None:
            return
        row, col = min(cell[0], SIZE - 2), min(cell[1], SIZE - 2)
        for r in range(row, row + 2):
            for c in range(col, col + 2):
                x, y = self.cell_position((r, c))
                burnable = 0 < self.game.board[r][c] <= 32
                self.canvas.create_rectangle(x + 2, y + 2, x + CELL - 2, y + CELL - 2,
                                             outline="#ef713c" if burnable else "#887c70",
                                             width=4 if burnable else 2, tags="preview")

    def click(self, event):
        if self.animation is not None or self.game.game_over:
            return
        cell = self.event_cell(event)
        if cell is None:
            return
        before = [row[:] for row in self.game.board]
        if self.selection == "fire":
            corner = (min(cell[0], SIZE - 2), min(cell[1], SIZE - 2))
            if self.game.use_fire(*corner):
                self.clear_selection()
                self.start_effect("fire", before, corner)
        elif self.selection == "lightning":
            if cell == self.first_cell:
                self.first_cell = None
                self.canvas.delete("selected")
            elif self.first_cell is None:
                if self.game.board[cell[0]][cell[1]]:
                    self.first_cell = cell
                    x, y = self.cell_position(cell)
                    self.canvas.create_rectangle(x, y, x + CELL, y + CELL,
                                                 outline="#7477ef", width=4, tags="selected")
            elif self.game.use_lightning(self.first_cell, cell):
                pair = (self.first_cell, cell)
                self.clear_selection()
                self.start_effect("lightning", before, pair)
        self.draw()

    def draw_ice(self):
        self.canvas.delete("ice")
        if self.game.ice_moves:
            self.canvas.create_rectangle(3, 3, WIDTH - 3, WIDTH - 3,
                                         outline="#80d6ec", width=5, tags="ice")
            for x in range(16, WIDTH, 35):
                self.canvas.create_line(x, 3, x + 8, 17, x + 16, 3,
                                        fill="#d2f7ff", width=2, tags="ice")

    def start_effect(self, kind, before=None, target=None):
        self.effect_running = True
        self.pending_direction = None
        self.effect_frame(kind, time.perf_counter(), before, target)

    def effect_frame(self, kind, started, before, target):
        duration = 0.6 if kind == "fire" else 0.5
        progress = min(1, (time.perf_counter() - started) / duration)
        self.draw()
        self.canvas.delete("effect")
        if kind == "fire":
            row, col = target
            x, y = self.cell_position(target)
            cx, cy = x + CELL + GAP / 2, y + CELL + GAP / 2
            for r in range(row, row + 2):
                for c in range(col, col + 2):
                    value = before[r][c]
                    if 0 < value <= 32 and progress < 0.65:
                        self.tile(value, *self.cell_position((r, c)), 1 - progress)
            radius = (CELL + GAP) * progress
            self.canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius,
                                    outline="#f3a43b", width=max(1, int(10*(1-progress))), tags="effect")
            for i in range(24):
                angle = i * math.tau / 24
                distance = radius * (0.6 + (i % 4) / 5)
                px, py = cx + math.cos(angle)*distance, cy + math.sin(angle)*distance
                size = 4*(1-progress) + 1
                self.canvas.create_oval(px-size, py-size, px+size, py+size,
                                        fill="#ef713c", outline="", tags="effect")
        elif kind == "lightning":
            self.canvas.delete("tiles")
            first, second = target
            for r, values in enumerate(before):
                for c, value in enumerate(values):
                    if value and (r, c) not in target:
                        self.tile(value, *self.cell_position((r, c)))
            x1, y1 = self.cell_position(first)
            x2, y2 = self.cell_position(second)
            eased = progress * progress * (3 - 2 * progress)
            length = max(1, math.hypot(x2-x1, y2-y1))
            arc = math.sin(progress * math.pi) * 35
            dx, dy = -(y2-y1)/length*arc, (x2-x1)/length*arc
            for source, start, end, sign in (
                (first, (x1, y1), (x2, y2), 1),
                (second, (x2, y2), (x1, y1), -1),
            ):
                value = before[source[0]][source[1]]
                if value:
                    self.tile(value, start[0]+(end[0]-start[0])*eased+dx*sign,
                              start[1]+(end[1]-start[1])*eased+dy*sign)
            points = []
            for i in range(13):
                t = i / 12
                jitter = math.sin(i*7 + progress*35)*10 if i not in (0, 12) else 0
                points.extend((x1+CELL/2+(x2-x1)*t+jitter,
                               y1+CELL/2+(y2-y1)*t-jitter))
            self.canvas.create_line(points, fill="#b2a4ff", width=5, tags="effect")
            self.canvas.create_line(points, fill="#f4efff", width=2, tags="effect")
        else:
            inset = 3 + (progress*30 if kind == "thaw" else (1-progress)*22)
            self.canvas.create_rectangle(inset, inset, WIDTH-inset, WIDTH-inset,
                                         outline="#b3edff", width=max(1, int(9*(1-progress))), tags="effect")
            if kind == "thaw":
                for i in range(16):
                    x = i * WIDTH / 16
                    self.canvas.create_line(x, progress*40, x+12, progress*40+18,
                                            fill="#8dd9f1", width=2, tags="effect")
        if progress >= 1:
            self.animation = None
            self.effect_running = False
            self.canvas.delete("effect")
            self.draw()
            return
        self.animation = self.root.after(16, self.effect_frame, kind, started, before, target)

    def cancel_animation(self):
        if self.animation is not None:
            self.root.after_cancel(self.animation)
            self.animation = None
        self.pending_direction = None
        self.effect_running = False
        self.clear_selection()
        self.canvas.delete("effect")

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

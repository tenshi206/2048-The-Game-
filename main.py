import tkinter as tk

from game import Game, SIZE, TARGET
from tkinter import ttk

from high_score import load_high_score, save_high_score


BACKGROUND = "#faf8ef"
TEXT = "#4e463e"
BOARD_BACKGROUND = "#bbada0"
CELL_SIZE = 92
TILE_COLORS = {
    0: "#cdc1b4",
    2: "#eee4da",
    4: "#ede0c8",
    8: "#ac5b25",
    16: "#a44c24",
    32: "#ae4431",
    64: "#9d3524",
    128: "#8a681d",
    256: "#80601b",
    512: "#765719",
    1024: "#6b5018",
    2048: "#624917",
}


class GameWindow:
    def __init__(self, root):
        self.game = Game()
        self.high_score = load_high_score()
        self.saved_high_score = self.high_score
        root.title("2048")
        root.configure(bg=BACKGROUND)
        root.resizable(False, False)
        root.minsize(448, 0)
        style = ttk.Style(root)
        style.configure("NewGame.TButton", font=("TkDefaultFont", 12, "bold"), padding=(16, 8))

        header = tk.Frame(root, bg=BACKGROUND)
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(header, text="2048", font=("TkDefaultFont", 36, "bold"),
                 bg=BACKGROUND, fg=TEXT).pack(side="left")
        scores = tk.Frame(header, bg=BACKGROUND)
        scores.pack(side="right")
        self.record = tk.Label(scores, bg=BACKGROUND, fg=TEXT,
                               font=("TkDefaultFont", 12))
        self.record.pack(anchor="e")
        self.score = tk.Label(scores, bg=BACKGROUND, fg=TEXT,
                              font=("TkDefaultFont", 14, "bold"))
        self.score.pack(anchor="e")

        toolbar = tk.Frame(root, bg=BACKGROUND)
        toolbar.pack(fill="x", padx=24, pady=(0, 16))
        tk.Label(
            toolbar, text="Собери плитку 2048", bg=BACKGROUND, fg=TEXT,
            font=("TkDefaultFont", 12),
        ).pack(side="left")
        ttk.Button(
            toolbar, text="Новая игра", style="NewGame.TButton",
            command=self.restart,
        ).pack(side="right")

        board = tk.Frame(root, bg=BOARD_BACKGROUND, padx=6, pady=6)
        board.pack(padx=24)
        self.tiles = []
        for row in range(SIZE):
            tile_row = []
            for col in range(SIZE):
                cell = tk.Frame(board, width=CELL_SIZE, height=CELL_SIZE)
                cell.grid(row=row, column=col, padx=4, pady=4)
                cell.pack_propagate(False)
                label = tk.Label(cell, borderwidth=0)
                label.pack(expand=True, fill="both")
                tile_row.append(label)
            self.tiles.append(tile_row)

        self.status = tk.Label(
            root, bg=BACKGROUND, fg=TEXT, wraplength=380,
            font=("TkDefaultFont", 12), justify="center",
        )
        self.status.pack(fill="x", padx=24, pady=(16, 20))

        root.bind("<KeyPress>", self.on_move)
        self.draw()
        root.focus_set()

    def on_move(self, event):
        key = event.keysym.lower()
        if key == "r":
            self.restart()
            return "break"
        directions = {
            "left": "left", "a": "left",
            "right": "right", "d": "right",
            "up": "up", "w": "up",
            "down": "down", "s": "down",
        }
        direction = directions.get(key)
        if direction is None:
            return
        if self.game.move(direction):
            self.draw()
        return "break"

    def restart(self):
        self.game.reset()
        self.draw()

    def draw(self):
        self.high_score = max(self.high_score, self.game.score)
        if self.high_score > self.saved_high_score:
            if save_high_score(self.high_score):
                self.saved_high_score = self.high_score
        record_text = f"Рекорд: {self.high_score}"
        if self.high_score > self.saved_high_score:
            record_text += " (не сохранён)"
        self.record.configure(text=record_text)
        for row, values in enumerate(self.game.board):
            for col, value in enumerate(values):
                self.tiles[row][col].configure(
                    text=str(value) if value else "",
                    bg=TILE_COLORS.get(value, "#3c3a32"),
                    fg=TEXT if value <= 4 else "white",
                    font=("TkDefaultFont", 28 if value < 1000 else 20, "bold"),
                )

        self.score.configure(text=f"Счёт: {self.game.score}")
        if not self.game.can_move():
            message = "Ходов больше нет. Начни новую игру!"
        elif self.game.reached_target:
            message = f"Ты собрал {TARGET}! Можно играть дальше."
        else:
            message = "Стрелки / WASD — ход · R — новая игра"
        self.status.configure(text=message)


if __name__ == "__main__":
    root = tk.Tk()
    GameWindow(root)
    root.mainloop()

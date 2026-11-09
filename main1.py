import tkinter as tk

from game import Game, SIZE, TARGET


BACKGROUND = "#FF0050"
TEXT = "#FFFFFF"
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
        root.title("2048")
        root.configure(bg=BACKGROUND)
        root.resizable(False, False)

        self._build_header(root)
        self._build_board(root)
        self._build_footer(root)

        for key in ("Left", "Right", "Up", "Down"):
            root.bind(f"<KeyPress-{key}>", self.on_move)
        self.draw()
        root.focus_set()

    def _build_header(self, root):
        header = tk.Frame(root, bg=BACKGROUND)
        header.pack(fill="x", padx=16, pady=(12, 8))
        tk.Label(header, text="2048", font=("TkDefaultFont", 28, "bold"),
                 bg=BACKGROUND, fg=TEXT).pack(side="left")
        self.score = tk.Label(header, bg=BACKGROUND, fg=TEXT,
                              font=("TkDefaultFont", 14, "bold"))
        self.score.pack(side="right")

    def _build_board(self, root):
        board = tk.Frame(root, bg="#bbada0", padx=5, pady=5)
        board.pack(padx=16)
        self.tiles = []
        for row in range(SIZE):
            tile_row = []
            for col in range(SIZE):
                cell = tk.Frame(board, width=78, height=78)
                cell.grid(row=row, column=col, padx=4, pady=4)
                cell.pack_propagate(False)
                label = tk.Label(cell, borderwidth=0)
                label.pack(expand=True, fill="both")
                tile_row.append(label)
            self.tiles.append(tile_row)

    def _build_footer(self, root):
        self.status = tk.Label(root, bg=BACKGROUND, fg=TEXT)
        self.status.pack(pady=(10, 4))
        tk.Button(root, text="Новая игра", command=self.restart).pack(pady=(0, 12))

    def on_move(self, event):
        if self.game.move(event.keysym.lower()):
            self.draw()
        return "break"

    def restart(self):
        self.game.reset()
        self.draw()

    def _draw_tile(self, row, col, value):
        self.tiles[row][col].configure(
            text=str(value) if value else "",
            bg=TILE_COLORS.get(value, "#3c3a32"),
            fg=TEXT if value <= 4 else "white",
            font=("TkDefaultFont", 22 if value < 1000 else 16, "bold"),
        )

    def _status_message(self):
        if not self.game.can_move():
            return "Ходов больше нет. Начни новую игру!"
        if self.game.reached_target:
            return f"Ты собрал {TARGET}! Можно играть дальше."
        return "Чтобы сделать ход-жми стрелки"

    def draw(self):
        for row, values in enumerate(self.game.board):
            for col, value in enumerate(values):
                self._draw_tile(row, col, value)

        self.score.configure(text=f"Счёт: {self.game.score}")
        self.status.configure(text=self._status_message())

if __name__ == "__main__":
    root = tk.Tk()
    GameWindow(root)
    root.mainloop() 
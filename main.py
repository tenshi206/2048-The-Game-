import math
import time
import tkinter as tk
from tkinter import ttk
from random import sample

from game import Game, SIZE, TARGET
from high_score import load_high_score, save_high_score
from progression import Profile, CONTRACTS, COMBINATIONS
from themes import THEMES, tile_text_color

CELL = 82
GAP = 10
PADDING = 12
WIDTH = PADDING * 2 + SIZE * CELL + (SIZE - 1) * GAP



class GameWindow:
    def __init__(self, root, profile=None, choose_contract=True):
        self.root = root
        self.profile = profile if profile is not None else Profile()
        self.theme = THEMES[self.profile.theme]
        self.dialog = None
        self.awaiting_contract = choose_contract
        self.result_round = None
        self.pending_rewards = {}
        self.notice = ""
        self.notice_until = 0
        self.game = Game()
        self.high_score = load_high_score()
        self.saved_high_score = self.high_score
        self.animation = None
        self.pending_direction = None
        self.selection = None
        self.first_cell = None
        self.effect_running = False
        root.title("2048 · Стихии")
        root.configure(bg=self.theme["background"])
        root.resizable(False, False)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("NewGame.TButton", font=("TkDefaultFont", 12, "bold"),
                        padding=(14, 9))

        header = tk.Frame(root, bg=self.theme["background"])
        header.pack(fill="x", padx=28, pady=(16, 4))
        tk.Label(header, text="2048", font=("TkDefaultFont", 40, "bold"),
                 bg=self.theme["background"], fg=self.theme["text"]).pack(side="left")
        scores = tk.Frame(header, bg=self.theme["background"])
        scores.pack(side="right")
        self.score = self.score_card(scores, "СЧЁТ")
        self.record = self.score_card(scores, "РЕКОРД")

        toolbar = tk.Frame(root, bg=self.theme["background"])
        toolbar.pack(fill="x", padx=28, pady=(4, 8))
        self.wallet = tk.Label(toolbar, text="", bg=self.theme["background"], fg=self.theme["text"],
                               font=("TkDefaultFont", 11, "bold"))
        self.wallet.pack(side="left")
        ttk.Button(toolbar, text="Мастерская",
                   command=self.show_workshop).pack(side="left", padx=10)
        ttk.Button(toolbar, text="Новая игра", style="NewGame.TButton",
                   command=self.restart).pack(side="right")

        self.contract_label = tk.Label(root, bg=self.theme["background"], fg=self.theme["muted"],
                                       wraplength=WIDTH, height=2,
                                       font=("TkDefaultFont", 10), justify="left")
        self.contract_label.pack(fill="x", padx=28, pady=(0, 6))

        self.canvas = tk.Canvas(root, width=WIDTH, height=WIDTH,
                                bg=self.theme["background"], highlightthickness=0)
        self.canvas.pack(padx=28)
        self.draw_base()

        powers = tk.Frame(root, bg=self.theme["background"])
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
            tk.Label(powers, text="За " + unlock, bg=self.theme["background"], fg=self.theme["muted"],
                     font=("TkDefaultFont", 9)).grid(row=1, column=column, pady=4)
        self.ice_label = tk.Label(root, text="", bg=self.theme["background"], fg="#287698",
                                  font=("TkDefaultFont", 11, "bold"))
        self.ice_label.pack()
        self.canvas.bind("<Motion>", self.hover)
        self.canvas.bind("<Leave>", lambda event: self.canvas.delete("preview"))
        self.canvas.bind("<Button-1>", self.click)

        self.status = tk.Label(root, bg=self.theme["background"], fg=self.theme["muted"], wraplength=WIDTH, height=2,
                               font=("TkDefaultFont", 12))
        self.status.pack(fill="x", padx=28, pady=(8, 4))
        tk.Label(root, text="↑ ↓ ← → / WASD — движение     R — новая игра",
                 bg=self.theme["background"], fg=self.theme["muted"], font=("TkDefaultFont", 10)).pack(pady=(0, 12))
        root.bind("<KeyPress>", self.on_move)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.apply_theme(self.profile.theme)
        self.draw()
        if choose_contract:
            root.after_idle(self.show_contracts)
        root.update_idletasks()
        x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
        root.geometry(f"+{x}+30")
        root.focus_set()

    def score_card(self, parent, caption):
        card = tk.Frame(parent, bg=self.theme["card"], padx=12, pady=8)
        card.pack(side="left", padx=(8, 0))
        tk.Label(card, text=caption, bg=self.theme["card"], fg=self.theme["muted"],
                 font=("TkDefaultFont", 9, "bold")).pack()
        value = tk.Label(card, text="0", bg=self.theme["card"], fg=self.theme["text"],
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
                          self.theme["tiles"].get(value, self.theme["tiles"][2048]), "tiles")
        font_size = max(8, int((30 if value < 1000 else 23) * scale))
        self.canvas.create_text(
            x + CELL / 2, y + CELL / 2, text=str(value),
            fill=tile_text_color(self.theme, value),
            font=("TkDefaultFont", font_size, "bold"), tags="tiles",
        )

    def on_move(self, event):
        if self.dialog is not None or self.awaiting_contract:
            return "break"
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
        else:
            self.draw()

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
        self.sync_progression()
        self.wallet.configure(text=f"Монеты · {self.profile.coins}")
        self.contract_label.configure(text=self.contract_text())

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
        if self.profile.error:
            message = self.profile.error
        elif time.perf_counter() < self.notice_until and not self.selection:
            message = self.notice
        self.status.configure(text=message)
        self.canvas.tag_raise("selected")
        self.canvas.tag_raise("preview")
        if (self.game.game_over and self.animation is None and not self.effect_running
                and self.result_round != self.game.round_id):
            self.result_round = self.game.round_id
            self.root.after_idle(self.show_results, self.game.round_id)

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
        if (self.animation is not None or self.game.game_over
                or self.dialog is not None or self.awaiting_contract):
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
        if (self.animation is not None or self.game.game_over
                or self.dialog is not None or self.awaiting_contract):
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

    def blend(self, foreground, background, opacity):
        opacity = max(0, min(1, opacity))
        channels = []
        for index in (1, 3, 5):
            a = int(foreground[index:index + 2], 16)
            b = int(background[index:index + 2], 16)
            channels.append(round(b + (a - b) * opacity))
        return "#" + "".join(f"{value:02x}" for value in channels)

    def frost(self, opacity, tag="ice", drift=0):
        # Frost stays on the border, keeping the numbers unobstructed.
        color = self.blend("#d9f8ff", self.theme["board"], opacity)
        for inset, width, strength in ((3, 6, 0.3), (5, 2, 0.8)):
            self.canvas.create_rectangle(
                inset, inset, WIDTH-inset, WIDTH-inset,
                outline=self.blend("#9de5f5", self.theme["board"], opacity*strength),
                width=width, tags=tag)
        for edge in range(4):
            for index in range(10):
                along = 14 + index * (WIDTH - 28) / 9
                depth = 10 + (index * 7 % 13)
                points = [(along-5, 4), (along, depth), (along+5, 4)]
                if edge == 1:
                    points = [(WIDTH-y, x) for x, y in points]
                elif edge == 2:
                    points = [(WIDTH-x, WIDTH-y) for x, y in points]
                elif edge == 3:
                    points = [(y, WIDTH-x) for x, y in points]
                self.canvas.create_line(
                    [coordinate + drift * math.sin(index + edge) for point in points for coordinate in point],
                    fill=color, width=1.5, tags=tag)

    def draw_ice(self):
        self.canvas.delete("ice")
        if self.game.ice_moves:
            self.frost(0.85)

    def glow_ring(self, x, y, radius, color, opacity, background=None):
        background = background or self.theme["empty"]
        for width, strength in ((12, 0.12), (6, 0.25), (2, 0.9)):
            self.canvas.create_oval(
                x-radius, y-radius, x+radius, y+radius,
                outline=self.blend(color, background, opacity*strength),
                width=width, tags="effect")

    def spark(self, x, y, size, color, opacity):
        if size < 0.3 or opacity <= 0:
            return
        self.canvas.create_oval(
            x-size*1.8, y-size*1.8, x+size*1.8, y+size*1.8,
            fill=self.blend(color, self.theme["empty"], opacity*0.2), outline="", tags="effect")
        self.canvas.create_oval(
            x-size, y-size, x+size, y+size,
            fill=self.blend(color, self.theme["empty"], opacity), outline="", tags="effect")

    def start_effect(self, kind, before=None, target=None):
        self.effect_running = True
        self.pending_direction = None
        self.draw()
        self.effect_frame(kind, time.perf_counter(), before, target)

    def effect_frame(self, kind, started, before, target):
        duration = {"fire": 0.78, "ice": 0.65, "lightning": 0.7, "thaw": 0.65}[kind]
        progress = min(1, (time.perf_counter() - started) / duration)
        self.canvas.delete("effect")
        if kind == "fire":
            self.fire_frame(progress, before, target)
        elif kind == "lightning":
            self.lightning_frame(progress, before, target)
        else:
            self.ice_frame(progress, kind == "thaw")
        self.combination_frame(progress, kind, target)
        if progress >= 1:
            self.animation = None
            self.effect_running = False
            self.canvas.delete("effect")
            self.draw()
            return
        self.animation = self.root.after(16, self.effect_frame, kind, started, before, target)

    def fire_frame(self, progress, before, target):
        self.canvas.delete("tiles")
        row, col = target
        x, y = self.cell_position(target)
        cx, cy = x + CELL + GAP/2, y + CELL + GAP/2
        burn = min(1, max(0, (progress-0.12)/0.58))
        for r, values in enumerate(before):
            for c, value in enumerate(values):
                inside = row <= r < row+2 and col <= c < col+2
                if value:
                    scale = 1
                    if inside and value <= 32:
                        scale = (1-burn) ** 1.5
                    if scale > 0.04:
                        self.tile(value, *self.cell_position((r, c)), scale)
        expansion = 1 - (1-progress)**3
        fade = math.sin(math.pi * progress)**0.8
        self.glow_ring(cx, cy, (CELL+GAP)*expansion, "#ffb650", fade)
        self.glow_ring(cx, cy, (CELL+GAP)*expansion*0.72, "#fff0b0", fade*0.55)
        # Deterministic trajectories avoid frame-to-frame particle flicker.
        for i in range(42):
            angle = i * 2.39996
            speed = 35 + (i*17 % 65)
            distance = speed * expansion
            px = cx + math.cos(angle)*distance
            py = cy + math.sin(angle)*distance - progress*progress*32
            life = max(0, math.sin(math.pi*progress)) * (0.6 + (i % 3)*0.2)
            color = ("#ffcc73", "#f58a4b", "#fff0bb")[i % 3]
            self.spark(px, py, (1.5+i%3)*(1-progress*0.65), color, life)
        for r in range(row, row+2):
            for c in range(col, col+2):
                if 0 < before[r][c] <= 32:
                    tx, ty = self.cell_position((r, c))
                    radius = CELL * (0.35 + burn*0.15)
                    self.glow_ring(tx+CELL/2, ty+CELL/2, radius,
                                   "#ffcc73", fade*0.4)

    def lightning_frame(self, progress, before, target):
        self.canvas.delete("tiles")
        first, second = target
        x1, y1 = self.cell_position(first)
        x2, y2 = self.cell_position(second)
        travel = max(0, min(1, (progress-0.18)/0.62))
        eased = travel*travel*(3-2*travel)
        distance = max(1, math.hypot(x2-x1, y2-y1))
        arc = math.sin(travel*math.pi)*min(32, distance*0.2)
        dx, dy = -(y2-y1)/distance*arc, (x2-x1)/distance*arc
        for r, values in enumerate(before):
            for c, value in enumerate(values):
                if value and (r, c) not in target:
                    self.tile(value, *self.cell_position((r, c)))
        beam_strength = math.sin(math.pi*progress)**0.7
        points = []
        for i in range(17):
            t = i/16
            jitter = math.sin(i*2.7 + progress*9)*7*math.sin(t*math.pi)
            points.extend((x1+CELL/2+(x2-x1)*t-(y2-y1)/distance*jitter,
                           y1+CELL/2+(y2-y1)*t+(x2-x1)/distance*jitter))
        for width, strength, color in ((15, 0.12, "#9887ed"), (8, 0.3, "#b5a5ff"), (3, 0.85, "#dcd0ff"), (1, 1, "#fff7ff")):
            self.canvas.create_line(
                points, fill=self.blend(color, self.theme["empty"], beam_strength*strength),
                width=width, smooth=True, tags="effect")
        for source, start, end, sign in (
            (first, (x1,y1), (x2,y2), 1), (second, (x2,y2), (x1,y1), -1),
        ):
            px = start[0]+(end[0]-start[0])*eased+dx*sign
            py = start[1]+(end[1]-start[1])*eased+dy*sign
            value = before[source[0]][source[1]]
            self.glow_ring(px+CELL/2, py+CELL/2, CELL*0.46, "#b8a1ff", beam_strength)
            if value:
                self.tile(value, px, py, 1+0.025*math.sin(travel*math.pi))
            for i in range(8):
                angle = i*math.tau/8 + progress*1.4
                radius = CELL*0.52
                self.spark(px+CELL/2+math.cos(angle)*radius,
                           py+CELL/2+math.sin(angle)*radius,
                           1.5, "#e3d7ff", beam_strength*0.8)

    def ice_frame(self, progress, thaw):
        self.canvas.delete("ice")
        eased = 1-(1-progress)**3
        opacity = 1-eased if thaw else eased
        self.frost(opacity, "effect", drift=progress*8 if thaw else 0)
        for edge in range(4):
            for i in range(12):
                along = 12+i*(WIDTH-24)/11
                drift = progress*progress*22 if thaw else (1-eased)*18
                px, py = along, 7+drift
                if edge == 1:
                    px, py = WIDTH-py, px
                elif edge == 2:
                    px, py = WIDTH-px, WIDTH-py
                elif edge == 3:
                    px, py = py, WIDTH-px
                twinkle = max(0, math.sin(math.pi*progress))*(0.6+0.4*math.sin(i+progress*3)**2)
                self.spark(px, py, 1.5+i%2, "#e0faff", twinkle)
                if thaw:
                    color = self.blend("#c2f2ff", self.theme["board"], 1-progress)
                    self.canvas.create_line(px-3, py-4, px+3, py+4,
                                            fill=color, width=1, tags="effect")

    def draw_base(self):
        self.canvas.delete("base")
        self.rounded_rect(0, 0, WIDTH, WIDTH, 18, self.theme["board"], "base")
        for row in range(SIZE):
            for col in range(SIZE):
                x, y = self.cell_position((row, col))
                self.rounded_rect(x, y, x + CELL, y + CELL, 10, self.theme["empty"], "base")
        self.canvas.tag_lower("base")

    def apply_theme(self, theme_id):
        previous = self.theme
        self.theme = THEMES[theme_id]
        backgrounds = {previous[key]: self.theme[key]
                       for key in ("background", "card")}
        foregrounds = {previous[key]: self.theme[key] for key in ("text", "muted")}

        def recolor(widget):
            if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame, tk.Label, tk.Canvas)):
                background = widget.cget("background")
                if background in backgrounds:
                    widget.configure(background=backgrounds[background])
            if isinstance(widget, tk.Label):
                foreground = widget.cget("foreground")
                if foreground in foregrounds:
                    widget.configure(foreground=foregrounds[foreground])
            for child in widget.winfo_children():
                recolor(child)

        recolor(self.root)
        style = ttk.Style(self.root)
        style.configure("TButton", background=self.theme["card"],
                        foreground=self.theme["text"], padding=(8, 6),
                        borderwidth=0, font=("TkDefaultFont", 11))
        style.map("TButton",
                  background=[("active", self.theme["empty"]),
                              ("disabled", self.theme["background"])],
                  foreground=[("disabled", self.theme["muted"])])
        style.configure("NewGame.TButton", padding=(10, 7),
                        font=("TkDefaultFont", 11, "bold"))
        style.configure("TNotebook", background=self.theme["background"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.theme["card"],
                        foreground=self.theme["text"], padding=(12, 8))
        style.map("TNotebook.Tab",
                  background=[("selected", self.theme["empty"])])
        self.draw_base()
        self.draw()

    def sync_progression(self):
        self.pending_rewards[self.game.round_id] = list(self.game.reward_events)
        added = []
        for round_id, events in list(self.pending_rewards.items()):
            received = self.profile.collect(round_id, events)
            if received is None:
                break
            added.extend(received)
            del self.pending_rewards[round_id]
        if added:
            amount = sum(reward for title, reward in added)
            titles = ", ".join(title for title, reward in added)
            self.notice = f"+{amount} монет · {titles}"
            self.notice_until = time.perf_counter() + 4

    def contract_text(self):
        if not self.game.contract:
            return "Свободная партия · монеты за плитки и открытия сочетаний"
        info = CONTRACTS[self.game.contract]
        state = {
            "active": "В работе", "complete": "Выполнен", "failed": "Не выполнен",
        }[self.game.contract_state]
        progress = self.game.contract_progress
        targets = {"clean": 256, "triple": 3, "fire": 4, "ice": 128, "arsenal": 3}
        return (f"{info['title']} · {state} · {min(progress, targets[self.game.contract])}"
                f"/{targets[self.game.contract]} · награда {info['reward']} монет")

    def open_dialog(self, title):
        if self.dialog is not None:
            self.dialog.lift()
            return None
        self.pending_direction = None
        self.clear_selection()
        window = tk.Toplevel(self.root)
        self.dialog = window
        window.title(title)
        window.configure(bg=self.theme["background"])
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()
        window.protocol("WM_DELETE_WINDOW", self.close_dialog)
        return window

    def close_dialog(self):
        if self.dialog is not None:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
        self.root.focus_set()

    def dialog_label(self, parent, text, size=12, bold=False, **options):
        label = tk.Label(parent, text=text, bg=self.theme["background"],
                         fg=self.theme["text"], justify="left", anchor="w",
                         font=("TkDefaultFont", size, "bold" if bold else "normal"),
                         **options)
        return label

    def show_contracts(self):
        window = self.open_dialog("Контракт на партию")
        if window is None:
            return
        self.dialog_label(window, "Выбери цель на эту партию", 19, True).pack(
            anchor="w", padx=22, pady=(18, 4))
        self.dialog_label(window, "Награда начисляется сразу после выполнения.",
                          size=11).pack(anchor="w", padx=22, pady=(0, 12))
        self.contract_offers = sample(list(CONTRACTS), 3)

        def choose(contract):
            self.close_dialog()
            self.start_round(contract)

        for contract in self.contract_offers:
            info = CONTRACTS[contract]
            frame = tk.Frame(window, bg=self.theme["background"])
            frame.pack(fill="x", padx=22, pady=8)
            self.dialog_label(frame, f"{info['title']} · +{info['reward']} монет",
                              13, True).pack(anchor="w")
            self.dialog_label(frame, info["description"], 11,
                              wraplength=360).pack(anchor="w", pady=5)
            ttk.Button(frame, text="Выбрать",
                       command=lambda value=contract: choose(value)).pack(anchor="w")
        ttk.Button(window, text="Играть без контракта",
                   command=lambda: choose(None)).pack(padx=22, pady=(12, 20), fill="x")

        def dismiss():
            self.close_dialog()
            if self.awaiting_contract:
                self.start_round()

        window.protocol("WM_DELETE_WINDOW", dismiss)
        window.bind("<Escape>", lambda event: dismiss())

    def show_workshop(self):
        if self.animation is not None or self.effect_running or self.awaiting_contract:
            return
        self.sync_progression()
        window = self.open_dialog("Мастерская и коллекция")
        if window is None:
            return
        self.shop_wallet = self.dialog_label(window, f"Монеты · {self.profile.coins}", 19, True)
        self.shop_wallet.pack(anchor="w", padx=22, pady=(18, 6))
        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", padx=16, pady=8)
        themes_page = tk.Frame(notebook, bg=self.theme["background"])
        combos_page = tk.Frame(notebook, bg=self.theme["background"])
        notebook.add(themes_page, text="Темы оформления")
        notebook.add(combos_page, text="Коллекция сочетаний")
        self.shop_buttons = {}
        for theme_id, theme in THEMES.items():
            row = tk.Frame(themes_page, bg=self.theme["background"])
            row.pack(fill="x", padx=10, pady=8)
            self.dialog_label(row, theme["title"], 13, True).pack(anchor="w")
            self.dialog_label(row, theme["description"], 10).pack(anchor="w", pady=(3, 4))
            preview = tk.Canvas(row, width=340, height=38, highlightthickness=0,
                                bg=theme["board"])
            preview.pack(anchor="w")
            for index, value in enumerate((2, 4, 8, 64, 256, 2048)):
                x = 5 + index*55
                preview.create_rectangle(x, 4, x+49, 34,
                                         fill=theme["tiles"][value], outline="")
                preview.create_text(x+24, 19, text=str(value),
                                    fill=tile_text_color(theme, value),
                                    font=("TkDefaultFont", 11, "bold"))
            button = ttk.Button(row, command=lambda name=theme_id: self.select_theme(name))
            button.pack(anchor="w", pady=(5, 0))
            self.shop_buttons[theme_id] = button

        discovered = self.profile.discovered_combinations()
        for combo_id, info in COMBINATIONS.items():
            opened = combo_id in discovered
            title = info["title"] if opened else "Не открыто"
            self.dialog_label(combos_page, title, 14, True).pack(
                anchor="w", padx=14, pady=(16, 5))
            self.dialog_label(combos_page, info["description"], 11,
                              wraplength=340).pack(anchor="w", padx=14)
            self.dialog_label(combos_page,
                              "Открыто · награда уже получена" if opened else "За первое открытие · +25 монет",
                              10).pack(anchor="w", padx=14, pady=(5, 12))
        self.shop_status = self.dialog_label(window, "", 10, wraplength=360)
        self.shop_status.pack(anchor="w", padx=22, pady=4)
        ttk.Button(window, text="Вернуться к игре", command=self.close_dialog).pack(
            fill="x", padx=22, pady=(4, 16))
        self.refresh_shop()

    def refresh_shop(self):
        owned = self.profile.owned_themes()
        self.shop_wallet.configure(text=f"Монеты · {self.profile.coins}")
        for theme_id, button in self.shop_buttons.items():
            price = THEMES[theme_id]["price"]
            if theme_id == self.profile.theme:
                text, enabled = "Применена", False
            elif theme_id in owned:
                text, enabled = "Применить", True
            else:
                text = f"Купить · {price} монет"
                enabled = self.profile.persistent and self.profile.coins >= price
            button.configure(text=text, state="normal" if enabled else "disabled")

    def select_theme(self, theme_id):
        if theme_id not in self.profile.owned_themes():
            if not self.profile.buy(theme_id):
                self.shop_status.configure(text=self.profile.error or "Недостаточно монет.")
                self.refresh_shop()
                return
        if self.profile.equip(theme_id):
            self.apply_theme(theme_id)
            self.shop_status.configure(text=f"Тема «{THEMES[theme_id]['title']}» применена.")
        else:
            self.shop_status.configure(text=self.profile.error)
        self.refresh_shop()

    def show_results(self, round_id):
        if round_id != self.game.round_id or not self.game.game_over:
            return
        self.sync_progression()
        window = self.open_dialog("Итоги партии")
        if window is None:
            return
        self.dialog_label(window, "Партия завершена", 22, True).pack(
            anchor="w", padx=24, pady=(20, 12))
        best = max(max(row) for row in self.game.board)
        self.dialog_label(window, f"Счёт · {self.game.score}     Лучшая плитка · {best}",
                          12).pack(anchor="w", padx=24)
        self.dialog_label(window, self.contract_text(), 11,
                          wraplength=350).pack(anchor="w", padx=24, pady=12)
        rewards = self.profile.round_rewards(round_id)
        total = sum(amount for title, amount in rewards)
        self.dialog_label(window, f"Заработано · {total} монет", 17, True).pack(
            anchor="w", padx=24, pady=(0, 8))
        lines = "\n".join(f"{title}  +{amount}" for title, amount in rewards)
        self.dialog_label(window, lines or "Следующая партия принесёт новые возможности.",
                          11, wraplength=350).pack(anchor="w", padx=24, pady=(0, 12))
        if self.profile.error:
            self.dialog_label(window, self.profile.error, 10,
                              wraplength=350).pack(anchor="w", padx=24)

        def new_round():
            self.close_dialog()
            self.restart()

        ttk.Button(window, text="Следующая партия", command=new_round).pack(
            fill="x", padx=24, pady=(0, 10))
        ttk.Button(window, text="Посмотреть поле", command=self.close_dialog).pack(
            fill="x", padx=24, pady=(0, 20))

    def combination_frame(self, progress, kind, target):
        if kind not in ("fire", "lightning") or not self.game.last_combinations:
            return
        fade = math.sin(math.pi*progress)
        if "thermal" in self.game.last_combinations and kind == "fire":
            x, y = self.cell_position(target)
            for i in range(12):
                px = x + (i % 4)*CELL/2 + math.sin(i+progress*3)*10
                py = y + CELL - progress*CELL + (i//4)*12
                radius = 8+progress*14
                color = self.blend("#e4f4f6", self.theme["empty"], fade*0.65)
                self.canvas.create_oval(px-radius, py-radius, px+radius, py+radius,
                                        fill=color, outline="", tags="effect")
        if "conductor" in self.game.last_combinations and kind == "lightning":
            first, second = target
            x1, y1 = self.cell_position(first)
            x2, y2 = self.cell_position(second)
            for i in range(1, 7):
                t = i/7
                x = x1+CELL/2+(x2-x1)*t
                y = y1+CELL/2+(y2-y1)*t
                self.canvas.create_line(
                    x-10, y+14, x+8, y, x+2, y-15,
                    fill=self.blend("#bcefff", self.theme["empty"], fade),
                    width=2, tags="effect")
        title = " + ".join(COMBINATIONS[value]["title"] for value in self.game.last_combinations)
        self.rounded_rect(10, WIDTH-36, WIDTH-10, WIDTH-7, 9, self.theme["card"], "effect")
        self.canvas.create_text(
            WIDTH/2, WIDTH-22, text=title, fill=self.theme["text"],
            font=("TkDefaultFont", 12, "bold"), tags="effect")

    def cancel_animation(self):
        if self.animation is not None:
            self.root.after_cancel(self.animation)
            self.animation = None
        self.pending_direction = None
        self.effect_running = False
        self.clear_selection()
        self.canvas.delete("effect")

    def restart(self):
        if self.dialog is not None:
            return
        self.cancel_animation()
        self.sync_progression()
        self.show_contracts()

    def start_round(self, contract=None):
        self.cancel_animation()
        self.game.reset(contract)
        self.result_round = None
        self.awaiting_contract = False
        self.notice_until = 0
        self.draw()
        self.root.focus_set()

    def close(self):
        self.cancel_animation()
        self.sync_progression()
        self.profile.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    GameWindow(root)
    root.mainloop()

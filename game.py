from random import choice, random


SIZE = 4
TARGET = 2048


def merge_line(line):
    """Сдвигает ряд к началу и возвращает новый ряд и очки за слияния."""
    tiles = [value for value in line if value != 0]
    merged = []
    points = 0
    index = 0

    while index < len(tiles):
        value = tiles[index]
        if index + 1 < len(tiles) and value == tiles[index + 1]:
            value *= 2
            points += value
            index += 2  # Обе исходные плитки уже использованы.
        else:
            index += 1
        merged.append(value)

    return merged + [0] * (len(line) - len(merged)), points


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[0] * SIZE for _ in range(SIZE)]
        self.score = 0
        self.charges = {"fire": 0, "ice": 0, "lightning": 0}
        self.rewarded = set()
        self.ice_moves = 0
        self.ice_just_ended = False
        self.game_over = False
        self.reached_target = False
        self.transitions = []
        self.merged_cells = set()
        self.spawned_cell = None
        self.add_tile()
        self.add_tile()

    def add_tile(self):
        empty = [
            (row, col)
            for row in range(SIZE)
            for col in range(SIZE)
            if self.board[row][col] == 0
        ]
        if empty:
            row, col = choice(empty)
            self.board[row][col] = 2 if random() < 0.9 else 4
            self.spawned_cell = (row, col)

    def move(self, direction):
        """Выполняет ход и возвращает True, если поле изменилось."""
        if direction not in ("left", "right", "up", "down"):
            raise ValueError(f"Неизвестное направление: {direction}")

        if self.game_over:
            return False
        self.ice_just_ended = False
        positions = range(SIZE)
        if direction in ("right", "down"):
            positions = reversed(range(SIZE))
        positions = list(positions)
        vertical = direction in ("up", "down")
        changed = False
        self.transitions = []
        self.merged_cells = set()
        self.spawned_cell = None

        for index in range(SIZE):
            # Читаем строку или столбец от края, к которому движутся плитки.
            if vertical:
                cells = [(position, index) for position in positions]
            else:
                cells = [(index, position) for position in positions]

            line = [self.board[row][col] for row, col in cells]
            merged, points = merge_line(line)
            occupied = [(cell, value) for cell, value in zip(cells, line) if value]
            source_index = 0
            for destination, value in zip(cells, merged):
                if value == 0:
                    break
                source, original = occupied[source_index]
                self.transitions.append((source, destination, original))
                source_index += 1
                if original != value:
                    source, original = occupied[source_index]
                    self.transitions.append((source, destination, original))
                    self.merged_cells.add(destination)
                    source_index += 1
            if merged != line:
                changed = True
                self.score += points
                for (row, col), value in zip(cells, merged):
                    self.board[row][col] = value

        if changed:
            self.award_elements()
            if self.ice_moves:
                self.ice_moves -= 1
                self.ice_just_ended = self.ice_moves == 0
            else:
                self.add_tile()
            self.reached_target = self.reached_target or any(
                TARGET in row for row in self.board
            )
        self.game_over = not self.can_move()
        return changed

    def can_move(self):
        for row in range(SIZE):
            for col in range(SIZE):
                value = self.board[row][col]
                if value == 0:
                    return True
                if col + 1 < SIZE and value == self.board[row][col + 1]:
                    return True
                if row + 1 < SIZE and value == self.board[row + 1][col]:
                    return True
        return False


    def award_elements(self):
        rewards = {128: ("lightning",), 256: ("fire",),
                   512: ("ice",), 1024: ("fire", "lightning")}
        created = {self.board[row][col] for row, col in self.merged_cells}
        for value in created:
            if value in rewards and value not in self.rewarded:
                self.rewarded.add(value)
                for element in rewards[value]:
                    limit = 1 if element == "ice" else 2
                    self.charges[element] = min(limit, self.charges[element] + 1)

    def available(self, element):
        return not self.game_over and self.can_move() and self.charges[element] > 0

    def use_fire(self, row, col):
        if not (0 <= row < SIZE - 1 and 0 <= col < SIZE - 1):
            return False
        if not self.available("fire"):
            return False
        targets = [(r, c) for r in range(row, row + 2)
                   for c in range(col, col + 2) if 0 < self.board[r][c] <= 32]
        if not targets:
            return False
        for r, c in targets:
            self.board[r][c] = 0
        self.charges["fire"] -= 1
        return True

    def use_ice(self):
        if not self.available("ice") or self.ice_moves:
            return False
        self.charges["ice"] -= 1
        self.ice_moves = 4
        return True

    def use_lightning(self, first, second):
        if not self.available("lightning"):
            return False
        for cell in (first, second):
            if len(cell) != 2 or not all(isinstance(i, int) and 0 <= i < SIZE for i in cell):
                return False
        r1, c1 = first
        r2, c2 = second
        if self.board[r1][c1] == 0 or self.board[r1][c1] == self.board[r2][c2]:
            return False
        self.board[r1][c1], self.board[r2][c2] = self.board[r2][c2], self.board[r1][c1]
        self.charges["lightning"] -= 1
        self.game_over = not self.can_move()
        return True

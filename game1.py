from random import choice, random


SIZE = 4
TARGET = 2048

def merge_line(line):

    tiles = [value for value in line if value != 0]
    merged = []
    points = 0
    index = 0

    while index < len(tiles):
        value = tiles[index]
        if index + 1 < len(tiles) and value == tiles[index + 1]:
            value *= 2
            points += value
            index += 2
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
        self.reached_target = False
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
    def move(self, direction):
        if direction not in ("left", "right", "up", "down"):
            raise ValueError(f"Неизвестное направление: {direction}")
        positions = range(SIZE)
        if direction in ("right", "down"):
            positions = reversed(range(SIZE))
        positions = list(positions)
        vertical = direction in ("up", "down")
        changed = False
        for index in range(SIZE):

            if vertical:
                cells = [(position, index) for position in positions]
            else:
                cells = [(index, position) for position in positions]

            line = [self.board[row][col] for row, col in cells]
            merged, points = merge_line(line)
            if merged != line:
                changed = True
                self.score += points
                for (row, col), value in zip(cells, merged):
                    self.board[row][col] = value

        if changed:
            self.add_tile()
            self.reached_target = self.reached_target or any(
                TARGET in row for row in self.board
            )
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

"""Профиль игрока, награды и покупки на стандартной библиотеке Python."""
from pathlib import Path
import sqlite3

from themes import THEMES

PROFILE_PATH = Path.home() / ".2048" / "profile.sqlite3"
TILE_REWARDS = {128: 5, 256: 10, 512: 20, 1024: 40, 2048: 80}
CONTRACTS = {
    "clean": {
        "title": "Чистая игра", "reward": 20,
        "description": "Собери 256 без применения стихий.",
    },
    "triple": {
        "title": "Тройное слияние", "reward": 15,
        "description": "Сделай хотя бы три слияния одним ходом.",
    },
    "fire": {
        "title": "Сила огня", "reward": 25,
        "description": "Уничтожь четыре плитки одной вспышкой.",
    },
    "ice": {
        "title": "Хладнокровие", "reward": 30,
        "description": "Заработай 128 очков за четыре хода одного льда.",
    },
    "arsenal": {
        "title": "Полный арсенал", "reward": 40,
        "description": "Примени все три стихии за одну партию.",
    },
}
COMBINATIONS = {
    "thermal": {
        "title": "Термошок",
        "description": "Примени огонь, пока действует лёд.",
    },
    "conductor": {
        "title": "Сверхпроводник",
        "description": "Примени молнию, пока действует лёд.",
    },
    "storm": {
        "title": "Огненная буря",
        "description": "Примени огонь и молнию подряд в любом порядке, без обычного хода между ними.",
    },
}


class Profile:
    def __init__(self, path=PROFILE_PATH):
        self.error = ""
        self.persistent = True
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(path, timeout=3)
            self.initialize()
        except (OSError, sqlite3.Error):
            # An inaccessible or damaged file is left in place for recovery.
            if hasattr(self, "connection"):
                self.connection.close()
            self.persistent = False
            self.error = "Профиль недоступен. Награды этой сессии не сохранятся."
            self.connection = sqlite3.connect(":memory:")
            self.initialize()

    def initialize(self):
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS wallet (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    coins INTEGER NOT NULL CHECK (coins >= 0),
                    theme TEXT NOT NULL
                );
                INSERT OR IGNORE INTO wallet VALUES (1, 0, 'classic');
                CREATE TABLE IF NOT EXISTS owned_themes (id TEXT PRIMARY KEY);
                INSERT OR IGNORE INTO owned_themes VALUES ('classic');
                CREATE TABLE IF NOT EXISTS rewards (
                    id TEXT PRIMARY KEY,
                    round_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    amount INTEGER NOT NULL CHECK (amount >= 0)
                );
                CREATE TABLE IF NOT EXISTS combinations (id TEXT PRIMARY KEY);
            """)

    @property
    def coins(self):
        return self.connection.execute("SELECT coins FROM wallet WHERE id=1").fetchone()[0]

    @property
    def theme(self):
        theme = self.connection.execute("SELECT theme FROM wallet WHERE id=1").fetchone()[0]
        return theme if theme in THEMES else "classic"

    def owned_themes(self):
        return {row[0] for row in self.connection.execute("SELECT id FROM owned_themes")}

    def discovered_combinations(self):
        return {row[0] for row in self.connection.execute("SELECT id FROM combinations")}

    def collect(self, round_id, events):
        """Выдаёт каждую награду ровно один раз даже после повторного вызова."""
        added = []
        try:
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                for event_id, title, amount, combination in events:
                    key = f"combo:{combination}" if combination else f"{round_id}:{event_id}"
                    cursor = self.connection.execute(
                        "INSERT OR IGNORE INTO rewards VALUES (?, ?, ?, ?)",
                        (key, round_id, title, amount),
                    )
                    if cursor.rowcount:
                        self.connection.execute(
                            "UPDATE wallet SET coins=coins+? WHERE id=1", (amount,))
                        if combination:
                            self.connection.execute(
                                "INSERT OR IGNORE INTO combinations VALUES (?)", (combination,))
                        added.append((title, amount))
            self.error = "" if self.persistent else "Профиль работает только до закрытия игры."
        except sqlite3.Error:
            self.error = "Не удалось сохранить награды. Повторим при следующем действии."
            return None
        return added

    def round_rewards(self, round_id):
        return list(self.connection.execute(
            "SELECT title, amount FROM rewards WHERE round_id=? ORDER BY rowid", (round_id,)))

    def buy(self, theme_id):
        if theme_id not in THEMES or not self.persistent:
            return False
        try:
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                if theme_id in self.owned_themes():
                    return True
                price = THEMES[theme_id]["price"]
                changed = self.connection.execute(
                    "UPDATE wallet SET coins=coins-? WHERE id=1 AND coins>=?", (price, price))
                if not changed.rowcount:
                    return False
                self.connection.execute("INSERT INTO owned_themes VALUES (?)", (theme_id,))
            self.error = ""
            return True
        except sqlite3.Error:
            self.error = "Покупка не сохранена. Монеты не списаны."
            return False

    def equip(self, theme_id):
        if theme_id not in THEMES or theme_id not in self.owned_themes():
            return False
        try:
            with self.connection:
                self.connection.execute("UPDATE wallet SET theme=? WHERE id=1", (theme_id,))
            return True
        except sqlite3.Error:
            self.error = "Не удалось сохранить выбранную тему."
            return False

    def close(self):
        self.connection.close()

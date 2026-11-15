import os
from pathlib import Path
import tempfile


RECORD_PATH = Path.home() / ".2048" / "high_score.txt"


def load_high_score(path=RECORD_PATH):
    """Возвращает рекорд или ноль, если сохранение недоступно."""
    try:
        return max(0, int(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return 0


def save_high_score(score, path=RECORD_PATH):
    """Атомарно заменяет файл рекорда и сообщает, удалось ли сохранение."""
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(str(max(score, load_high_score(path))))
        os.replace(temporary_path, path)
        return True
    except OSError:
        return False
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

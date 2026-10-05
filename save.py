"""save.py - Persistent progress and simple leaderboard (JSON file next to main.py)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict

from .config import SAVE_FILE


@dataclass
class SaveData:
    unlocked: int = 1                               # number of levels unlocked
    seen_tutorial: bool = False
    best_total: int = 0                             # highest total score in one session
    best_level_scores: Dict[str, int] = field(default_factory=dict)
    fewest_attempts: Dict[str, int] = field(default_factory=dict)
    fastest_completion: float = 0.0                 # seconds to finish the 7 main levels (0 = never)
    best_accuracy: int = 0                          # best single accuracy bonus
    completed: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def path(cls) -> str:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, SAVE_FILE)

    @classmethod
    def load(cls) -> "SaveData":
        try:
            with open(cls.path(), "r", encoding="utf-8") as f:
                raw = json.load(f)
            data = cls()
            for key, value in raw.items():
                if hasattr(data, key):
                    setattr(data, key, value)
            return data
        except (OSError, ValueError):
            return cls()

    def save(self) -> None:
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except OSError:
            pass

    def record_level_result(self, level_number: int, level_score: int, attempts: int, accuracy_bonus: int) -> None:
        key = str(level_number)
        self.completed[key] = True
        if level_score > self.best_level_scores.get(key, 0):
            self.best_level_scores[key] = level_score
        if key not in self.fewest_attempts or attempts < self.fewest_attempts[key]:
            self.fewest_attempts[key] = attempts
        self.best_accuracy = max(self.best_accuracy, accuracy_bonus)

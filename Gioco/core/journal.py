# =============================================================================
# core/journal.py — Diario di gioco del personaggio
# =============================================================================
from typing import List, Optional


# Categorie eventi con colore associato per la UI
EVENT_CATEGORIES = {
    "combat":    {"label": "Combattimento", "color": (220,  80,  80)},
    "discovery": {"label": "Scoperta",      "color": ( 80, 180, 255)},
    "item":      {"label": "Oggetto",       "color": (255, 180,  30)},
    "quest":     {"label": "Quest",         "color": (100, 220, 130)},
    "level":     {"label": "Livello",       "color": (200, 170, 255)},
    "death":     {"label": "Morte",         "color": (160, 160, 160)},
    "social":    {"label": "Sociale",       "color": (255, 220, 100)},
    "misc":      {"label": "Altro",         "color": (180, 180, 180)},
}


class JournalEntry:
    def __init__(self, day: int, age: int, text: str, category: str = "misc"):
        self.day      = day
        self.age      = age
        self.text     = text
        self.category = category if category in EVENT_CATEGORIES else "misc"

    def to_dict(self) -> dict:
        return {
            "day":      self.day,
            "age":      self.age,
            "text":     self.text,
            "category": self.category,
        }

    @staticmethod
    def from_dict(d: dict) -> "JournalEntry":
        return JournalEntry(
            day      = d.get("day", 1),
            age      = d.get("age", 0),
            text     = d.get("text", ""),
            category = d.get("category", "misc"),
        )

    def display_str(self) -> str:
        label = EVENT_CATEGORIES[self.category]["label"]
        return f"[Giorno {self.day} | Età {self.age}] [{label}] {self.text}"

    def color(self) -> tuple:
        return EVENT_CATEGORIES[self.category]["color"]


class Journal:
    MAX_ENTRIES = 200   # limite per non appesantire il save

    def __init__(self):
        self.entries: List[JournalEntry] = []

    def add(self, day: int, age: int, text: str, category: str = "misc"):
        entry = JournalEntry(day, age, text, category)
        self.entries.append(entry)
        if len(self.entries) > self.MAX_ENTRIES:
            self.entries.pop(0)
        return entry

    def get_by_category(self, category: str) -> List[JournalEntry]:
        return [e for e in self.entries if e.category == category]

    def get_significant(self) -> List[JournalEntry]:
        """Restituisce solo gli eventi che gli NPC potrebbero 'conoscere'."""
        notable = {"combat", "discovery", "quest", "level", "social"}
        return [e for e in self.entries if e.category in notable]

    def to_dict(self) -> dict:
        return {"entries": [e.to_dict() for e in self.entries]}

    @staticmethod
    def from_dict(d: dict) -> "Journal":
        j = Journal()
        j.entries = [JournalEntry.from_dict(e) for e in d.get("entries", [])]
        return j

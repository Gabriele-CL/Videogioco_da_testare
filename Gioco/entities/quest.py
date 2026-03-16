# =============================================================================
# quest.py — Struttura Quest e pool di missioni disponibili.
# =============================================================================

import random


class Quest:
    """
    Missione assegnata da un NPC al giocatore.

    Tipi obiettivo:
        "kill"    : uccidi N nemici di tipo obj_target
        "collect" : raccogli N oggetti con obj_target nel nome
    """

    def __init__(self, qid, title, desc, giver,
                 obj_type, obj_target, obj_count, reward_gold, reward_xp):
        self.qid         = qid           # ID univoco (es. "q1")
        self.title       = title         # titolo breve
        self.desc        = desc          # descrizione estesa
        self.giver       = giver         # nome NPC che assegna la quest
        self.obj_type    = obj_type      # tipo obiettivo ("kill"|"collect")
        self.obj_target  = obj_target    # bersaglio (es. "Wolf", "Herb")
        self.obj_count   = obj_count     # quantità necessaria
        self.current     = 0             # progresso attuale
        self.reward_gold = reward_gold
        self.reward_xp   = reward_xp
        self.completed   = False         # True quando current >= obj_count

    @property
    def progress_str(self) -> str:
        """Stringa progresso "attuale/totale" per HUD e quest log."""
        return f"{self.current}/{self.obj_count}"

    def to_dict(self) -> dict:
        """Serializza per il salvataggio JSON."""
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict) -> "Quest":
        """Ricostruisce da dizionario JSON, ripristinando il progresso."""
        q = Quest.__new__(Quest)
        q.__dict__.update(d)
        return q


# Pool di tutte le quest disponibili nel gioco
# Formato: (qid, title, desc, giver, obj_type, obj_target, obj_count, gold, xp)
QUEST_POOL = [
    ("q1", "Wolf Hunt",      "Kill 3 wolves in the wild.",   "Tormund", "kill",    "Wolf",    3, 25, 40),
    ("q2", "Goblin Slayer",  "Eliminate 5 goblins.",         "Brom",    "kill",    "Goblin",  5, 40, 60),
    ("q3", "Herb Collector", "Collect 3 Herb materials.",    "Lyra",    "collect", "Herb",    3, 15, 25),
    ("q4", "Ghost Buster",   "Banish 2 Ghosts.",             "Seera",   "kill",    "Ghost",   2, 50, 70),
    ("q5", "Crystal Seeker", "Collect 2 Crystal materials.", "Dwin",    "collect", "Crystal", 2, 30, 45),
    ("q6", "Bone Collector", "Collect 4 Bone materials.",    "Gruk",    "collect", "Bone",    4, 20, 30),
]


def make_random_quest() -> Quest:
    """Crea una Quest casuale dal pool. Chiamata alla creazione degli NPC."""
    return Quest(*random.choice(QUEST_POOL))

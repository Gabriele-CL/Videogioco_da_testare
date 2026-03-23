# =============================================================================
# core/constants.py
# =============================================================================

SCREEN_W = 1024
SCREEN_H = 600

TILE_W = 13
TILE_H = 18

VIEW_COLS = 61
VIEW_ROWS = 30

CHUNK_SIZE = 32
WORLD_LIMIT = 500
FPS = 30

# ── Tipi di tile ──────────────────────────────────────────────────────────────
GRASS    = 0
WALL     = 1
WATER    = 2
FOREST   = 3
ROAD     = 4
CHEST    = 5
FLOOR    = 6   # pavimento interno di un edificio
DOOR     = 7   # porta (attraversabile)
BUILDING = 8   # muro esterno edificio (non attraversabile)
DEN      = 9   # tana lupi (non attraversabile, spawn point)

TILE_CHAR = {
    GRASS:    "·",
    WALL:     "#",
    WATER:    "~",
    FOREST:   "T",
    ROAD:     "·",
    CHEST:    "§",
    FLOOR:    ",",
    DOOR:     "+",
    BUILDING: "#",
    DEN:      "W",   # tana lupi
}
TILE_COLOR = {
    GRASS:    (45, 160, 45),
    WALL:     (140, 130, 120),
    WATER:    (30, 144, 255),
    FOREST:   (0, 110, 0),
    ROAD:     (180, 155, 60),
    CHEST:    (200, 180, 0),
    FLOOR:    (160, 120, 80),
    DOOR:     (220, 160, 60),
    BUILDING: (170, 120, 70),
    DEN:      (180, 60, 40),
}
TILE_BG = {
    GRASS:    (8, 22, 8),
    WALL:     (22, 20, 18),
    WATER:    (0, 0, 60),
    FOREST:   (4, 18, 4),
    ROAD:     (38, 32, 12),
    CHEST:    (30, 20, 0),
    FLOOR:    (45, 30, 15),
    DOOR:     (50, 30, 10),
    BUILDING: (28, 18, 8),
    DEN:      (40, 10, 10),
}

# Caratteri direzionali muri edificio
WALL_H = "_"
WALL_V = "|"
WALL_C = "+"

# Raggio di sicurezza intorno alla città di partenza (no spawn nemici)
TOWN_SAFE_RADIUS = 40

RARITY_COLORS = {
    "common":    (200, 200, 200),
    "uncommon":  (30, 255, 30),
    "rare":      (50, 100, 255),
    "epic":      (180, 0, 255),
    "legendary": (255, 140, 0),
}

# ── Ciclo giorno/notte ────────────────────────────────────────────────────────
SECONDS_PER_GAME_HOUR_BASE  = 50   # 1 ora di gioco = 50s reali → 1 giorno = 20 min reali
SECONDS_PER_GAME_DAY_BASE   = SECONDS_PER_GAME_HOUR_BASE * 24

LIFE_STAGE_TIME_SCALE = {
    "CHILD": 0.235,
    "TEEN":  0.94,
    "ADULT": 2.12,
    "ELDER": 2.12,
}
LIFE_STAGE_AGES = {
    "CHILD": (0, 12),
    "TEEN":  (13, 17),
    "ADULT": (18, 60),
    "ELDER": (61, 999),
}
SECONDS_PER_GAME_DAY_REAL = 480
SECONDS_PER_YEAR = {
    "CHILD": SECONDS_PER_GAME_DAY_REAL * 365 * 0.05,
    "TEEN":  SECONDS_PER_GAME_DAY_REAL * 365 * 0.15,
    "ADULT": SECONDS_PER_GAME_DAY_REAL * 365 * 0.40,
    "ELDER": SECONDS_PER_GAME_DAY_REAL * 365 * 0.40,
}

SKY_COLORS = {
    "DAY":   (70, 120, 180),
    "DAWN":  (180, 80, 20),
    "DUSK":  (160, 60, 10),
    "NIGHT": (5, 5, 25),
}
NIGHT_OVERLAYS = {
    "DAY":   None,
    "DAWN":  ((255, 120, 0), 50),
    "DUSK":  ((200, 80, 0), 70),
    "NIGHT": ((0, 0, 80), 150),
}

NOISE_SCALE  = 0.04
NOISE_OCTAVE = 4

MOVE_DELAY = 0.13
ROT_SPEED  = 0.06

# ── ESSENZA — attributi stile SPECIAL ─────────────────────────────────────────
ESSENZA_ATTRS = ["Forza", "Agilità", "Intelligenza", "Resistenza", "Carisma", "Fortuna", "Percezione"]
ESSENZA_POINTS = 21          # punti totali da distribuire
ESSENZA_MIN    = 1           # minimo per attributo
ESSENZA_MAX    = 10          # massimo per attributo

# ── Edifici — tipi ────────────────────────────────────────────────────────────
BUILDING_TYPES = ["casa", "locanda", "bottega", "scuola", "bagno"]
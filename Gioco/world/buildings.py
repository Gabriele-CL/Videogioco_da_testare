# =============================================================================
# world/buildings.py
# =============================================================================
import random
from core.constants import (GRASS, WALL, WATER, FOREST, ROAD,
                             FLOOR, DOOR, BUILDING,
                             WALL_H, WALL_V, WALL_C,
                             TILE_CHAR, TILE_COLOR, TILE_BG)
from world.npc_behavior import NPCBehaviorEngine
from items.item import Item

# ── Tile arredo interno ───────────────────────────────────────────────────────
COUNTER = 10   # bancone (bloccante)
SHELF   = 11   # scaffale a muro (bloccante)
BARREL  = 12   # barile decorativo (bloccante)

TILE_CHAR[COUNTER]  = "=";  TILE_COLOR[COUNTER]  = (160,100,50); TILE_BG[COUNTER]  = (40,22,8)
TILE_CHAR[SHELF]    = ")";  TILE_COLOR[SHELF]    = (140, 80,40); TILE_BG[SHELF]    = (30,15,5)
TILE_CHAR[BARREL]   = "o";  TILE_COLOR[BARREL]   = (120, 80,40); TILE_BG[BARREL]   = (28,14,4)
TABLE   = 13   # tavolo locanda (bloccante)
TILE_CHAR[TABLE]    = "#";  TILE_COLOR[TABLE]    = (180,120,50); TILE_BG[TABLE]    = (50,28,8)


# =============================================================================
# Building
# =============================================================================
class Building:
    """Edificio rettangolare. Porta principale sul lato SUD centrata."""

    def __init__(self, wx, wy, w, h, btype="casa"):
        self.wx    = wx
        self.wy    = wy
        self.w     = w
        self.h     = h
        self.btype = btype

        self.door_x = wx + w // 2
        self.door_y = wy + h - 1

        self.sign_x     = self.door_x
        self.sign_y     = wy - 1
        self.sign_label = _sign_label(btype)

        self.furniture: dict = {}

        # Porta retro: parete divisoria interna (sovrascritta da furnish)
        self.back_door_x: int = wx + 8
        self.back_door_y: int = wy + 5
        # Zona riservata oste (locanda)
        self.innkeeper_zone: set = set()
        self.innkeeper_spawn: tuple = (wx + 4, wy + 2)
        self.table_seats: dict = {}

        # Zona riservata mercante (tile FLOOR ma forbidden per altri NPC)
        self.merchant_zone: set = set()

        # Gate bancone: tile che si apre/chiude
        self.counter_gate_x: int  = wx + 5
        self.counter_gate_y: int  = wy + 5
        self.counter_gate_open: bool = False  # chiuso di default (mercante è dietro)

        # Posizione spawn mercante (dietro bancone)
        self.merchant_spawn: tuple = (wx + 3, wy + 3)

    # ── Tile perimetrali ──────────────────────────────────────────────────────
    def tiles(self):
        result = {}
        for dy in range(self.h):
            for dx in range(self.w):
                x, y = self.wx + dx, self.wy + dy
                result[(x, y)] = WALL if (dy==0 or dy==self.h-1 or dx==0 or dx==self.w-1) else FLOOR
        result[(self.door_x, self.door_y)] = DOOR
        if self.btype in ("bottega", "locanda"):
            result[(self.back_door_x, self.back_door_y)] = DOOR
        return result

    def door_outside(self):
        return (self.door_x, self.door_y + 1)

    # ── Char muri ─────────────────────────────────────────────────────────────
    def wall_chars(self):
        result = {}
        for dy in range(self.h):
            for dx in range(self.w):
                x, y = self.wx + dx, self.wy + dy
                is_top    = dy == 0
                is_bottom = dy == self.h - 1
                is_left   = dx == 0
                is_right  = dx == self.w - 1
                if not (is_top or is_bottom or is_left or is_right):
                    continue
                if (x, y) in ((self.door_x, self.door_y),
                               (self.back_door_x, self.back_door_y)):
                    result[(x, y)] = WALL_C
                elif (is_top or is_bottom) and not (is_left or is_right):
                    result[(x, y)] = WALL_H
                elif (is_left or is_right) and not (is_top or is_bottom):
                    result[(x, y)] = WALL_V
                else:
                    result[(x, y)] = WALL_C
        return result

    # ── Tile interni camminabili (esclude furniture e merchant_zone) ──────────
    def interior_tiles(self):
        return [
            (self.wx + dx, self.wy + dy)
            for dy in range(1, self.h - 1)
            for dx in range(1, self.w - 1)
            if (self.wx+dx, self.wy+dy) not in self.furniture
            and (self.wx+dx, self.wy+dy) not in self.merchant_zone
        ]

    # ── Tile area cliente (camminabili, escluso retro bancone) ───────────────
    def customer_tiles(self):
        """Tile accessibili al player e NPC generici (esclusa merchant_zone)."""
        return self.interior_tiles()

    # ── Furniture ─────────────────────────────────────────────────────────────
    def furnish(self, world_tiles: dict, wall_chars: dict):
        if self.btype == "bottega":
            _furnish_bottega(self, world_tiles, wall_chars)
        elif self.btype == "locanda":
            _furnish_locanda(self, world_tiles, wall_chars)
        elif self.btype == "scuola_magia":
            _furnish_scuola_magia(self, world_tiles, wall_chars)
        elif self.btype == "palace":
            _furnish_palace(self, world_tiles, wall_chars)
        for pos, tid in self.furniture.items():
            world_tiles[pos] = tid




# =============================================================================
# _furnish_scuola_magia — aula con cattedra, banchi studenti, scaffali
# =============================================================================
def _furnish_scuola_magia(b: Building, world_tiles: dict, wall_chars: dict):
    if b.w < 12 or b.h < 10: return
    wx, wy = b.wx, b.wy

    # ── Scaffali nord-ovest (dx=1..2, dy=1) ──────────────────────────────────
    for dx in range(1, 3):
        pos = (wx+dx, wy+1)
        b.furniture[pos] = SHELF; wall_chars[pos] = ")"

    # ── Scaffali nord-est (dx=9..10, dy=1) ───────────────────────────────────
    for dx in range(9, 11):
        pos = (wx+dx, wy+1)
        b.furniture[pos] = SHELF; wall_chars[pos] = ")"

    # ── Cattedra professore (dx=4..6, dy=1) — tavolo largo ───────────────────
    for dx in range(4, 7):
        pos = (wx+dx, wy+1)
        b.furniture[pos] = TABLE; wall_chars[pos] = "="
        world_tiles[pos] = TABLE

    # ── Sedia/posto professore (dx=5, dy=2) — barile come segnaposto ─────────
    # Non mettiamo furniture qui: è lo spawn del maestro
    world_tiles[(wx+5, wy+2)] = FLOOR

    # ── Banchi studenti — 2 file, 4 colonne ──────────────────────────────────
    for dx in [2, 4, 6, 8]:
        # Fila 1 (dy=4)
        pos1 = (wx+dx, wy+4)
        b.furniture[pos1] = TABLE; wall_chars[pos1] = "="; world_tiles[pos1] = TABLE
        # Fila 2 (dy=6)
        pos2 = (wx+dx, wy+6)
        b.furniture[pos2] = TABLE; wall_chars[pos2] = "="; world_tiles[pos2] = TABLE

    # ── Scaffali / barili angoli sud ──────────────────────────────────────────
    b.furniture[(wx+1, wy+7)] = SHELF;  wall_chars[(wx+1, wy+7)] = ")"
    b.furniture[(wx+2, wy+7)] = SHELF;  wall_chars[(wx+2, wy+7)] = ")"
    b.furniture[(wx+9, wy+7)] = BARREL; wall_chars[(wx+9, wy+7)] = "o"
    b.furniture[(wx+10,wy+7)] = BARREL; wall_chars[(wx+10,wy+7)] = "o"

    # ── Barile decorativo lato ovest ──────────────────────────────────────────
    b.furniture[(wx+1, wy+4)] = BARREL; wall_chars[(wx+1, wy+4)] = "o"
    b.furniture[(wx+1, wy+6)] = BARREL; wall_chars[(wx+1, wy+6)] = "o"

    # ── Spawn maestro e zona magia ────────────────────────────────────────────
    b.magic_teacher_spawn = (wx+5, wy+2)
    # Zona davanti alla cattedra dove avviene il rituale
    b.magic_zone = set()
    for dy in range(2, 5):
        for dx in range(3, 8):
            pos = (wx+dx, wy+dy)
            if pos not in b.furniture:
                b.magic_zone.add(pos)
                world_tiles[pos] = FLOOR


def _furnish_palace(b: Building, world_tiles: dict, wall_chars: dict):
    if b.w < 18 or b.h < 14:
        return
    wx, wy = b.wx, b.wy

    # Corridoio d'ingresso centrale
    for dy in range(1, 11):
        pos = (wx + 8, wy + dy)
        if pos not in b.furniture:
            world_tiles[pos] = FLOOR

    # Sala del trono
    for dx in range(5, 13):
        for dy in range(1, 5):
            pos = (wx + dx, wy + dy)
            if pos not in b.furniture:
                world_tiles[pos] = FLOOR
    throne = (wx + 8, wy + 2)
    b.furniture[throne] = TABLE
    wall_chars[throne] = "#"
    world_tiles[throne] = TABLE

    # Camera da letto reale
    for dx in range(1, 6):
        for dy in range(5, 9):
            pos = (wx + dx, wy + dy)
            if pos not in b.furniture:
                world_tiles[pos] = FLOOR
    b.furniture[(wx + 2, wy + 6)] = BARREL
    wall_chars[(wx + 2, wy + 6)] = "o"
    b.furniture[(wx + 4, wy + 6)] = TABLE
    wall_chars[(wx + 4, wy + 6)] = "="
    world_tiles[(wx + 4, wy + 6)] = TABLE

    # Sala da pranzo
    for dx in range(12, 17):
        for dy in range(5, 9):
            pos = (wx + dx, wy + dy)
            if pos not in b.furniture:
                world_tiles[pos] = FLOOR
    for dx in range(13, 16):
        pos = (wx + dx, wy + 6)
        b.furniture[pos] = TABLE
        wall_chars[pos] = "#"
        world_tiles[pos] = TABLE

    # Corridoio posteriore con segrete e servitu'
    for dx in range(4, 14):
        pos = (wx + dx, wy + 10)
        if pos not in b.furniture:
            world_tiles[pos] = FLOOR
    # Aree laterali posteriori
    for dx in range(1, 5):
        for dy in range(10, 13):
            pos = (wx + dx, wy + dy)
            if pos not in b.furniture:
                world_tiles[pos] = FLOOR
    for dx in range(13, 17):
        for dy in range(10, 13):
            pos = (wx + dx, wy + dy)
            if pos not in b.furniture:
                world_tiles[pos] = FLOOR
    # Celle semplici
    for pos in [(wx + 2, wy + 11), (wx + 3, wy + 11), (wx + 14, wy + 11), (wx + 15, wy + 11)]:
        b.furniture[pos] = BARREL
        wall_chars[pos] = "o"

    b.throne_x = throne[0]
    b.throne_y = throne[1]
    b.palace_bed_x = wx + 2
    b.palace_bed_y = wy + 6
    b.palace_dining_x = wx + 14
    b.palace_dining_y = wy + 6


def place_capital_city(world_tiles: dict, wall_chars: dict, entities_list: list, cx: int, cy: int, rng=None):
    if rng is None:
        rng = random

    buildings = []
    wc_update = {}

    # Città ampia, pulita e senza rumore naturale all'interno
    city_r = 38
    for dy in range(-city_r, city_r + 1):
        for dx in range(-city_r, city_r + 1):
            world_tiles[(cx + dx, cy + dy)] = GRASS

    city_wall, city_wc = place_city_walls(world_tiles, cx, cy)
    wc_update.update(city_wc)

    # Palazzo reale al centro
    palace = Building(cx - 9, cy - 7, 18, 14, "palace")
    buildings.append(palace)
    for (tx, ty), tid in palace.tiles().items():
        world_tiles[(tx, ty)] = tid
    wc_update.update(palace.wall_chars())
    _furnish_palace(palace, world_tiles, wc_update)

    # Case ed edifici civili
    layout = [
        (-28, -18, "casa"),
        (-8, -20, "bottega"),
        (10, -20, "locanda"),
        (28, -16, "casa"),
        (-28, 4, "casa"),
        (28, 6, "ambulatorio"),
        (-14, 22, "scuola_magia"),
        (14, 22, "chiesa"),
    ]
    rng.shuffle(layout)
    for ox, oy, btype in layout:
        bw, bh = (10, 8)
        if btype in ("locanda", "scuola_magia"):
            bw, bh = (14, 10)
        elif btype == "chiesa":
            bw, bh = (12, 10)
        elif btype == "bottega":
            bw, bh = (14, 10)
        bx = cx + ox - bw // 2
        by = cy + oy - bh // 2
        b = Building(bx, by, bw, bh, btype)
        buildings.append(b)
        buf = 2
        for dy in range(-buf, bh + buf):
            for dx in range(-buf, bw + buf):
                world_tiles[(bx + dx, by + dy)] = GRASS
        for (tx, ty), tid in b.tiles().items():
            world_tiles[(tx, ty)] = tid
        wc_update.update(b.wall_chars())
        b.furnish(world_tiles, wc_update)

    wall_chars.update(wc_update)

    # NPC capitali: re, regina, amministratori, guardie
    spawn_capital_npcs(buildings, entities_list, world_tiles, cx, cy)
    spawn_village_npcs(buildings, entities_list, world_tiles)
    spawn_guards(city_wall, entities_list, world_tiles)
    return buildings, wc_update, city_wall


# =============================================================================
# Insegne
# =============================================================================
_SIGN_LABELS = {
    "bottega":      "[ BOTTEGA ]",
    "locanda":      "[ LOCANDA ]",
    "chiesa":       "[ CHIESA  ]",
    "ambulatorio":  "[ MEDICO  ]",
    "scuola_magia": "[ MAGIA   ]",
    "palace":       "[ PALAZZO ]",
    "casa":         "",
}
def _sign_label(btype): return _SIGN_LABELS.get(btype, "")


# =============================================================================
# _furnish_bottega — bancone a U + retro interno (parete a dx=8)
#
#  dy= 0  + _ _ _ _ _ _ _ _ # # # # # +
#  dy= 1  | . ) ) ) . . . # ) ) ) ) # |  scaffali | parete | scaffali retro
#  dy= 2  | = = = = . . . # . letto   |  bancone nord | parete | letto retro
#  dy= 3  | | M M M . . . # o o . . # |  bancone | zona M | parete | barili
#  dy= 4  | | M M M . . . # . . . . # |  bancone | zona M | parete | floor
#  dy= 5  | = = = = G . . + _ _ _ _ _ |  bancone sud + gate G | PORTA dx=8
#  dy= 6  | . . . . . . . . . . . . . |  area cliente
#  dy= 7  | . . . . . . . . . . . . . |
#  dy= 8  | . . . . . . . . . . . . . |
#  dy= 9  + _ _ _ _ _ D _ _ _ _ _ _ _ +
# =============================================================================
def _furnish_bottega(b: Building, world_tiles: dict, wall_chars: dict):
    if b.w < 13 or b.h < 9: return
    wx, wy = b.wx, b.wy

    # Parete divisoria verticale dx=8, dy=1..5 — back_door a dy=3
    for dy in range(1, 6):
        pos = (wx + 8, wy + dy)
        if dy == 3:
            world_tiles[pos] = DOOR
            wall_chars[pos]  = WALL_C
            b.back_door_x    = wx + 8
            b.back_door_y    = wy + 3
        else:
            world_tiles[pos] = WALL
            wall_chars[pos]  = WALL_V

    # Muro sud del retro (dy=5, dx=8..12)
    for dx in range(8, 13):
        pos = (wx + dx, wy + 5)
        world_tiles[pos] = WALL
        wall_chars[pos]  = WALL_H

    # Scaffali nord negozio (dy=1, dx=1..4)
    for dx in range(1, 5):
        pos = (wx + dx, wy + 1)
        b.furniture[pos] = SHELF
        wall_chars[pos]  = ")"

    # Bancone nord (dy=2, dx=1..4)
    for dx in range(1, 5):
        pos = (wx + dx, wy + 2)
        b.furniture[pos] = COUNTER
        wall_chars[pos]  = "="

    # Bancone lato sinistro (dy=2..5, dx=1)
    for dy in range(2, 6):
        pos = (wx + 1, wy + dy)
        b.furniture[pos] = COUNTER
        wall_chars[pos]  = "|"

    # Bancone lato destro (dy=2 e dy=4, dx=5) — dy=3 è il gate
    for dy in [2, 4]:
        pos = (wx + 5, wy + dy)
        b.furniture[pos] = COUNTER
        wall_chars[pos]  = "|"

    # Bancone sud (dy=5, dx=1..5)
    for dx in range(1, 6):
        pos = (wx + dx, wy + 5)
        b.furniture[pos] = COUNTER
        wall_chars[pos]  = "="

    # Gate (dy=3, dx=5) — allineato con merchant_zone per percorso diretto
    gate_x = wx + 5; gate_y = wy + 3
    b.counter_gate_x = gate_x; b.counter_gate_y = gate_y; b.counter_gate_open = False
    world_tiles[(gate_x, gate_y)] = COUNTER
    wall_chars[(gate_x, gate_y)]  = "|"

    # Zona mercante (dy=3..4, dx=2..4)
    for dy in range(3, 5):
        for dx in range(2, 5):
            pos = (wx + dx, wy + dy)
            b.merchant_zone.add(pos)
            world_tiles[pos] = FLOOR
    b.merchant_spawn = (wx + 3, wy + 3)

    # Scaffali retro (dy=1, dx=9..12)
    for dx in range(9, 13):
        pos = (wx + dx, wy + 1)
        b.furniture[pos] = SHELF
        wall_chars[pos]  = ")"

    # Letto retro (dy=2, dx=9..10)
    for dx in range(9, 11):
        pos = (wx + dx, wy + 2)
        b.furniture[pos] = BARREL
        wall_chars[pos]  = "="

    # Barili retro (dy=3, dx=9..10)
    for dx in range(9, 11):
        pos = (wx + dx, wy + 3)
        b.furniture[pos] = BARREL
        wall_chars[pos]  = "o"

    # Floor retro libero
    for dy in range(2, 5):
        for dx in range(11, 13):
            pos = (wx + dx, wy + dy)
            if pos not in b.furniture:
                world_tiles[pos] = FLOOR
    for dx in range(9, 13):
        pos = (wx + dx, wy + 4)
        if pos not in b.furniture:
            world_tiles[pos] = FLOOR



# =============================================================================
# _furnish_locanda — bancone a U chiuso + retro + tavoli
# =============================================================================
def _furnish_locanda(b: Building, world_tiles: dict, wall_chars: dict):
    if b.w < 14 or b.h < 9: return
    wx, wy = b.wx, b.wy
    # Nota: muri perimetrali a dx=0, dx=b.w-1=13, dy=0, dy=b.h-1=9
    # Tile interni validi: dx=1..12, dy=1..8

    # ── Bancone a U attorno alla zona oste (dx=2..7, dy=2..3) ────────────
    # Nord (dy=1, dx=1..7)
    for dx in range(1, 8):
        pos = (wx+dx, wy+1)
        b.furniture[pos] = COUNTER; wall_chars[pos] = "="
    # Lato sinistro (dx=1, dy=2..3)
    for dy in range(2, 4):
        pos = (wx+1, wy+dy)
        b.furniture[pos] = COUNTER; wall_chars[pos] = "|"
    # Lato destro (dx=8, dy=1,3) — dy=2 è il gate
    for dy in [1, 3]:
        pos = (wx+8, wy+dy)
        b.furniture[pos] = COUNTER; wall_chars[pos] = "|"
    # Sud (dy=3, dx=1..7)
    for dx in range(1, 8):
        pos = (wx+dx, wy+3)
        b.furniture[pos] = COUNTER; wall_chars[pos] = "="

    # ── Gate (dx=8, dy=2) ─────────────────────────────────────────────────
    gate_x = wx+8; gate_y = wy+2
    b.counter_gate_x = gate_x; b.counter_gate_y = gate_y; b.counter_gate_open = False
    world_tiles[(gate_x, gate_y)] = COUNTER
    wall_chars[(gate_x, gate_y)]  = "|"

    # ── Zona oste (dietro il bancone + corridoio verso retro) ─────────────
    # Zona bancone: dx=2..7, dy=2 (1 riga sola — bancone ridotto)
    for dx in range(2, 8):
        pos = (wx+dx, wy+2)
        b.innkeeper_zone.add(pos); world_tiles[pos] = FLOOR
    # Corridoio retro: dx=9..10, dy=1..3
    for dy in range(1, 4):
        for dx in range(9, 11):
            pos = (wx+dx, wy+dy)
            b.innkeeper_zone.add(pos); world_tiles[pos] = FLOOR
    b.innkeeper_spawn = (wx+4, wy+2)

    # ── Parete divisoria (dx=11, dy=1..3) — back_door a dy=2 ─────────────
    for dy in range(1, 4):
        pos = (wx+11, wy+dy)
        if dy == 2:
            world_tiles[pos] = DOOR; wall_chars[pos] = WALL_C
            b.back_door_x = wx+11; b.back_door_y = wy+2
        else:
            world_tiles[pos] = WALL; wall_chars[pos] = WALL_V

    # ── Stanza retro (dx=12, dy=1..3) ─────────────────────────────────────
    # Solo dx=12 — dx=13 è il muro perimetrale, NON toccare
    b.furniture[(wx+12, wy+1)] = SHELF;  wall_chars[(wx+12, wy+1)] = ")"
    world_tiles[(wx+12, wy+2)] = FLOOR   # tile dove l'oste dorme
    b.furniture[(wx+12, wy+3)] = BARREL; wall_chars[(wx+12, wy+3)] = "o"
    # Muro sud della stanza retro a dy=3 lato dx=11..12 già muro perimetrale
    # Aggiungiamo muro interno che chiude la stanza in basso
    world_tiles[(wx+11, wy+3)] = WALL; wall_chars[(wx+11, wy+3)] = WALL_V
    # (wx+11,wy+3) era già WALL dalla parete div — ok

    # ── Tavoli area cliente (dy=4..8) ────────────────────────────────────
    b.table_seats = {}
    for (tx, ty) in [(wx+2,wy+5),(wx+6,wy+5),(wx+3,wy+7),(wx+8,wy+7)]:
        b.furniture[(tx,ty)] = TABLE; wall_chars[(tx,ty)] = "#"
        world_tiles[(tx,ty)] = TABLE
        seats = []
        for ddx,ddy in [(0,-1),(0,1),(-1,0),(1,0)]:
            sx,sy = tx+ddx, ty+ddy
            if (sx,sy) not in b.furniture and world_tiles.get((sx,sy), FLOOR) == FLOOR:
                seats.append((sx,sy))
        b.table_seats[(tx,ty)] = seats


# =============================================================================
# Tipi edificio
# =============================================================================
BUILDING_TYPES = [
    ("casa",        10,  8),
    ("casa",        10,  8),
    ("casa",        10,  8),
    ("locanda",     14, 10),
    ("bottega",     14, 10),
    ("chiesa",      12, 10),
    ("ambulatorio", 10,  8),
    ("scuola_magia",12, 10),
]

VILLAGE_BUILDING_TYPES = [
    ("casa",     8,  6),
    ("casa",     8,  6),
    ("casa",     8,  6),
]


# =============================================================================
# CityWall
# =============================================================================
class CityWall:
    def __init__(self, cx, cy, half_w, half_h):
        self.cx = cx; self.cy = cy
        self.x0 = cx - half_w; self.y0 = cy - half_h
        self.x1 = cx + half_w; self.y1 = cy + half_h
        self.gate_n = (cx, self.y0)
        self.gate_s = (cx, self.y1)

    def tiles(self):
        result = {}
        x0,y0,x1,y1 = self.x0,self.y0,self.x1,self.y1
        for x in range(x0, x1+1): result[(x,y0)] = WALL; result[(x,y1)] = WALL
        for y in range(y0, y1+1): result[(x0,y)] = WALL; result[(x1,y)] = WALL
        for (tx,ty) in [(x0,y0),(x1,y0),(x0,y1),(x1,y1)]:
            for dy in range(-1,2):
                for dx in range(-1,2): result[(tx+dx,ty+dy)] = WALL
        for dx in range(-1,2):
            result[(self.cx+dx,y0)] = DOOR
            result[(self.cx+dx,y1)] = DOOR
        return result

    def wall_chars(self):
        result = {}
        x0,y0,x1,y1 = self.x0,self.y0,self.x1,self.y1
        for x in range(x0,x1+1):
            for y in [y0,y1]: result[(x,y)] = WALL_H
        for y in range(y0,y1+1):
            for x in [x0,x1]: result[(x,y)] = WALL_V
        for (tx,ty) in [(x0,y0),(x1,y0),(x0,y1),(x1,y1)]:
            for dy in range(-1,2):
                for dx in range(-1,2): result[(tx+dx,ty+dy)] = "T"
        for dx in range(-1,2):
            result[(self.cx+dx,y0)] = WALL_C
            result[(self.cx+dx,y1)] = WALL_C
        return result

    def is_inside(self, wx, wy): return self.x0 < wx < self.x1 and self.y0 < wy < self.y1
    def gate_outside_n(self): return (self.cx, self.y0-1)
    def gate_outside_s(self): return (self.cx, self.y1+1)
    def gate_inside_s(self):  return (self.cx, self.y1-2)


# =============================================================================
# place_starting_town
# =============================================================================
def place_starting_town(world_tiles: dict, cx: int, cy: int):
    buildings  = []
    wall_chars = {}

    town_r = 60
    for dy in range(-town_r, town_r+1):
        for dx in range(-town_r, town_r+1):
            world_tiles[(cx+dx, cy+dy)] = GRASS

    layout = [
        (-28,-22),(0,-22),(28,-22),
        (-28,  0),(0,  0),(28,  0),
        (-14, 22),(14, 22),
    ]

    for i, (btype, bw, bh) in enumerate(BUILDING_TYPES):
        ox, oy = layout[i]
        bx = cx + ox - bw//2
        by = cy + oy - bh//2
        b  = Building(bx, by, bw, bh, btype)
        buildings.append(b)

        buf = 3
        for dy in range(-buf, bh+buf):
            for dx in range(-buf, bw+buf):
                tx, ty = bx+dx, by+dy
                if world_tiles.get((tx,ty)) != FLOOR:
                    world_tiles[(tx,ty)] = GRASS

        for (tx,ty), tid in b.tiles().items():
            world_tiles[(tx,ty)] = tid
        wall_chars.update(b.wall_chars())
        b.furnish(world_tiles, wall_chars)

        ox2, oy2 = b.door_outside()
        for step in range(5):
            world_tiles[(ox2, oy2+step)] = GRASS

    return buildings, wall_chars


# =============================================================================
# place_city_walls
# =============================================================================
def place_city_walls(world_tiles: dict, cx: int, cy: int):
    wall       = CityWall(cx, cy, half_w=46, half_h=38)
    wall_chars = {}
    for (tx,ty), tid in wall.tiles().items():
        world_tiles[(tx,ty)] = tid
    wall_chars.update(wall.wall_chars())
    for step in range(1, 6):
        for ddx in range(-1, 2):
            world_tiles[(cx+ddx, wall.y0-step)] = GRASS
            world_tiles[(cx+ddx, wall.y1+step)] = GRASS
    return wall, wall_chars


# =============================================================================
# place_village
# =============================================================================
def place_village(world_tiles: dict, wall_chars: dict, cx: int, cy: int, rng=None):
    if rng is None: rng = random
    buildings = []; wc_update = {}

    n_buildings = rng.randint(3, 5)
    types = rng.sample(VILLAGE_BUILDING_TYPES, min(n_buildings, len(VILLAGE_BUILDING_TYPES)))
    if n_buildings > len(types):
        types += [("casa", 8, 6)] * (n_buildings - len(types))

    vr = 20
    for dy in range(-vr,vr+1):
        for dx in range(-vr,vr+1):
            world_tiles[(cx+dx, cy+dy)] = GRASS

    offsets = [(-12,-10),(0,-10),(12,-10),(-10,6),(6,6),(14,6)]
    rng.shuffle(offsets)

    for i, (btype, bw, bh) in enumerate(types):
        if i >= len(offsets): break
        ox, oy = offsets[i]
        bx = cx+ox-bw//2; by = cy+oy-bh//2
        b = Building(bx, by, bw, bh, btype)
        buildings.append(b)
        buf = 2
        for dy in range(-buf,bh+buf):
            for dx in range(-buf,bw+buf):
                world_tiles[(bx+dx,by+dy)] = GRASS
        for (tx,ty), tid in b.tiles().items():
            world_tiles[(tx,ty)] = tid
        wc_update.update(b.wall_chars())
        b.furnish(world_tiles, wc_update)
        ox2,oy2 = b.door_outside()
        for step in range(4): world_tiles[(ox2,oy2+step)] = GRASS

    wall_chars.update(wc_update)
    return buildings, wc_update


# =============================================================================
# NPC helpers
# =============================================================================
from entities.entity import Entity
from items.item import ITEM_GEN

NPC_TYPES = {
    "merchant":    {"symbol":"M","color":(200,160,60), "ai":"merchant",  "name":"Mercante",
                    "dialogue":"Cosa posso fare per te?","prefers":["bottega"],"role":"merchant"},
    "oste":        {"symbol":"O","color":(180,120,40), "ai":"innkeeper", "name":"Oste",
                    "dialogue":"Benvenuto alla locanda!","prefers":["locanda"],"role":"oste"},
    "popolano":    {"symbol":"p","color":(160,200,160),"ai":"wander",    "name":"Popolano",
                    "dialogue":"Buona giornata!",        "prefers":[],          "role":"popolano"},
    "contadino":   {"symbol":"c","color":(180,200,100),"ai":"wander",    "name":"Contadino",
                    "dialogue":"I campi non si arano da soli!","prefers":["casa"],"role":"contadino"},
    "fabbro":      {"symbol":"f","color":(200,140,80), "ai":"wander",    "name":"Fabbro",
                    "dialogue":"Hai bisogno di un'arma affilata?","prefers":["bottega"],"role":"fabbro"},
    "bambino":     {"symbol":"b","color":(220,220,120),"ai":"wander",    "name":"Bambino",
                    "dialogue":"Vuoi giocare con me?",  "prefers":["casa"],"role":"bambino"},
    "anziano":     {"symbol":"a","color":(180,180,200),"ai":"wander",    "name":"Anziano",
                    "dialogue":"Ai miei tempi le cose erano diverse...","prefers":["casa"],"role":"anziano"},
    "prete":       {"symbol":"r","color":(220,220,255),"ai":"wander",    "name":"Prete",
                    "dialogue":"La luce ti guidi, figlio mio.","prefers":["chiesa"],"role":"prete"},
    "guaritore":   {"symbol":"g","color":(100,220,180),"ai":"wander",    "name":"Guaritore",
                    "dialogue":"Ho erbe per ogni male.","prefers":["ambulatorio"],"role":"guaritore"},
    "ins_magia":   {"symbol":"~","color":(180,100,255),"ai":"wander",    "name":"Maestro di Magia",
                    "dialogue":"La magia e' nell'anima, non nelle parole.","prefers":["scuola_magia"],"role":"ins_magia"},
    "cacciatore":  {"symbol":"h","color":(160,130,80), "ai":"wander",    "name":"Cacciatore",
                    "dialogue":"Ho visto lupi enormi nel bosco.","prefers":["casa"],"role":"cacciatore"},
    "taglialegna": {"symbol":"t","color":(140,100,60), "ai":"wander",    "name":"Taglialegna",
                    "dialogue":"Il bosco e' pieno di legna buona.","prefers":["casa"],"role":"taglialegna"},
    "minatore":    {"symbol":"m","color":(150,150,160),"ai":"wander",    "name":"Minatore",
                    "dialogue":"La pietra non mente mai.","prefers":["casa"],"role":"minatore"},
    "guardia_civ": {"symbol":"G","color":(200,200,80), "ai":"guard",     "name":"Guardia Civile",
                    "dialogue":"Tengo d'occhio le strade.","prefers":[],"role":"guardia_civ"},
    "guardia":     {"symbol":"G","color":(180,180,60), "ai":"guard",     "name":"Guardia",
                    "dialogue":"Alt! Chi va là?","prefers":[],"role":"guardia"},
}

VILLAGE_NPCS = [
    ("merchant",1),("oste",1),("prete",1),("guaritore",1),("ins_magia",1),
    ("contadino",2),("fabbro",1),("bambino",2),("anziano",1),
    ("cacciatore",1),("taglialegna",1),("minatore",1),
    ("guardia_civ",2),("popolano",3),
]
VILLAGE_NPCS_SMALL = [("popolano",3)]


def _building_of_type(buildings, *btypes):
    matches = [b for b in buildings if b.btype in btypes]
    return random.choice(matches) if matches else None

def _rarity_for_level(level):
    if level>=10: return "legendary"
    if level>=7:  return "epic"
    if level>=5:  return "rare"
    if level>=3:  return "uncommon"
    return "common"


def _make_npc(info: dict, pos: tuple, buildings: list) -> Entity:
    e = Entity.__new__(Entity)
    e.x, e.y         = pos
    e.name            = info["name"]
    e.symbol          = info["symbol"]
    e.color           = info["color"]
    e.ai_type         = info["ai"]
    e.alive           = True
    e.health = e.max_health = 20
    e.damage = e.defense = 0
    e.level           = 1
    e.dialogue        = info["dialogue"]
    e.gold            = 0
    e.shop            = []
    e.home_x          = pos[0]
    e.home_y          = pos[1]
    e.home_radius     = 6
    e.npc_role        = info.get("role","")
    e.sleep_x         = None
    e.sleep_y         = None
    e.outdoor_dest_set = False

    work_b = _building_of_type(buildings, *info.get("prefers",[])) if info.get("prefers") else None
    if work_b:
        e.work_x = work_b.wx + work_b.w//2
        e.work_y = work_b.wy + work_b.h//2
    else:
        e.work_x = pos[0]; e.work_y = pos[1]
    e.work_radius = 5

    tavern_b = _building_of_type(buildings, "locanda")
    if tavern_b:
        e.tavern_x = tavern_b.wx + tavern_b.w//2
        e.tavern_y = tavern_b.wy + tavern_b.h//2
    else:
        e.tavern_x = pos[0]; e.tavern_y = pos[1]

    if info.get("role") == "merchant":
        e.gold          = random.randint(100, 300)
        e.level         = random.randint(1, 6)
        shop_size       = max(3, e.level//2+2)
        e.shop          = [ITEM_GEN.generate_merchant_item(_rarity_for_level(e.level))
                           for _ in range(shop_size)]
        e.exits_today      = 0
        e.daily_roll       = 0
        e.is_outside       = False
        e.chest_radius     = 40
        e.shop_door_locked = False
        e.found_items      = []
    elif info.get("role") == "oste":
        e.gold  = random.randint(50, 150)
        e.level = random.randint(1, 4)
        e.shop  = [ITEM_GEN.generate_innkeeper_item(_rarity_for_level(e.level)) for _ in range(4)]

    NPCBehaviorEngine.configure_npc(e, buildings)
    return e


def _equip_guard(e: Entity, elite: bool = False):
    if elite:
        sword = Item("Royal Sword", "weapon", "/", "rare", {"damage": 14, "crit_chance": 0.08}, "Sword of the royal guard", 120)
        armor = Item("Royal Armor", "armor", "[", "rare", {"defense": 8}, "Armor of the royal guard", 160)
        helm = Item("Royal Helm", "helmet", "^", "rare", {"defense": 4}, "Helm of the royal guard", 90)
        legs = Item("Royal Greaves", "legs", "L", "rare", {"defense": 4}, "Greaves of the royal guard", 90)
        shield = Item("Royal Shield", "shield", "O", "rare", {"defense": 5}, "Shield of the royal guard", 80)
        boots = Item("Royal Boots", "boots", "v", "rare", {"defense": 2}, "Boots of the royal guard", 40)
    else:
        sword = Item("Steel Sword", "weapon", "/", "uncommon", {"damage": 10, "crit_chance": 0.05}, "Sword for a city guard", 70)
        armor = Item("Chain Armor", "armor", "[", "uncommon", {"defense": 5}, "Armor for a city guard", 80)
        helm = Item("Iron Helm", "helmet", "^", "common", {"defense": 2}, "Helmet for a city guard", 30)
        legs = Item("Guard Leggings", "legs", "L", "common", {"defense": 2}, "Leg protection", 30)
        shield = Item("Wooden Shield", "shield", "O", "common", {"defense": 2}, "Shield for a city guard", 25)
        boots = Item("Leather Boots", "boots", "v", "common", {"defense": 1}, "Boots for a city guard", 20)
    e.equipped_weapon = sword
    e.equipped_armor = armor
    e.equipped_head = helm
    e.equipped_legs = legs
    e.equipped_shield = shield
    e.equipped_boots = boots
    e.damage = sword.stats.get("damage", e.damage)
    e.defense = armor.stats.get("defense", 0) + helm.stats.get("defense", 0) + legs.stats.get("defense", 0) + shield.stats.get("defense", 0) + boots.stats.get("defense", 0)


# =============================================================================
# spawn_village_npcs
# Regola chiave: il fabbro e qualsiasi NPC NON-mercante NON può spawnare
# nella merchant_zone della bottega (né camminarci sopra — gestito in main.py)
# =============================================================================
def spawn_village_npcs(buildings, entities_list, world_tiles):
    if not buildings: return

    # Tile vietati: porte, tile davanti alle porte, merchant_zone di ogni bottega
    forbidden = set()
    for b in buildings:
        forbidden.add((b.door_x, b.door_y))
        dx, dy = b.door_outside()
        forbidden.add((dx, dy)); forbidden.add((dx, dy+1))
        if b.btype == "bottega":
            forbidden |= b.merchant_zone
            forbidden.add((b.back_door_x, b.back_door_y))
        if b.btype == "locanda":
            forbidden |= getattr(b, "innkeeper_zone", set())
            if hasattr(b, "back_door_x"): forbidden.add((b.back_door_x, b.back_door_y))

    occupied = {(e.x, e.y) for e in entities_list}

    for npc_type, count in VILLAGE_NPCS:
        info = NPC_TYPES[npc_type]
        for _ in range(count):
            pos = None

            # Mercante: spawna nella merchant_spawn della bottega
            if npc_type == "merchant":
                bottega = _building_of_type(buildings, "bottega")
                if bottega and bottega.merchant_spawn not in occupied:
                    pos = bottega.merchant_spawn
            # Oste: spawna nella innkeeper_spawn della locanda
            elif npc_type == "oste":
                locanda = _building_of_type(buildings, "locanda")
                if locanda and hasattr(locanda, "innkeeper_spawn"):
                    sp = locanda.innkeeper_spawn
                    if sp not in occupied: pos = sp

            # Altri NPC: tile interni del loro edificio preferito (esclusa merchant_zone)
            if pos is None and info["prefers"]:
                bldg = _building_of_type(buildings, *info["prefers"])
                if bldg:
                    interior = [t for t in bldg.interior_tiles()
                                 if t not in occupied and t not in forbidden]
                    if interior:
                        pos = random.choice(interior)

            # Fallback: GRASS libero intorno alla città
            if pos is None:
                b0  = buildings[0]
                cx0 = b0.wx + b0.w//2
                cy0 = b0.wy + b0.h//2
                for _ in range(80):
                    rx = cx0 + random.randint(-20, 20)
                    ry = cy0 + random.randint(-20, 20)
                    if ((rx,ry) not in occupied and (rx,ry) not in forbidden
                            and world_tiles.get((rx,ry), GRASS) == GRASS):
                        pos = (rx, ry); break

            if pos is None: continue
            e = _make_npc(info, pos, buildings)
            occupied.add(pos)
            entities_list.append(e)


def spawn_guards(city_wall, entities_list, world_tiles):
    from entities.entity import Entity
    occupied = {(e.x,e.y) for e in entities_list}

    def make_guard(x, y, patrol_x, patrol_y):
        e = Entity.__new__(Entity)
        e.x,e.y          = x,y
        e.name            = "Guardia"
        e.symbol          = "G"
        e.color           = (200,200,60)
        e.ai_type         = "guard"
        e.alive           = True
        e.health = e.max_health = 50
        e.damage          = 12
        e.defense         = 5
        e.level           = random.randint(3,7)
        e.dialogue        = "Alt! Chi va là?"
        e.gold            = random.randint(10,30)
        e.shop            = []
        e.home_x          = patrol_x
        e.home_y          = patrol_y
        e.home_radius     = 8
        e.patrol_x        = patrol_x
        e.patrol_y        = patrol_y
        e.is_gate_guard   = False
        e.guard_stage     = 0
        e.npc_role        = "guardia"
        e.sleep_x         = None
        e.sleep_y         = None
        e.outdoor_dest_set = False
        _equip_guard(e, elite=False)
        return e

    # Guardie porta Nord: fuori (gn_y-1), flangiano l'ingresso
    gn_x,gn_y = city_wall.gate_n
    for dx in [-2, 2]:
        pos = (gn_x+dx, gn_y-1)
        if pos not in occupied and world_tiles.get(pos, GRASS) in (GRASS, FLOOR):
            g = make_guard(pos[0], pos[1], pos[0], pos[1])
            g.is_gate_guard = True
            entities_list.append(g); occupied.add(pos)

    # Guardie porta Sud: fuori (gs_y+1), flangiano l'ingresso
    gs_x,gs_y = city_wall.gate_s
    for dx in [-2, 2]:
        pos = (gs_x+dx, gs_y+1)
        if pos not in occupied and world_tiles.get(pos, GRASS) in (GRASS, FLOOR):
            g = make_guard(pos[0], pos[1], pos[0], pos[1])
            g.is_gate_guard = True
            entities_list.append(g); occupied.add(pos)

    for px,py in [(city_wall.x0+6,city_wall.y0+2),(city_wall.x1-6,city_wall.y0+2),
                  (city_wall.x0+6,city_wall.y1-2),(city_wall.x1-6,city_wall.y1-2)]:
        for ddx,ddy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
            pos=(px+ddx,py+ddy)
            if pos not in occupied and world_tiles.get(pos,GRASS) in (GRASS,FLOOR):
                entities_list.append(make_guard(pos[0],pos[1],px,py))
                occupied.add(pos); break


def spawn_village_npcs_small(buildings, entities_list, world_tiles, cx, cy):
    if not buildings: return

    forbidden = set()
    for b in buildings:
        forbidden.add((b.door_x,b.door_y))
        dx,dy = b.door_outside()
        forbidden.add((dx,dy))
        if b.btype=="bottega": forbidden |= b.merchant_zone

    occupied = {(e.x,e.y) for e in entities_list}
    has_bottega = any(b.btype=="bottega" for b in buildings)
    npc_list = list(VILLAGE_NPCS_SMALL)
    if has_bottega: npc_list = [("merchant",1)] + npc_list

    for npc_type, count in npc_list:
        info = NPC_TYPES[npc_type]
        for _ in range(count):
            pos = None
            if npc_type == "merchant":
                bottega = _building_of_type(buildings, "bottega")
                if bottega and bottega.merchant_spawn not in occupied:
                    pos = bottega.merchant_spawn
            if pos is None and info["prefers"]:
                bldg = _building_of_type(buildings, *info["prefers"])
                if bldg:
                    interior=[t for t in bldg.interior_tiles()
                               if t not in occupied and t not in forbidden]
                    if interior: pos=random.choice(interior)
            if pos is None:
                for _ in range(60):
                    rx=cx+random.randint(-14,14); ry=cy+random.randint(-14,14)
                    if ((rx,ry) not in occupied and (rx,ry) not in forbidden
                            and world_tiles.get((rx,ry),GRASS)==GRASS):
                        pos=(rx,ry); break
            if pos is None: continue
            e=_make_npc(info,pos,buildings)
            occupied.add(pos); entities_list.append(e)


# =============================================================================
# spawn_capital_npcs
# =============================================================================
def spawn_capital_npcs(buildings, entities_list, world_tiles, cx, cy):
    if not buildings:
        return

    palace = _building_of_type(buildings, "palace")
    city_guard = _building_of_type(buildings, "bottega", "locanda", "casa") or buildings[0]
    occupied = {(e.x, e.y) for e in entities_list}

    def add_custom(name, symbol, color, ai, pos, role, dialogue, prefers=None):
        info = {
            "name": name,
            "symbol": symbol,
            "color": color,
            "ai": ai,
            "dialogue": dialogue,
            "prefers": prefers or [],
            "role": role,
        }
        e = _make_npc(info, pos, buildings)
        if ai == "royal":
            e.home_radius = 0
            e.work_radius = 0
            e.is_royal = True
        entities_list.append(e)
        occupied.add(pos)
        return e

    # Guardia d'ingresso al palazzo: prima avvisa, poi diventa combattimento
    if palace:
        gate_x = palace.door_x
        gate_y = palace.door_y - 1
        for dx in (-1, 1):
            pos = (gate_x + dx, gate_y)
            if pos not in occupied and world_tiles.get(pos, GRASS) in (GRASS, FLOOR):
                g = add_custom("Guardia Reale", "G", (220, 220, 90), "guard", pos, "guardia",
                               "Alt! Il palazzo e' chiuso al pubblico.")
                g.is_palace_guard = True
                g.warned_once = False
                g.guard_stage = 0
                _equip_guard(g, elite=True)

    # Royalties
    if palace:
        add_custom("Re", "R", (255, 220, 120), "royal", (palace.wx + 8, palace.wy + 2), "re",
                   "Il regno e' sotto la mia protezione.", ["palace"])
        add_custom("Regina", "Q", (255, 200, 220), "royal", (palace.wx + 9, palace.wy + 2), "regina",
                   "La corona porta anche doveri.", ["palace"])
        # Servizio interno
        for pos in [(palace.wx + 2, palace.wy + 10), (palace.wx + 14, palace.wy + 10)]:
            if pos not in occupied and world_tiles.get(pos, GRASS) in (GRASS, FLOOR):
                add_custom("Servitore", "s", (200, 200, 180), "wander", pos, "servitore",
                           "La servitu' non si ferma mai.", ["palace"])

    # Nobili e amministratori sparsi nella capitale
    city_roles = [
        ("Amministratore", "n", (220, 180, 120), "wander", "amministratore", "Gli ordini della capitale sono chiari."),
        ("Nobile", "N", (240, 220, 180), "wander", "nobile", "La citta' deve prosperare."),
        ("Nobile", "N", (240, 220, 180), "wander", "nobile", "Il commercio e' la linfa della citta'."),
    ]
    houses = [b for b in buildings if b.btype in ("casa", "locanda", "bottega")]
    for idx, (name, symbol, color, ai, role, dialogue) in enumerate(city_roles):
        if idx >= len(houses):
            break
        house = houses[idx]
        pos = (house.wx + house.w // 2, house.wy + house.h // 2)
        if pos not in occupied and world_tiles.get(pos, GRASS) in (GRASS, FLOOR):
            add_custom(name, symbol, color, ai, pos, role, dialogue, ["casa"])

# =============================================================================
# draw_building_labels — insegne sopra la porta (Opzione A)
# =============================================================================
def draw_building_labels(screen, fonts, buildings, px, py,
                         tile_w, tile_h, view_cols, view_rows):
    import pygame
    half_c = view_cols//2
    half_r = view_rows//2
    for b in buildings:
        if not b.sign_label: continue
        sx = (b.door_x - px + half_c) * tile_w
        sy = (b.wy - 1  - py + half_r) * tile_h - 2
        surf = fonts["small"].render(b.sign_label, True, (255,220,80))
        bg   = pygame.Surface((surf.get_width()+6, surf.get_height()+2), pygame.SRCALPHA)
        bg.fill((0,0,0,160))
        screen.blit(bg,   (sx-3, sy-1))
        screen.blit(surf, (sx,   sy))

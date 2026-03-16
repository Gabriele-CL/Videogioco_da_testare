# world/buildings.py
import random
from core.constants import (GRASS, WALL, WATER, FOREST, ROAD,
                             FLOOR, DOOR, BUILDING,
                             WALL_H, WALL_V, WALL_C,
                             TILE_CHAR, TILE_COLOR, TILE_BG)

# ─────────────────────────────────────────────────────────────────────────────
class Building:
    """Un edificio rettangolare nella mappa mondo."""
    def __init__(self, wx, wy, w, h, btype="casa"):
        self.wx    = wx   # angolo in alto a sinistra (coord mondo)
        self.wy    = wy
        self.w     = w
        self.h     = h
        self.btype = btype
        # Porta sul lato SUD, centrata
        self.door_x = wx + w // 2
        self.door_y = wy + h - 1

    def tiles(self):
        """Genera tutti i tile dell'edificio come dict {(wx,wy): tile_id}."""
        result = {}
        for dy in range(self.h):
            for dx in range(self.w):
                x, y = self.wx + dx, self.wy + dy
                if dy == 0 or dy == self.h-1 or dx == 0 or dx == self.w-1:
                    result[(x, y)] = WALL   # muri perimetrali
                else:
                    result[(x, y)] = FLOOR  # interno
        # Porta
        result[(self.door_x, self.door_y)] = DOOR
        return result

    def door_outside(self):
        """Tile immediatamente fuori dalla porta (a sud)."""
        return (self.door_x, self.door_y + 1)

    def wall_chars(self):
        """Genera i char direzionali per i muri perimetrali."""
        result = {}
        for dy in range(self.h):
            for dx in range(self.w):
                x, y = self.wx + dx, self.wy + dy
                is_top    = dy == 0
                is_bottom = dy == self.h - 1
                is_left   = dx == 0
                is_right  = dx == self.w - 1
                is_wall   = is_top or is_bottom or is_left or is_right
                if not is_wall:
                    continue
                if (x, y) == (self.door_x, self.door_y):
                    result[(x, y)] = WALL_C
                elif (is_top or is_bottom) and not (is_left or is_right):
                    result[(x, y)] = WALL_H
                elif (is_left or is_right) and not (is_top or is_bottom):
                    result[(x, y)] = WALL_V
                else:
                    result[(x, y)] = WALL_C  # angolo
        return result

    def interior_tiles(self):
        """Lista di tile interni (camminabili), escluse porte e muri."""
        tiles = []
        for dy in range(1, self.h - 1):
            for dx in range(1, self.w - 1):
                tiles.append((self.wx + dx, self.wy + dy))
        return tiles


# ─────────────────────────────────────────────────────────────────────────────
# Tipi di edificio: (tipo, larghezza, altezza)
BUILDING_TYPES = [
    ("casa",         6, 5),
    ("casa",         6, 5),
    ("casa",         6, 5),
    ("locanda",      8, 6),
    ("bottega",      7, 5),
    ("chiesa",       8, 6),
    ("ambulatorio",  7, 5),
    ("scuola_magia", 8, 6),
]

# Tipi per i villaggi procedurali (subset più piccolo)
VILLAGE_BUILDING_TYPES = [
    ("casa",    5, 4),
    ("casa",    5, 4),
    ("locanda", 7, 5),
    ("bottega", 6, 4),
]


# ─────────────────────────────────────────────────────────────────────────────
class CityWall:
    """
    Mura rettangolari con torri agli angoli e due porte (N e S).
    Le mura sono tile WALL (non passabili), le porte sono DOOR (passabili).
    """
    def __init__(self, cx, cy, half_w, half_h):
        self.cx     = cx
        self.cy     = cy
        self.x0     = cx - half_w   # angolo top-left
        self.y0     = cy - half_h
        self.x1     = cx + half_w   # angolo bottom-right
        self.y1     = cy + half_h
        # Porte centrate a N e S
        self.gate_n = (cx, self.y0)
        self.gate_s = (cx, self.y1)

    def tiles(self):
        """Genera i tile delle mura: dict {(wx,wy): tile_id}."""
        result = {}
        x0, y0, x1, y1 = self.x0, self.y0, self.x1, self.y1

        # Muri perimetrali
        for x in range(x0, x1 + 1):
            result[(x, y0)] = WALL   # nord
            result[(x, y1)] = WALL   # sud
        for y in range(y0, y1 + 1):
            result[(x0, y)] = WALL   # ovest
            result[(x1, y)] = WALL   # est

        # Torri agli angoli (3x3 attorno ad ogni angolo)
        for (tx, ty) in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    result[(tx+dx, ty+dy)] = WALL

        # Porte N e S (3 tile larghezza per permettere passaggio)
        for dx in range(-1, 2):
            result[(self.cx + dx, y0)] = DOOR
            result[(self.cx + dx, y1)] = DOOR

        return result

    def wall_chars(self):
        """Char direzionali per le mura."""
        result = {}
        x0, y0, x1, y1 = self.x0, self.y0, self.x1, self.y1
        for x in range(x0, x1 + 1):
            for y in [y0, y1]:
                result[(x, y)] = WALL_H
        for y in range(y0, y1 + 1):
            for x in [x0, x1]:
                result[(x, y)] = WALL_V
        # Torri — char speciale T
        for (tx, ty) in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    result[(tx+dx, ty+dy)] = "T"
        # Porte
        for dx in range(-1, 2):
            result[(self.cx + dx, y0)] = WALL_C
            result[(self.cx + dx, y1)] = WALL_C
        return result

    def is_inside(self, wx, wy):
        return self.x0 < wx < self.x1 and self.y0 < wy < self.y1

    def gate_outside_n(self):
        return (self.cx, self.y0 - 1)

    def gate_outside_s(self):
        return (self.cx, self.y1 + 1)

    def gate_inside_s(self):
        """Tile interno appena dentro la porta sud."""
        return (self.cx, self.y1 - 2)


def place_starting_town(world_tiles: dict, cx: int, cy: int):
    """
    Piazza la città di partenza centrata su (cx, cy).
    Ritorna (buildings, wall_chars).
    """
    buildings  = []
    wall_chars = {}

    # Prima passata: pulisci tutta l'area della città (buffer generoso)
    town_r = 22
    for dy in range(-town_r, town_r + 1):
        for dx in range(-town_r, town_r + 1):
            world_tiles[(cx + dx, cy + dy)] = GRASS

    # Disposizione manuale a griglia 3 colonne x 3 righe (8 edifici)
    layout = [
        (-14, -12), (0, -12), (14, -12),
        (-14,   0), (0,   0), (14,   0),
        ( -7,  12), (7,   12),
    ]
    for i, (btype, bw, bh) in enumerate(BUILDING_TYPES):
        ox, oy = layout[i]
        bx = cx + ox - bw // 2
        by = cy + oy - bh // 2
        b  = Building(bx, by, bw, bh, btype)
        buildings.append(b)

        # Buffer di 2 tile intorno all'edificio: tutto GRASS
        buf = 2
        for dy in range(-buf, bh + buf):
            for dx in range(-buf, bw + buf):
                tx, ty = bx + dx, by + dy
                if (tx, ty) not in world_tiles or world_tiles[(tx, ty)] != FLOOR:
                    world_tiles[(tx, ty)] = GRASS

        # Scrivi tile edificio (sovrascrive il buffer)
        for (tx, ty), tid in b.tiles().items():
            world_tiles[(tx, ty)] = tid
        # Scrivi char direzionali muri
        wall_chars.update(b.wall_chars())

        # Garantisci corridoio libero davanti alla porta (3 tile a sud)
        ox2, oy2 = b.door_outside()
        for step in range(4):
            world_tiles[(ox2, oy2 + step)] = GRASS

    return buildings, wall_chars


def place_city_walls(world_tiles: dict, cx: int, cy: int):
    """
    Piazza le mura attorno alla città di partenza.
    Ritorna (CityWall, wall_chars).
    """
    wall = CityWall(cx, cy, half_w=20, half_h=18)
    wall_chars = {}

    for (tx, ty), tid in wall.tiles().items():
        world_tiles[(tx, ty)] = tid
    wall_chars.update(wall.wall_chars())

    # Pulisci corridoio davanti alle porte (4 tile fuori)
    for step in range(1, 5):
        world_tiles[(cx, wall.y0 - step)] = GRASS
        world_tiles[(cx, wall.y1 + step)] = GRASS
        world_tiles[(cx-1, wall.y0 - step)] = GRASS
        world_tiles[(cx+1, wall.y0 - step)] = GRASS
        world_tiles[(cx-1, wall.y1 + step)] = GRASS
        world_tiles[(cx+1, wall.y1 + step)] = GRASS

    return wall, wall_chars


def place_village(world_tiles: dict, wall_chars: dict,
                  cx: int, cy: int, rng=None):
    """
    Piazza un villaggio procedurale centrato su (cx, cy).
    Niente mura. Ritorna (buildings, wall_chars_update).
    """
    if rng is None:
        rng = random
    buildings  = []
    wc_update  = {}

    # Numero di edifici: 3-5
    n_buildings = rng.randint(3, 5)
    types = rng.sample(VILLAGE_BUILDING_TYPES, min(n_buildings, len(VILLAGE_BUILDING_TYPES)))
    if n_buildings > len(types):
        types += [("casa", 5, 4)] * (n_buildings - len(types))

    # Pulisci area villaggio
    vr = 16
    for dy in range(-vr, vr + 1):
        for dx in range(-vr, vr + 1):
            world_tiles[(cx + dx, cy + dy)] = GRASS

    # Layout casuale: disposizione a cerchio con offset
    offsets = [
        (-10, -8), (0, -8), (10, -8),
        (-8,   4), (4,   4), (12,  4),
    ]
    rng.shuffle(offsets)

    for i, (btype, bw, bh) in enumerate(types):
        if i >= len(offsets):
            break
        ox, oy = offsets[i]
        bx = cx + ox - bw // 2
        by = cy + oy - bh // 2
        b  = Building(bx, by, bw, bh, btype)
        buildings.append(b)

        # Buffer intorno all'edificio
        buf = 2
        for dy in range(-buf, bh + buf):
            for dx in range(-buf, bw + buf):
                tx, ty = bx + dx, by + dy
                world_tiles[(tx, ty)] = GRASS

        for (tx, ty), tid in b.tiles().items():
            world_tiles[(tx, ty)] = tid
        wc_update.update(b.wall_chars())

        # Corridoio porta
        ox2, oy2 = b.door_outside()
        for step in range(4):
            world_tiles[(ox2, oy2 + step)] = GRASS

    wall_chars.update(wc_update)
    return buildings, wc_update



# ─────────────────────────────────────────────────────────────────────────────
# Spawn NPC del villaggio
# ─────────────────────────────────────────────────────────────────────────────
from entities.entity import Entity
from items.item import ITEM_GEN

NPC_TYPES = {
    "merchant":      {"symbol": "M", "color": (200, 160,  60), "ai": "merchant",
                      "name": "Mercante",         "dialogue": "Cosa posso fare per te?",
                      "prefers": ["bottega"],     "role": "merchant"},
    "oste":          {"symbol": "O", "color": (180, 120,  40), "ai": "innkeeper",
                      "name": "Oste",             "dialogue": "Benvenuto alla locanda!",
                      "prefers": ["locanda"],     "role": "oste"},
    "popolano":      {"symbol": "p", "color": (160, 200, 160), "ai": "wander",
                      "name": "Popolano",         "dialogue": "Buona giornata!",
                      "prefers": [],              "role": "popolano"},
    "contadino":     {"symbol": "c", "color": (180, 200, 100), "ai": "wander",
                      "name": "Contadino",        "dialogue": "I campi non si arano da soli!",
                      "prefers": ["casa"],        "role": "contadino"},
    "fabbro":        {"symbol": "f", "color": (200, 140,  80), "ai": "wander",
                      "name": "Fabbro",           "dialogue": "Hai bisogno di un'arma affilata?",
                      "prefers": ["bottega"],     "role": "fabbro"},
    "bambino":       {"symbol": "b", "color": (220, 220, 120), "ai": "wander",
                      "name": "Bambino",          "dialogue": "Vuoi giocare con me?",
                      "prefers": ["casa"],        "role": "bambino"},
    "anziano":       {"symbol": "a", "color": (180, 180, 200), "ai": "wander",
                      "name": "Anziano",          "dialogue": "Ai miei tempi le cose erano diverse...",
                      "prefers": ["casa"],        "role": "anziano"},
    "prete":         {"symbol": "r", "color": (220, 220, 255), "ai": "wander",
                      "name": "Prete",            "dialogue": "La luce ti guidi, figlio mio.",
                      "prefers": ["chiesa"],      "role": "prete"},
    "guaritore":     {"symbol": "g", "color": (100, 220, 180), "ai": "wander",
                      "name": "Guaritore",        "dialogue": "Ho erbe per ogni male.",
                      "prefers": ["ambulatorio"], "role": "guaritore"},
    "ins_magia":     {"symbol": "~", "color": (180, 100, 255), "ai": "wander",
                      "name": "Maestro di Magia", "dialogue": "La magia e' nell'anima, non nelle parole.",
                      "prefers": ["scuola_magia"],"role": "ins_magia"},
    "cacciatore":    {"symbol": "h", "color": (160, 130,  80), "ai": "wander",
                      "name": "Cacciatore",       "dialogue": "Ho visto lupi enormi nel bosco.",
                      "prefers": ["casa"],        "role": "cacciatore"},
    "taglialegna":   {"symbol": "t", "color": (140, 100,  60), "ai": "wander",
                      "name": "Taglialegna",      "dialogue": "Il bosco e' pieno di legna buona.",
                      "prefers": ["casa"],        "role": "taglialegna"},
    "minatore":      {"symbol": "m", "color": (150, 150, 160), "ai": "wander",
                      "name": "Minatore",         "dialogue": "La pietra non mente mai.",
                      "prefers": ["casa"],        "role": "minatore"},
    "guardia_civ":   {"symbol": "G", "color": (200, 200,  80), "ai": "wander",
                      "name": "Guardia Civile",   "dialogue": "Tengo d'occhio le strade.",
                      "prefers": [],              "role": "guardia_civ"},
    "guardia":       {"symbol": "G", "color": (180, 180, 60),  "ai": "guard",
                      "name": "Guardia",          "dialogue": "Alt! Chi va là?",
                      "prefers": [],              "role": "guardia"},
}

VILLAGE_NPCS = [
    ("merchant",    1),
    ("oste",        1),
    ("prete",       1),
    ("guaritore",   1),
    ("ins_magia",   1),
    ("contadino",   2),
    ("fabbro",      1),
    ("bambino",     2),
    ("anziano",     1),
    ("cacciatore",  1),
    ("taglialegna", 1),
    ("minatore",    1),
    ("guardia_civ", 2),
    ("popolano",    3),
]

VILLAGE_NPCS_SMALL = [
    ("popolano", 3),
]


def _building_of_type(buildings, *btypes):
    """Restituisce un edificio casuale tra quelli con tipo in btypes, o None."""
    matches = [b for b in buildings if b.btype in btypes]
    return random.choice(matches) if matches else None


def _rarity_for_level(level: int) -> str:
    """Converte il livello NPC in una rarità oggetto."""
    if level >= 10: return "legendary"
    if level >= 7:  return "epic"
    if level >= 5:  return "rare"
    if level >= 3:  return "uncommon"
    return "common"


def spawn_village_npcs(buildings, entities_list, world_tiles):
    """
    Spawna gli NPC del villaggio.
    - Mercanti e Osti: dentro il proprio edificio preferito.
    - Popolani: su tile GRASS liberi nelle vicinanze del villaggio,
      mai dentro edifici né su WALL/WATER.
    - Nessuno spawna su una porta o sul tile davanti alla porta.
    """
    if not buildings: return

    # Raccoglie porte e tile vietati
    forbidden = set()
    for b in buildings:
        forbidden.add((b.door_x, b.door_y))
        dx, dy = b.door_outside()
        forbidden.add((dx, dy))
        forbidden.add((dx, dy + 1))

    occupied = {(e.x, e.y) for e in entities_list}

    for npc_type, count in VILLAGE_NPCS:
        info = NPC_TYPES[npc_type]
        for _ in range(count):
            pos = None
            if info["prefers"]:
                bldg = _building_of_type(buildings, *info["prefers"])
                if bldg:
                    # Scegli tile interno libero
                    interior = [t for t in bldg.interior_tiles()
                                if t not in occupied and t not in forbidden]
                    if interior:
                        pos = random.choice(interior)
            if pos is None:
                # Cerca tile GRASS libero intorno al villaggio (raggio 6-14)
                b0 = buildings[0]
                cx0 = b0.wx + b0.w // 2
                cy0 = b0.wy + b0.h // 2
                for attempt in range(80):
                    rx = cx0 + random.randint(-14, 14)
                    ry = cy0 + random.randint(-14, 14)
                    if ((rx, ry) not in occupied
                            and (rx, ry) not in forbidden
                            and world_tiles.get((rx, ry), GRASS) == GRASS):
                        pos = (rx, ry)
                        break
            if pos is None:
                continue  # fallback: salta

            e = Entity.__new__(Entity)
            e.x, e.y   = pos
            e.name     = info["name"]
            e.symbol   = info["symbol"]
            e.color    = info["color"]
            e.ai_type  = info["ai"]
            e.alive    = True
            e.health   = e.max_health = 20
            e.damage   = 0
            e.defense  = 0
            e.level    = 1
            e.dialogue = info["dialogue"]
            e.has_quest = False
            e.quest     = None
            e.gold      = 0
            e.shop      = []
            e.home_x    = pos[0]
            e.home_y    = pos[1]
            e.home_radius = 6
            e.npc_role  = info.get("role", npc_type)
            # Destinazione lavoro: edificio preferito o posizione casa
            work_btype  = info.get("prefers", [])
            work_b      = _building_of_type(buildings, *work_btype) if work_btype else None
            if work_b:
                wx_mid  = work_b.wx + work_b.w // 2
                wy_mid  = work_b.wy + work_b.h // 2
                e.work_x = wx_mid; e.work_y = wy_mid
            else:
                e.work_x = pos[0]; e.work_y = pos[1]
            e.work_radius = 5
            # Destinazione sera: locanda o piazza centrale
            tavern_b = _building_of_type(buildings, "locanda")
            if tavern_b:
                e.tavern_x = tavern_b.wx + tavern_b.w // 2
                e.tavern_y = tavern_b.wy + tavern_b.h // 2
            else:
                e.tavern_x = pos[0]; e.tavern_y = pos[1]
            if npc_type == "merchant":
                e.gold  = random.randint(100, 300)
                e.level = random.randint(1, 6)
                shop_size = max(3, e.level // 2 + 2)
                e.shop  = [ITEM_GEN.generate_merchant_item(
                               _rarity_for_level(e.level))
                           for _ in range(shop_size)]
            elif npc_type == "oste":
                e.gold  = random.randint(50, 150)
                e.level = random.randint(1, 4)
                e.shop  = [ITEM_GEN.generate_innkeeper_item(
                               _rarity_for_level(e.level))
                           for _ in range(4)]
            occupied.add(pos)
            entities_list.append(e)


def spawn_guards(city_wall, entities_list, world_tiles):
    """
    Spawna guardie alle porte N e S e sulle mura.
    Le guardie hanno ai_type='guard' — aggressive con i nemici, ignorano il player.
    """
    from entities.entity import Entity
    occupied = {(e.x, e.y) for e in entities_list}

    def make_guard(x, y, patrol_x, patrol_y):
        e = Entity.__new__(Entity)
        e.x, e.y        = x, y
        e.name          = "Guardia"
        e.symbol        = "G"
        e.color         = (200, 200, 60)
        e.ai_type       = "guard"
        e.alive         = True
        e.health        = e.max_health = 50
        e.damage        = 12
        e.defense       = 5
        e.level         = random.randint(3, 7)
        e.dialogue      = "Alt! Chi va là?"
        e.has_quest     = False
        e.quest         = None
        e.gold          = random.randint(10, 30)
        e.shop          = []
        e.home_x        = patrol_x
        e.home_y        = patrol_y
        e.home_radius   = 6
        e.patrol_x      = patrol_x
        e.patrol_y      = patrol_y
        return e

    # Guardie porta Nord (2 ai lati della porta)
    gn_x, gn_y = city_wall.gate_n
    for dx in [-2, 2]:
        pos = (gn_x + dx, gn_y + 1)
        if pos not in occupied:
            entities_list.append(make_guard(pos[0], pos[1], gn_x, gn_y))
            occupied.add(pos)

    # Guardie porta Sud
    gs_x, gs_y = city_wall.gate_s
    for dx in [-2, 2]:
        pos = (gs_x + dx, gs_y - 1)
        if pos not in occupied:
            entities_list.append(make_guard(pos[0], pos[1], gs_x, gs_y))
            occupied.add(pos)

    # Guardie sulle mura (pattugliano il perimetro)
    patrol_points = [
        (city_wall.x0 + 5,  city_wall.y0 + 1),
        (city_wall.x1 - 5,  city_wall.y0 + 1),
        (city_wall.x0 + 5,  city_wall.y1 - 1),
        (city_wall.x1 - 5,  city_wall.y1 - 1),
    ]
    for px, py in patrol_points:
        # Trova tile GRASS vicino al punto di pattuglia
        for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
            pos = (px+dx, py+dy)
            if pos not in occupied and world_tiles.get(pos, GRASS) in (GRASS, FLOOR):
                entities_list.append(make_guard(pos[0], pos[1], px, py))
                occupied.add(pos)
                break


def spawn_village_npcs_small(buildings, entities_list, world_tiles, cx, cy):
    """
    Spawna NPC per un villaggio piccolo (senza mura).
    Solo popolani + eventuale mercante ambulante.
    """
    if not buildings:
        return

    forbidden = set()
    for b in buildings:
        forbidden.add((b.door_x, b.door_y))
        dx, dy = b.door_outside()
        forbidden.add((dx, dy))

    occupied = {(e.x, e.y) for e in entities_list}

    # Eventuale mercante se c'è una bottega
    has_bottega = any(b.btype == "bottega" for b in buildings)
    npc_list = list(VILLAGE_NPCS_SMALL)
    if has_bottega:
        npc_list = [("merchant", 1)] + npc_list

    for npc_type, count in npc_list:
        info = NPC_TYPES[npc_type]
        for _ in range(count):
            pos = None
            if info["prefers"]:
                bldg = _building_of_type(buildings, *info["prefers"])
                if bldg:
                    interior = [t for t in bldg.interior_tiles()
                                if t not in occupied and t not in forbidden]
                    if interior:
                        pos = random.choice(interior)
            if pos is None:
                for _ in range(60):
                    rx = cx + random.randint(-12, 12)
                    ry = cy + random.randint(-12, 12)
                    if ((rx, ry) not in occupied and (rx, ry) not in forbidden
                            and world_tiles.get((rx, ry), GRASS) == GRASS):
                        pos = (rx, ry)
                        break
            if pos is None:
                continue

            e = Entity.__new__(Entity)
            e.x, e.y      = pos
            e.name        = info["name"]
            e.symbol      = info["symbol"]
            e.color       = info["color"]
            e.ai_type     = info["ai"]
            e.alive       = True
            e.health      = e.max_health = 20
            e.damage      = 0
            e.defense     = 0
            e.level       = 1
            e.dialogue    = info["dialogue"]
            e.has_quest   = False
            e.quest       = None
            e.gold        = 0
            e.shop        = []
            e.home_x      = pos[0]
            e.home_y      = pos[1]
            e.home_radius = 8
            if npc_type == "merchant":
                e.gold  = random.randint(50, 200)
                e.level = random.randint(1, 4)
                e.shop  = [ITEM_GEN.generate_merchant_item(
                               _rarity_for_level(e.level)) for _ in range(3)]
            occupied.add(pos)
            entities_list.append(e)


# ─────────────────────────────────────────────────────────────────────────────
# draw_building_labels — stub per compatibilità import
# ─────────────────────────────────────────────────────────────────────────────
def draw_building_labels(screen, fonts, buildings, px, py,
                         tile_w, tile_h, view_cols, view_rows):
    pass
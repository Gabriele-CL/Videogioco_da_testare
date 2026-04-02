# world/world.py
import random
from core.constants import *
from world.layout import WorldLayout
from world.chunk import generate_chunk, set_seed
from world.buildings import (Building, place_starting_town, place_city_walls,
                              place_village, place_capital_city, spawn_village_npcs,
                              spawn_village_npcs_small, spawn_guards,
                              FLOOR, DOOR)

PASSABLE = {GRASS, FLOOR, DOOR, ROAD, FOREST}   # tile percorribili normali
PASSABLE_GHOST = PASSABLE | {WALL}               # fantasmi passano i muri


class World:
    def __init__(self, seed: int, entities: list, bootstrap_static: bool = True):
        self.seed      = seed
        self.entities  = entities
        self.chunks    = {}          # (cx,cy) -> {tiles, biome}
        self.overrides = {}          # (wx,wy)  -> tile_id
        self.wall_chars= {}          # (wx,wy)  -> char direzionale (|, _, +)
        self.buildings = []
        self.city_wall = None
        self.capital_walls = []
        self.layout    = WorldLayout(seed)
        set_seed(seed)
        if bootstrap_static:
            self.bootstrap_static_landmarks()

    def bootstrap_static_landmarks(self):
        """
        Piazzamento iniziale dei grandi punti fissi del mondo.
        Idempotente: se i landmark sono già presenti negli entity list/overrides,
        non li duplica.
        """
        for landmark in self.layout.capitals:
            self._ensure_chunk(landmark.x // CHUNK_SIZE, landmark.y // CHUNK_SIZE)
            existing = any(
                getattr(e, "name", "") == landmark.name and e.x == landmark.x and e.y == landmark.y
                for e in self.entities
            )
            if existing:
                continue
            buildings, wc, city_wall = place_capital_city(self.overrides, self.wall_chars, self.entities, landmark.x, landmark.y)
            self.buildings.extend(buildings)
            self.wall_chars.update(wc)
            self.capital_walls.append(city_wall)

    def rebuild_starting_town_runtime(self, cx: int, cy: int):
        """
        Ricostruisce SOLO gli oggetti runtime (buildings/city_wall) per la città iniziale
        senza modificare tiles/overrides/wall_chars caricati da save.

        La città iniziale è ora un capitale, quindi il runtime va ricostruito con
        place_capital_city su un buffer separato.
        """
        tmp_tiles = {}
        tmp_entities = []
        self.buildings, _, self.city_wall = place_capital_city(tmp_tiles, {}, tmp_entities, cx, cy)

    def get_wall_char(self, wx, wy):
        """Ritorna il char direzionale del muro edificio, o None se normale."""
        return self.wall_chars.get((wx, wy))

    # ── chunk ─────────────────────────────────────────────────────────────────
    def _cx_cy(self, wx, wy):
        return wx // CHUNK_SIZE, wy // CHUNK_SIZE

    def _ensure_chunk(self, cx, cy):
        if (cx, cy) not in self.chunks:
            self.chunks[(cx, cy)] = generate_chunk(cx, cy, self.layout)

    def preload_around(self, wx, wy, radius=2):
        cx, cy = self._cx_cy(wx, wy)
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                self._ensure_chunk(cx+dx, cy+dy)

    # ── tile ──────────────────────────────────────────────────────────────────
    def get_tile(self, wx, wy):
        if (wx, wy) in self.overrides:
            return self.overrides[(wx, wy)]
        cx, cy   = self._cx_cy(wx, wy)
        self._ensure_chunk(cx, cy)
        lx = wx - cx * CHUNK_SIZE
        ly = wy - cy * CHUNK_SIZE
        return self.chunks[(cx, cy)]["tiles"][ly][lx]

    def _set_tile(self, wx, wy, tid):
        self.overrides[(wx, wy)] = tid

    # ── passabilità ───────────────────────────────────────────────────────────
    def is_passable(self, wx, wy):
        return self.get_tile(wx, wy) in PASSABLE

    def is_passable_ghost(self, wx, wy):
        return self.get_tile(wx, wy) in PASSABLE_GHOST

    def is_safe_zone(self, wx: int, wy: int) -> bool:
        """
        Zone protette attorno a capitali e nuclei urbani.
        Usata per evitare spawn ostili troppo vicini alle città principali.
        """
        if self.layout and self.layout.is_capital_zone(wx, wy):
            return True
        return (wx * wx + wy * wy) < (TOWN_SAFE_RADIUS * TOWN_SAFE_RADIUS)

    # ── bioma ─────────────────────────────────────────────────────────────────
    def get_biome_at(self, wx, wy):
        cx, cy = self._cx_cy(wx, wy)
        self._ensure_chunk(cx, cy)
        return self.chunks[(cx, cy)].get("biome", "Grassland")

    def peek_biome_at(self, wx, wy):
        """
        Ritorna il bioma senza generare chunk nuovi.
        Utile per UI e preview che non devono caricare il mondo.
        """
        cx, cy = self._cx_cy(wx, wy)
        chunk = self.chunks.get((cx, cy))
        if chunk is not None:
            return chunk.get("biome", "Grassland")
        if self.layout:
            from world.chunk import get_biome
            return get_biome(cx, cy)
        return "Grassland"

    # ── città iniziale ────────────────────────────────────────────────────────
    def place_starting_town(self, cx: int, cy: int):
        """Piazza edifici, mura, NPC e guardie della città di partenza."""
        self.preload_around(cx, cy, radius=3)
        # Edifici interni
        self.buildings, wall_chars = place_starting_town(self.overrides, cx, cy)
        self.wall_chars.update(wall_chars)
        # Mura cittadine con torri
        self.city_wall, wc_walls = place_city_walls(self.overrides, cx, cy)
        self.wall_chars.update(wc_walls)
        # NPC villaggio
        spawn_village_npcs(self.buildings, self.entities, self.overrides)
        # Guardie alle porte e sulle mura
        spawn_guards(self.city_wall, self.entities, self.overrides)

    # ── serializzazione ───────────────────────────────────────────────────────
    def to_dict(self):
        return {
            "chunks":     {f"{cx},{cy}": v for (cx,cy), v in self.chunks.items()},
            "overrides":  {f"{wx},{wy}": t for (wx,wy), t  in self.overrides.items()},
            "wall_chars": {f"{wx},{wy}": c for (wx,wy), c  in self.wall_chars.items()},
        }

    def load_dict(self, data: dict, seed: int):
        set_seed(seed)
        self.chunks     = {}
        self.overrides  = {}
        self.wall_chars = {}
        for key, val in data.get("chunks", {}).items():
            cx, cy = map(int, key.split(","))
            self.chunks[(cx, cy)] = val
        for key, tid in data.get("overrides", {}).items():
            wx, wy = map(int, key.split(","))
            self.overrides[(wx, wy)] = tid
        for key, ch in data.get("wall_chars", {}).items():
            wx, wy = map(int, key.split(","))
            self.wall_chars[(wx, wy)] = ch


# =============================================================================
# SPAWN NEMICI PER CHUNK
# =============================================================================
from core.constants import DEN
try:
    from core.constants import TOWN_SAFE_RADIUS
except ImportError:
    TOWN_SAFE_RADIUS = 40

# Raggio minimo garantito
_SAFE_R = max(TOWN_SAFE_RADIUS, 80)
from entities.entity import make_entity, BIOME_SPAWNS
import random as _random

DEN_CHANCE_PER_CHUNK  = 0.18
MAX_ENEMIES_PER_CHUNK = 4


def _weighted_pick(entries, is_night: bool):
    pool = [(t, w[1] if is_night else w[0]) for t, *w in entries]
    pool = [(t, w) for t, w in pool if w > 0]
    if not pool:
        return None
    types, weights = zip(*pool)
    return _random.choices(types, weights=weights)[0]


def _is_safe_zone(wx: int, wy: int) -> bool:
    """Compat helper legacy: mantenuto per compatibilità interna."""
    return (wx * wx + wy * wy) < (_SAFE_R * _SAFE_R)


def _place_den(world_tiles: dict, wall_chars: dict, cx: int, cy: int):
    CHUNK_SIZE = 32
    for _ in range(12):
        ox = _random.randint(2, CHUNK_SIZE - 5)
        oy = _random.randint(2, CHUNK_SIZE - 5)
        bx = cx * CHUNK_SIZE + ox
        by = cy * CHUNK_SIZE + oy
        if any(world_tiles.get((bx+dx, by+dy), GRASS) not in (GRASS, FOREST)
               for dy in range(3) for dx in range(3)):
            continue
        for dy in range(3):
            for dx in range(3):
                tx, ty = bx + dx, by + dy
                if dx == 1 and dy == 1:
                    world_tiles[(tx, ty)] = GRASS
                else:
                    world_tiles[(tx, ty)] = DEN
                    if (dx == 0 or dx == 2) and (dy == 0 or dy == 2):
                        wall_chars[(tx, ty)] = "+"
                    elif dy == 0 or dy == 2:
                        wall_chars[(tx, ty)] = "_"
                    else:
                        wall_chars[(tx, ty)] = "|"
        return (bx + 1, by + 1)
    return None


def _place_camp_marker(world_tiles: dict, wall_chars: dict, cx: int, cy: int):
    CHUNK_SIZE = 32
    for _ in range(14):
        ox = _random.randint(3, CHUNK_SIZE - 6)
        oy = _random.randint(3, CHUNK_SIZE - 6)
        bx = cx * CHUNK_SIZE + ox
        by = cy * CHUNK_SIZE + oy
        if any(world_tiles.get((bx + dx, by + dy), GRASS) not in (GRASS, FOREST, ROAD)
               for dy in range(4) for dx in range(4)):
            continue
        for dy in range(3):
            for dx in range(3):
                tx, ty = bx + dx, by + dy
                world_tiles[(tx, ty)] = CAMP
                wall_chars[(tx, ty)] = "^"
        return (bx + 1, by + 1)
    return None


def _place_dungeon_marker(world_tiles: dict, wall_chars: dict, cx: int, cy: int):
    CHUNK_SIZE = 32
    for _ in range(10):
        ox = _random.randint(2, CHUNK_SIZE - 4)
        oy = _random.randint(2, CHUNK_SIZE - 4)
        bx = cx * CHUNK_SIZE + ox
        by = cy * CHUNK_SIZE + oy
        if any(world_tiles.get((bx + dx, by + dy), GRASS) not in (GRASS, FOREST, ROAD, WALL)
               for dy in range(3) for dx in range(3)):
            continue
        world_tiles[(bx + 1, by + 1)] = DUNGEON
        wall_chars[(bx + 1, by + 1)] = "*"
        return (bx + 1, by + 1)
    return None


class WorldSpawner:
    def __init__(self, world: "World"):
        self.world      = world
        self.populated  : set = set()
        self.generated_pois: set = set()
        self.poi_markers: dict = {}

    def bootstrap_all(self):
        """Popola subito tutti i POI selvaggi del layout."""
        CHUNK_SIZE = 32
        w = self.world
        for idx, (sx, sy) in enumerate(getattr(w.layout, "wild_slots", [])):
            slot_key = ("wild", idx)
            if slot_key in self.generated_pois:
                continue
            if w.is_safe_zone(sx, sy):
                continue
            cx, cy = sx // CHUNK_SIZE, sy // CHUNK_SIZE
            w._ensure_chunk(cx, cy)
            biome = w.chunks.get((cx, cy), {}).get("biome", "Grassland")
            slot_rng = _random.Random(w.seed ^ (idx * 2654435761) ^ (cx * 1597334677) ^ (cy * 3812015801))

            camp_allowed = biome in ("Forest", "Grassland", "Road", "Swamp")
            dungeon_allowed = biome in ("Forest", "Swamp", "Mountain")
            kind = None
            if camp_allowed and slot_rng.random() < 0.72:
                kind = "camp"
            elif dungeon_allowed and slot_rng.random() < 0.55:
                kind = "dungeon"
            elif camp_allowed:
                kind = "camp"
            elif dungeon_allowed:
                kind = "dungeon"
            else:
                continue

            if kind == "camp":
                camp_center = _place_camp_marker(w.overrides, w.wall_chars, cx, cy)
                if camp_center:
                    ccx, ccy = camp_center
                    camp_types = ["bandit", "goblin", "orc", "wolf"]
                    for _ in range(slot_rng.randint(2, 4)):
                        etype = slot_rng.choice(camp_types)
                        for _ in range(12):
                            ex = ccx + slot_rng.randint(-3, 3)
                            ey = ccy + slot_rng.randint(-3, 3)
                            if w.is_passable(ex, ey) and not w.is_safe_zone(ex, ey):
                                w.entities.append(make_entity(etype, ex, ey))
                                break
                    self.poi_markers[slot_key] = {"kind": "camp", "x": ccx, "y": ccy}
                    self.generated_pois.add(slot_key)
            else:
                dungeon_center = _place_dungeon_marker(w.overrides, w.wall_chars, cx, cy)
                if dungeon_center:
                    dx, dy = dungeon_center
                    self.poi_markers[slot_key] = {"kind": "dungeon", "x": dx, "y": dy}
                    self.generated_pois.add(slot_key)

    def populate_chunk_if_needed(self, cx: int, cy: int, is_night: bool):
        if (cx, cy) in self.populated:
            return
        self.populated.add((cx, cy))

        w     = self.world
        biome = w.chunks.get((cx, cy), {}).get("biome", "Grassland")
        spawns = BIOME_SPAWNS.get(biome)
        if not spawns:
            return

        CHUNK_SIZE = 32
        cx0 = cx * CHUNK_SIZE
        cy0 = cy * CHUNK_SIZE

        # Tana lupi nei biomi bosco/palude
        if biome in ("Forest", "Swamp") and _random.random() < DEN_CHANCE_PER_CHUNK:
            den_center = _place_den(w.overrides, w.wall_chars, cx, cy)
            if den_center:
                dcx, dcy = den_center
                for _ in range(_random.randint(2, 3)):
                    for _ in range(20):
                        ex = dcx + _random.randint(-4, 4)
                        ey = dcy + _random.randint(-4, 4)
                        if w.is_passable(ex, ey) and not w.is_safe_zone(ex, ey):
                            e = make_entity("wolf", ex, ey)
                            e.home_x = dcx
                            e.home_y = dcy
                            e.home_radius = 8
                            w.entities.append(e)
                            break
                return

        # Spawn normale
        count = _random.randint(1, MAX_ENEMIES_PER_CHUNK)
        for _ in range(count):
            etype = _weighted_pick(spawns, is_night)
            if not etype:
                continue
            for _ in range(20):
                ex = cx0 + _random.randint(1, CHUNK_SIZE - 2)
                ey = cy0 + _random.randint(1, CHUNK_SIZE - 2)
                if w.is_passable(ex, ey) and not w.is_safe_zone(ex, ey):
                    w.entities.append(make_entity(etype, ex, ey))
                    break

        # POI selvaggi: slot semi-stabili del layout, non puro random.
        layout_slots = getattr(w.layout, "wild_slots", [])
        for idx, (sx, sy) in enumerate(layout_slots):
            slot_key = ("wild", idx)
            if slot_key in self.generated_pois:
                continue
            if (sx // CHUNK_SIZE, sy // CHUNK_SIZE) != (cx, cy):
                continue
            if w.is_safe_zone(sx, sy):
                continue
            if not w.is_passable(sx, sy):
                continue

            slot_rng = _random.Random(w.seed ^ (idx * 2654435761) ^ (cx * 1597334677) ^ (cy * 3812015801))
            if biome in ("Forest", "Grassland", "Road", "Swamp") and slot_rng.random() < 0.72:
                camp_center = _place_camp_marker(w.overrides, w.wall_chars, cx, cy)
                if camp_center:
                    ccx, ccy = camp_center
                    camp_types = ["bandit", "goblin", "orc", "wolf"]
                    for _ in range(slot_rng.randint(2, 4)):
                        etype = slot_rng.choice(camp_types)
                        for _ in range(12):
                            ex = ccx + slot_rng.randint(-3, 3)
                            ey = ccy + slot_rng.randint(-3, 3)
                            if w.is_passable(ex, ey) and not w.is_safe_zone(ex, ey):
                                w.entities.append(make_entity(etype, ex, ey))
                                break
                    self.poi_markers[slot_key] = {"kind": "camp", "x": ccx, "y": ccy}
                    self.generated_pois.add(slot_key)
                    continue

            if biome in ("Forest", "Swamp", "Mountain") and slot_rng.random() < 0.45:
                dungeon_center = _place_dungeon_marker(w.overrides, w.wall_chars, cx, cy)
                if dungeon_center:
                    dx, dy = dungeon_center
                    self.poi_markers[slot_key] = {"kind": "dungeon", "x": dx, "y": dy}
                    self.generated_pois.add(slot_key)

# =============================================================================
# VILLAGGI PROCEDURALI
# =============================================================================
class WorldSettlements:
    """
    Genera villaggi procedurali sparsi man mano che si esplora.
    Deterministico per seed: stesso seed = stessi villaggi.
    """
    MIN_DIST       = 80    # distanza minima tra villaggi (tile)
    VILLAGE_CHANCE = 0.06  # probabilità per chunk

    def __init__(self, world: "World"):
        self.world     = world
        self.evaluated : set  = set()
        self.centers   : list = []
        self.generated_villages: set = set()

    def bootstrap_all(self):
        """Popola subito tutti i villaggi del layout."""
        CHUNK_SIZE = 32
        w = self.world
        for idx, (_, vx, vy) in enumerate(getattr(w.layout, "village_slots", [])):
            village_key = ("village", idx)
            if village_key in self.generated_villages:
                continue
            if w.is_safe_zone(vx, vy):
                continue
            if self._too_close(vx, vy):
                continue
            w._ensure_chunk(vx // CHUNK_SIZE, vy // CHUNK_SIZE)
            rng = _random.Random(w.seed ^ (idx * 73856093) ^ (vx * 19349663) ^ (vy * 83492791))
            buildings, wc = place_village(w.overrides, w.wall_chars, vx, vy, rng)
            w.wall_chars.update(wc)
            spawn_village_npcs_small(buildings, w.entities, w.overrides, vx, vy)
            self.centers.append((vx, vy))
            self.generated_villages.add(village_key)

    def _too_close(self, wx, wy):
        for vx, vy in self.centers:
            if (wx-vx)**2 + (wy-vy)**2 < self.MIN_DIST**2:
                return True
        if self.world.layout and not self.world.layout.safe_distance_from_capitals(wx, wy, margin=20):
            return True
        return wx*wx + wy*wy < (self.MIN_DIST * 1.5)**2

    def try_generate(self, cx: int, cy: int):
        if (cx, cy) in self.evaluated:
            return
        self.evaluated.add((cx, cy))

        CHUNK_SIZE = 32
        w = self.world
        wx0 = cx * CHUNK_SIZE + CHUNK_SIZE // 2
        wy0 = cy * CHUNK_SIZE + CHUNK_SIZE // 2
        if w.is_safe_zone(wx0, wy0):
            return

        rng = _random.Random(self.world.seed ^ (cx * 73856093) ^ (cy * 19349663))
        w.preload_around(wx0, wy0, radius=2)

        for idx, (_, vx, vy) in enumerate(getattr(w.layout, "village_slots", [])):
            if ("village", idx) in self.generated_villages:
                continue
            if (vx // CHUNK_SIZE, vy // CHUNK_SIZE) != (cx, cy):
                continue
            if self._too_close(vx, vy):
                continue
            if not w.is_passable(vx, vy):
                continue

            buildings, wc = place_village(w.overrides, w.wall_chars, vx, vy, rng)
            w.wall_chars.update(wc)
            spawn_village_npcs_small(buildings, w.entities, w.overrides, vx, vy)
            self.centers.append((vx, vy))
            self.generated_villages.add(("village", idx))
            break

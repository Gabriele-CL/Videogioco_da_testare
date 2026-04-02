# =============================================================================
# chunk.py — Generazione procedurale dei chunk di mappa.
# Un chunk è CHUNK_SIZE x CHUNK_SIZE tile generati col rumore Perlin.
# =============================================================================

import random
from core.constants import CHUNK_SIZE, NOISE_SCALE, NOISE_OCTAVE, GRASS, WALL, WATER, FOREST, ROAD, WORLD_LIMIT
from core.utils import pnoise2

# Seed globale — impostato da set_seed() prima di generare qualsiasi chunk
SEED = 0

def set_seed(s: int):
    """Imposta il seed globale. Chiamata da World.__init__() e load_dict()."""
    global SEED
    SEED = s

def get_biome(cx: int, cy: int) -> str:
    """
    Determina il bioma di un chunk tramite rumore a bassa frequenza (0.3).
    Produce zone ampie e coerenti invece di biomi sparsi.

    Mappa valore → bioma:
        > 0.3  → Mountain
        > 0.1  → Forest
        > -0.1 → Grassland
        > -0.3 → Road
        else   → Swamp
    """
    v = pnoise2(cx * 0.3, cy * 0.3, octaves=2, base=SEED % 256)
    if v >  0.3: return "Mountain"
    if v >  0.1: return "Forest"
    if v > -0.1: return "Grassland"
    if v > -0.3: return "Road"
    return "Swamp"

def generate_chunk(cx: int, cy: int, layout=None) -> dict:
    """
    Genera un chunk completo alla posizione (cx, cy).

    Per ogni tile calcola le coordinate assolute (wx, wy), campiona il rumore
    Perlin e assegna il tipo:
        n > 0.4  → WALL  (roccia/montagna)
        n < -0.4 → WATER (lago/fiume)
        Forest + n > 0.05 → FOREST
        Road → griglia di strade
        default → GRASS

    Ritorna dizionario con "tiles" (griglia 2D), "biome" e "entities" (vuota).
    """
    biome = get_biome(cx, cy)
    tiles = []
    for ty in range(CHUNK_SIZE):
        row = []
        for tx in range(CHUNK_SIZE):
            wx = cx * CHUNK_SIZE + tx   # coordinata mondo assoluta
            wy = cy * CHUNK_SIZE + ty
            edge_band = WORLD_LIMIT - 96
            if abs(wx) >= edge_band or abs(wy) >= edge_band:
                row.append(WALL)
                continue
            n  = pnoise2(wx * NOISE_SCALE, wy * NOISE_SCALE,
                         octaves=NOISE_OCTAVE, base=SEED % 256)
            if n > 0.4:
                tile = WALL
            elif n < -0.4:
                tile = WATER
            elif biome == "Forest" and n > 0.05:
                tile = FOREST
            elif biome == "Road":
                # Le strade reali sono generate da buildings.py
                # Nei chunk "Road" mettiamo solo erba rada con pochi alberi
                tile = FOREST if n > 0.15 else GRASS
            else:
                tile = GRASS
            if layout is not None and layout.is_capital_zone(wx, wy):
                tile = GRASS
            row.append(tile)
        tiles.append(row)
    return {"tiles": tiles, "biome": biome, "entities": []}

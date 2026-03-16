# =============================================================================
# utils.py — Funzioni di utilità: rumore Perlin 2D e pathfinding A*.
# Nessuna dipendenza da stato globale: funzioni pure e riutilizzabili.
# =============================================================================

import math
import heapq
import random


# =============================================================================
# RUMORE PERLIN 2D (implementazione pura Python)
# Genera valori "naturali" utili per mappe procedurali.
# =============================================================================

def _fade(t):
    """Attenuazione smoothstep: rende le transizioni del rumore morbide."""
    return t * t * t * (t * (t * 6 - 15) + 10)

def _lerp(a, b, t):
    """Interpolazione lineare tra a e b con fattore t."""
    return a + t * (b - a)

def _grad(h, x, y):
    """Prodotto scalare tra gradiente pseudocasuale e vettore (x,y)."""
    h &= 3
    if h == 0: return  x + y
    if h == 1: return -x + y
    if h == 2: return  x - y
    return             -x - y

class _PerlinNoise:
    """Generatore Perlin 2D interno. Un'istanza per seed."""
    def __init__(self, seed=0):
        # Tabella di permutazione mescolata deterministicamente col seed
        rng = random.Random(seed)
        p   = list(range(256)); rng.shuffle(p)
        self._p = p * 2   # duplicata per evitare overflow indici

    def noise2(self, x, y):
        """Valore Perlin nel punto (x,y), circa in [-1, 1]."""
        p  = self._p
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u, v = _fade(xf), _fade(yf)
        aa = p[p[xi]     + yi    ]
        ab = p[p[xi]     + yi + 1]
        ba = p[p[xi + 1] + yi    ]
        bb = p[p[xi + 1] + yi + 1]
        x1 = _lerp(_grad(aa, xf,     yf    ), _grad(ba, xf-1, yf    ), u)
        x2 = _lerp(_grad(ab, xf,     yf - 1), _grad(bb, xf-1, yf - 1), u)
        return _lerp(x1, x2, v)

# Cache istanze: una per seed, evita di ricrearle ogni chiamata
_PERLIN_INSTANCES: dict = {}

def pnoise2(x, y, octaves=1, base=0):
    """
    Rumore Perlin frattale multi-ottava.
    Stesso base + stesse coordinate = stesso valore sempre.
    Ritorna float normalizzato in circa [-1, 1].
    """
    if base not in _PERLIN_INSTANCES:
        _PERLIN_INSTANCES[base] = _PerlinNoise(base)
    pn  = _PERLIN_INSTANCES[base]
    val = amp = freq = mx = 0.0
    amp = freq = 1.0
    for _ in range(octaves):
        val  += pn.noise2(x * freq, y * freq) * amp
        mx   += amp
        amp  *= 0.5
        freq *= 2.0
    return val / mx


# =============================================================================
# A* PATHFINDING — percorso minimo su griglia 2D
# =============================================================================

def astar(sx, sy, tx, ty, passable_fn, max_steps=20):
    """
    Percorso più breve da (sx,sy) a (tx,ty).

    Parametri:
        sx, sy      : punto di partenza
        tx, ty      : punto di arrivo
        passable_fn : funzione (x,y)->bool, True se la cella è percorribile
        max_steps   : profondità massima (limita CPU per distanze lunghe)

    Ritorna lista di tuple (x,y) del percorso, vuota se non trovato.
    """
    if sx == tx and sy == ty:
        return []  # già in destinazione

    # Coda con priorità: (f_score, x, y, path_finora)
    open_set = [(0, sx, sy, [])]
    visited  = set()

    while open_set:
        f, x, y, path = heapq.heappop(open_set)
        if (x, y) in visited:
            continue
        visited.add((x, y))

        if x == tx and y == ty:
            return path  # percorso trovato

        if len(path) >= max_steps:
            continue  # troppo lungo, abbandona ramo

        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited and passable_fn(nx, ny):
                g = len(path) + 1
                h = abs(nx - tx) + abs(ny - ty)  # euristica Manhattan
                heapq.heappush(open_set, (g + h, nx, ny, path + [(nx, ny)]))

    return []  # nessun percorso trovato

# =============================================================================
# ui/world_map_ui.py - Schermata mappa del mondo
# =============================================================================
from collections import deque

import pygame

from core.constants import CAMP, DUNGEON, SCREEN_H, SCREEN_W, WALL, WATER, FOREST, ROAD


BG_DARK = (8, 10, 18)
PAPER = (18, 22, 30)
PAPER_2 = (24, 28, 38)
BORDER = (110, 120, 150)
TEXT = (220, 220, 230)
DIM = (140, 150, 165)
TITLE = (250, 240, 210)

BIOME_COLORS = {
    "Grassland": (40, 92, 58),
    "Forest": (22, 66, 38),
    "Mountain": (95, 92, 84),
    "Road": (110, 92, 58),
    "Swamp": (28, 66, 64),
}

TILE_COLORS = {
    WATER: (30, 58, 100),
    WALL: (105, 98, 88),
    FOREST: (28, 76, 42),
    ROAD: (124, 104, 70),
}


def _world_bounds(world, player):
    layout = getattr(world, "layout", None)
    if layout and getattr(layout, "world_extent", None):
        extent = int(layout.world_extent)
        pad = 96
        return (-extent - pad, -extent - pad, extent + pad, extent + pad)

    points = []
    if layout:
        for cap in layout.capitals:
            points.append((cap.x, cap.y, cap.radius + 72))
        for _, x, y in getattr(layout, "village_slots", []):
            points.append((x, y, 44))
        for x, y in getattr(layout, "wild_slots", []):
            points.append((x, y, 44))

    for x, y in getattr(getattr(world, "settlements", None), "centers", []):
        points.append((x, y, 44))

    poi_markers = getattr(getattr(world, "spawner", None), "poi_markers", {})
    for marker in poi_markers.values():
        points.append((marker["x"], marker["y"], 36))

    for (wx, wy), tid in getattr(world, "overrides", {}).items():
        if tid in (CAMP, DUNGEON):
            points.append((wx, wy, 24))

    if player:
        points.append((player.x, player.y, 36))

    if not points:
        return (-128, -128, 128, 128)

    min_x = min(x - r for x, y, r in points)
    max_x = max(x + r for x, y, r in points)
    min_y = min(y - r for x, y, r in points)
    max_y = max(y + r for x, y, r in points)

    pad = 64
    return (min_x - pad, min_y - pad, max_x + pad, max_y + pad)


def _map_rects():
    pad = 20
    legend_w = min(280, max(220, SCREEN_W // 4))
    map_w = SCREEN_W - legend_w - pad * 3
    map_h = SCREEN_H - pad * 2
    map_rect = pygame.Rect(pad, pad, map_w, map_h)
    legend_rect = pygame.Rect(map_rect.right + pad, pad, legend_w, map_h)
    return map_rect, legend_rect


def _transform(bounds, rect):
    min_x, min_y, max_x, max_y = bounds
    world_w = max(1, max_x - min_x)
    world_h = max(1, max_y - min_y)
    scale = min(rect.w / world_w, rect.h / world_h)

    def to_screen(wx, wy):
        sx = rect.x + (wx - min_x) * scale
        sy = rect.y + (wy - min_y) * scale
        return sx, sy

    return to_screen, scale


def _collect_marker_clusters(world):
    overrides = getattr(world, "overrides", {})
    visited = set()
    markers = []

    for (wx, wy), tid in overrides.items():
        if tid not in (CAMP, DUNGEON) or (wx, wy) in visited:
            continue

        kind = "camp" if tid == CAMP else "dungeon"
        stack = deque([(wx, wy)])
        cluster = []
        visited.add((wx, wy))

        while stack:
            x, y = stack.pop()
            cluster.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in visited:
                        continue
                    if overrides.get((nx, ny)) == tid:
                        visited.add((nx, ny))
                        stack.append((nx, ny))

        if cluster:
            cx = sum(x for x, _ in cluster) / len(cluster)
            cy = sum(y for _, y in cluster) / len(cluster)
            markers.append({"kind": kind, "x": cx, "y": cy})

    return markers


def _marker_entries(world):
    markers = []
    layout = getattr(world, "layout", None)
    if layout:
        for cap in layout.capitals:
            markers.append({
                "kind": "capital",
                "x": cap.x,
                "y": cap.y,
                "label": cap.name,
                "radius": cap.radius,
            })

    for idx, (vx, vy) in enumerate(getattr(getattr(world, "settlements", None), "centers", [])):
        markers.append({
            "kind": "village",
            "x": vx,
            "y": vy,
            "label": f"Village {idx + 1}",
        })

    poi_markers = getattr(getattr(world, "spawner", None), "poi_markers", {})
    if poi_markers:
        for marker in poi_markers.values():
            markers.append({
                "kind": marker.get("kind", "camp"),
                "x": marker["x"],
                "y": marker["y"],
                "label": marker.get("kind", "poi").title(),
            })
    else:
        markers.extend({
            "kind": m["kind"],
            "x": m["x"],
            "y": m["y"],
            "label": m["kind"].title(),
        } for m in _collect_marker_clusters(world))

    return markers


def _cache_stamp(world):
    return (
        len(getattr(world, "overrides", {})),
        len(getattr(world, "buildings", [])),
        len(getattr(getattr(world, "settlements", None), "centers", [])),
        len(getattr(getattr(world, "spawner", None), "poi_markers", {})),
    )


def _biome_color(world, wx, wy):
    layout = getattr(world, "layout", None)
    if layout and getattr(layout, "world_extent", None):
        extent = int(layout.world_extent)
        if abs(wx) >= extent - 72 or abs(wy) >= extent - 72:
            return BIOME_COLORS["Mountain"]
    biome = world.peek_biome_at(int(wx), int(wy)) if hasattr(world, "peek_biome_at") else world.get_biome_at(int(wx), int(wy))
    return BIOME_COLORS.get(biome, (48, 88, 62))


def _draw_marker(screen, fonts, to_screen, marker, scale):
    kind = marker["kind"]
    x, y = to_screen(marker["x"], marker["y"])
    px, py = int(x), int(y)

    if kind == "capital":
        radius = max(10, int(marker.get("radius", 40) * scale))
        pygame.draw.circle(screen, (70, 88, 70), (px, py), radius + 4)
        pygame.draw.circle(screen, (170, 150, 110), (px, py), radius, 2)
        pygame.draw.rect(screen, (210, 190, 120), pygame.Rect(px - 4, py - 4, 8, 8))
        label = fonts["small"].render(marker["label"], True, TITLE)
        screen.blit(label, (px - label.get_width() // 2, py - radius - 18))
        return

    if kind == "village":
        pygame.draw.circle(screen, (170, 140, 95), (px, py), 4)
        return

    if kind == "camp":
        pygame.draw.polygon(screen, (200, 120, 80), [(px - 6, py + 5), (px, py - 6), (px + 6, py + 5)])
        pygame.draw.polygon(screen, (90, 50, 35), [(px - 6, py + 5), (px, py - 1), (px + 6, py + 5)], 1)
        return

    if kind == "dungeon":
        pygame.draw.polygon(screen, (80, 140, 220), [(px, py - 7), (px + 7, py), (px, py + 7), (px - 7, py)])
        pygame.draw.polygon(screen, (240, 210, 120), [(px, py - 4), (px + 4, py), (px, py + 4), (px - 4, py)], 1)
        return


def draw_world_map(screen, fonts, world, player):
    map_rect, legend_rect = _map_rects()
    bounds = _world_bounds(world, player)
    to_screen, scale = _transform(bounds, map_rect)

    # sfondo generale
    screen.fill(BG_DARK)
    pygame.draw.rect(screen, PAPER, map_rect, border_radius=10)
    pygame.draw.rect(screen, BORDER, map_rect, 2, border_radius=10)
    pygame.draw.rect(screen, PAPER_2, legend_rect, border_radius=10)
    pygame.draw.rect(screen, BORDER, legend_rect, 2, border_radius=10)

    # cache del layer terreno
    stamp = _cache_stamp(world)
    cache = getattr(world, "_map_cache", {})
    cache_key = (map_rect.size, bounds, stamp)
    if cache.get("key") != cache_key:
        terrain = pygame.Surface(map_rect.size, pygame.SRCALPHA)
        terrain.fill((0, 0, 0, 0))

        cols = max(20, map_rect.w // 32)
        rows = max(14, map_rect.h // 32)
        cell_w = map_rect.w / cols
        cell_h = map_rect.h / rows

        for row in range(rows):
            for col in range(cols):
                wx = bounds[0] + (col + 0.5) / cols * (bounds[2] - bounds[0])
                wy = bounds[1] + (row + 0.5) / rows * (bounds[3] - bounds[1])
                color = _biome_color(world, wx, wy)
                fill = (
                    max(0, min(255, int(color[0] * 0.85))),
                    max(0, min(255, int(color[1] * 0.85))),
                    max(0, min(255, int(color[2] * 0.85))),
                )
                pygame.draw.rect(
                    terrain,
                    fill,
                    pygame.Rect(int(col * cell_w), int(row * cell_h), int(cell_w) + 1, int(cell_h) + 1),
                )

        # linee leggere per dare una sensazione di carta/atlante
        grid_col = (255, 255, 255, 16)
        for row in range(0, map_rect.h, max(18, map_rect.h // 18)):
            pygame.draw.line(terrain, grid_col, (0, row), (map_rect.w, row), 1)
        for col in range(0, map_rect.w, max(18, map_rect.w // 18)):
            pygame.draw.line(terrain, grid_col, (col, 0), (col, map_rect.h), 1)

        cache = {"key": cache_key, "surface": terrain}
        world._map_cache = cache

    screen.blit(cache["surface"], map_rect.topleft)

    # overlay dei marker
    markers = _marker_entries(world)
    for marker in markers:
        _draw_marker(screen, fonts, to_screen, marker, scale)

    # marker del giocatore
    if player:
        px, py = to_screen(player.x, player.y)
        pygame.draw.circle(screen, (255, 235, 90), (int(px), int(py)), 5)
        pygame.draw.circle(screen, (40, 30, 0), (int(px), int(py)), 6, 1)

    # cornice e titolo
    title = fonts["bold"].render("WORLD MAP", True, TITLE)
    screen.blit(title, (map_rect.x + 14, map_rect.y + 10))
    hint = fonts["small"].render("M / ESC close   Capitals are fixed, camps and villages vary", True, DIM)
    screen.blit(hint, (map_rect.x + 14, map_rect.y + 10 + title.get_height() + 2))

    # legenda
    lx = legend_rect.x + 14
    ly = legend_rect.y + 14
    screen.blit(fonts["bold"].render("LEGEND", True, TITLE), (lx, ly))
    ly += 34

    legend_rows = [
        ((255, 235, 90), "Player"),
        ((210, 190, 120), "Capital"),
        ((170, 140, 95), "Village"),
        ((200, 120, 80), "Bandit camp"),
        ((80, 140, 220), "Dungeon entry"),
    ]
    for color, label in legend_rows:
        pygame.draw.rect(screen, color, pygame.Rect(lx, ly + 4, 12, 12))
        screen.blit(fonts["small"].render(label, True, TEXT), (lx + 20, ly + 1))
        ly += 24

    ly += 10
    if player:
        info = [
            f"Pos: {player.x}, {player.y}",
            f"Seed: {getattr(world, 'seed', 0)}",
            f"Cities: {len(getattr(getattr(world, 'layout', None), 'capitals', []))}",
            f"Villages: {len(getattr(getattr(world, 'settlements', None), 'centers', []))}",
        ]
        for line in info:
            screen.blit(fonts["small"].render(line, True, TEXT), (lx, ly))
            ly += 20

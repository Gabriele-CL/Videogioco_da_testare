# =============================================================================
# hud.py  —  HUD, minimap, pannello equipaggiamento/inventario, overlay notte
# =============================================================================
import math
import pygame
from core.constants import (SCREEN_W, SCREEN_H, TILE_W, TILE_H,
                             VIEW_COLS, VIEW_ROWS, TILE_COLOR,
                             NIGHT_OVERLAYS, RARITY_COLORS)


# ── Layout ────────────────────────────────────────────────────────────────────
PANEL_X  = VIEW_COLS * TILE_W
PANEL_W  = SCREEN_W  - PANEL_X
HUD_Y    = VIEW_ROWS * TILE_H

MM_SIZE  = min(PANEL_W - 4, 180)   # si adatta al pannello
MM_X     = PANEL_X + (PANEL_W - MM_SIZE) // 2
MM_Y     = 6

EQUIP_SLOTS = [
    ("Head",   "equipped_head",   "^"),
    ("Chest",  "equipped_armor",  "X"),
    ("Legs",   "equipped_legs",   "L"),
    ("Weapon", "equipped_weapon", "/"),
    ("Shield", "equipped_shield", "O"),
    ("Boots",  "equipped_boots",  "v"),
]


# =============================================================================
# MINIMAP
# =============================================================================
def draw_minimap(screen, fonts, minimap_surf, world, player):
    if PANEL_W < 20:
        return  # pannello troppo stretto, salta

    TP    = 3
    SHOWN = MM_SIZE // TP
    half  = SHOWN // 2
    p     = player

    # Ricrea la surface se ha dimensione sbagliata
    if minimap_surf.get_size() != (MM_SIZE, MM_SIZE):
        minimap_surf = pygame.Surface((MM_SIZE, MM_SIZE))

    minimap_surf.fill((8, 8, 8))

    for row in range(SHOWN):
        for col in range(SHOWN):
            wx   = p.x - half + col
            wy   = p.y - half + row
            tile = world.get_tile(wx, wy)
            base = TILE_COLOR.get(tile, (60, 60, 60))
            c    = (base[0] // 2, base[1] // 2, base[2] // 2)
            pygame.draw.rect(minimap_surf, c, (col * TP, row * TP, TP, TP))

    # Solo entità vive e visibili sulla minimappa
    for e in world.entities:
        if not getattr(e, "alive", False):
            continue
        ex = (e.x - p.x + half) * TP
        ey = (e.y - p.y + half) * TP
        if 0 <= ex < MM_SIZE and 0 <= ey < MM_SIZE:
            pygame.draw.rect(minimap_surf, e.color, (ex, ey, TP, TP))

    # Giocatore — punto giallo al centro
    cx_ = half * TP + TP // 2
    cy_ = half * TP + TP // 2
    pygame.draw.circle(minimap_surf, (255, 255, 0), (cx_, cy_), 4)

    pygame.draw.rect(minimap_surf, (70, 90, 140), (0, 0, MM_SIZE, MM_SIZE), 1)
    screen.blit(minimap_surf, (MM_X, MM_Y))


# =============================================================================
# PANNELLO EQUIP — più largo, nomi completi
# =============================================================================
def draw_equip_panel(screen, fonts, player):
    p      = player
    top_y  = MM_Y + MM_SIZE + 14
    slot_h = 26
    slot_w = PANEL_W - 8          # usa quasi tutto il pannello
    sx     = PANEL_X + 4

    pygame.draw.rect(screen, (10, 13, 10),
                     pygame.Rect(PANEL_X, top_y - 4, PANEL_W,
                                 len(EQUIP_SLOTS) * (slot_h + 3) + 24))

    for i, (label, attr, icon) in enumerate(EQUIP_SLOTS):
        item   = getattr(p, attr, None)
        sy     = top_y + 14 + i * (slot_h + 3)
        bg     = (18, 28, 18) if item else (13, 13, 17)
        border = (55, 85, 55) if item else (38, 38, 52)

        pygame.draw.rect(screen, bg,     pygame.Rect(sx, sy, slot_w, slot_h))
        pygame.draw.rect(screen, border, pygame.Rect(sx, sy, slot_w, slot_h), 1)

        # Icona + label slot
        screen.blit(fonts["small"].render(icon,  True, (90, 130, 90)), (sx + 3,  sy + 5))
        screen.blit(fonts["small"].render(label, True, (80, 115, 80)), (sx + 16, sy + 5))

        if item:
            col  = RARITY_COLORS.get(getattr(item, "rarity", "common"), (200, 200, 200))
            # Calcola spazio disponibile per il nome
            label_w   = fonts["small"].size(label)[0] + 24
            avail_w   = slot_w - label_w - 6
            char_w    = max(1, fonts["small"].size("A")[0])
            max_chars = max(4, avail_w // char_w)
            name_crop = item.name[:max_chars]
            ns = fonts["small"].render(name_crop, True, col)
            screen.blit(ns, (sx + slot_w - ns.get_width() - 4, sy + 5))
        else:
            es = fonts["small"].render("—", True, (48, 48, 52))
            screen.blit(es, (sx + slot_w - es.get_width() - 4, sy + 5))


# =============================================================================
# INVENTARIO OVERLAY
# =============================================================================
def draw_inventory_panel(screen, fonts, player, cursor):
    p   = player
    PAD = 8
    sx  = PANEL_X + PAD
    sw  = PANEL_W - PAD * 2

    pygame.draw.rect(screen, (8, 10, 8),
                     pygame.Rect(PANEL_X, 0, PANEL_W, SCREEN_H))
    pygame.draw.line(screen, (50, 80, 50), (PANEL_X, 0), (PANEL_X, SCREEN_H), 1)

    title = fonts["small"].render("== Inventory ==", True, (120, 200, 120))
    screen.blit(title, (PANEL_X + (PANEL_W - title.get_width()) // 2, 6))

    ey0 = 28; slh = 22; slw = PANEL_W // 2 - PAD - 2

    for i, (label, attr, icon) in enumerate(EQUIP_SLOTS):
        item = getattr(p, attr, None)
        sy   = ey0 + i * (slh + 3)
        bg   = (18, 28, 18) if item else (12, 12, 16)
        pygame.draw.rect(screen, bg,           pygame.Rect(sx, sy, slw, slh))
        pygame.draw.rect(screen, (50, 75, 50), pygame.Rect(sx, sy, slw, slh), 1)
        screen.blit(fonts["small"].render(icon,  True, (80, 120, 80)), (sx + 3,  sy + 4))
        screen.blit(fonts["small"].render(label, True, (70, 100, 70)), (sx + 16, sy + 4))
        if item:
            col = RARITY_COLORS.get(getattr(item, "rarity", "common"), (200, 200, 200))
            ns  = fonts["small"].render(item.name[:9], True, col)
            screen.blit(ns, (sx + slw - ns.get_width() - 3, sy + 4))

    stats_x = PANEL_X + PANEL_W // 2 + 2
    stats   = [
        f"ATK  {p.attack_damage()}",
        f"DEF  {p.defense()}",
        f"HP   {p.health}/{p.max_health}",
        f"ST   {p.stamina}/{p.max_stamina}",
        f"LV   {p.level}",
        f"XP   {p.xp}/{p.xp_to_next()}",
    ]
    for i, s in enumerate(stats):
        screen.blit(fonts["small"].render(s, True, (160, 200, 160)),
                    (stats_x, ey0 + i * 25 + 2))

    sep_y = ey0 + len(EQUIP_SLOTS) * (slh + 3) + 6
    pygame.draw.line(screen, (50, 80, 50), (PANEL_X + 4, sep_y), (SCREEN_W - 4, sep_y), 1)

    inv    = p.inventory
    list_y = sep_y + 6
    row_h  = 20
    vis    = (SCREEN_H - list_y - 28) // row_h

    if not inv:
        screen.blit(fonts["small"].render("(empty)", True, (80, 80, 80)), (sx, list_y))
    else:
        start = max(0, cursor - vis + 1)
        for i, item in enumerate(inv[start: start + vis]):
            idx = start + i
            sel = idx == cursor
            bg  = (30, 50, 30) if sel else (10, 12, 10)
            iy  = list_y + i * row_h
            pygame.draw.rect(screen, bg, pygame.Rect(sx, iy, sw, row_h - 1))
            col = RARITY_COLORS.get(getattr(item, "rarity", "common"), (200, 200, 200))
            if item.item_type == "weapon":
                bonus = f"+{item.stats.get('damage', 0)}ATK"
            elif item.item_type in ("armor", "helmet", "legs", "shield", "boots"):
                bonus = f"+{item.stats.get('defense', 0)}DEF"
            elif item.item_type == "potion":
                bonus = f"+{item.stats.get('heal', 0)}HP"
            elif item.item_type == "material":
                bonus = "mat."
            else:
                bonus = f"[{item.item_type[:4]}]"
            prefix       = ">" if sel else " "
            bonus_surf   = fonts["small"].render(bonus, True, col)
            prefix_w     = fonts["small"].size(f"{prefix} ")[0]
            avail_w      = sw - prefix_w - bonus_surf.get_width() - 8
            max_chars    = max(4, avail_w // max(1, fonts["small"].size("A")[0]))
            name_cropped = item.name[:max_chars]
            screen.blit(fonts["small"].render(f"{prefix} {name_cropped}", True, col),
                        (sx + 2, iy + 2))
            screen.blit(bonus_surf, (sx + sw - bonus_surf.get_width() - 2, iy + 2))

    leg = fonts["small"].render("W/S nav  INVIO equip  D butta  I chiudi",
                                True, (80, 110, 80))
    screen.blit(leg, (PANEL_X + (PANEL_W - leg.get_width()) // 2, SCREEN_H - 22))


# =============================================================================
# HUD — due righe compatte che non sforano
# =============================================================================
def draw_hud(screen, fonts, player, biome: str, time_str: str):
    p = player

    hp_pct = max(0.0, min(1.0, p.health  / max(1, p.max_health)))
    st_pct = max(0.0, min(1.0, p.stamina / max(1, p.max_stamina)))
    xp_pct = max(0.0, min(1.0, p.xp      / max(1, p.xp_to_next())))
    hp_col = (max(0, min(255, int(255*(1-hp_pct)))), max(0, min(255, int(255*hp_pct))), 0)

    hud_h = SCREEN_H - HUD_Y
    pygame.draw.rect(screen, (10, 10, 18), pygame.Rect(0, HUD_Y, SCREEN_W, hud_h))
    pygame.draw.line(screen, (40, 40, 80), (0, HUD_Y), (SCREEN_W, HUD_Y), 1)

    # ── Barre HP/ST/XP con etichetta + valore a destra ───────────────────────
    bar_w, bar_h = 200, 10
    bar_x = 28
    fsm = fonts["small"]

    bars = [
        ("HP", hp_pct, hp_col,               f"{p.health}/{p.max_health}"),
        ("ST", st_pct, (50, 100, 220),        f"{p.stamina}/{p.max_stamina}"),
        ("XP", xp_pct, (200, 140, 0),         f"Lv.{p.level}"),
    ]
    for i, (lbl, pct, col, val_str) in enumerate(bars):
        by = HUD_Y + 4 + i * (bar_h + 5)
        pygame.draw.rect(screen, (33, 33, 44),  pygame.Rect(bar_x, by, bar_w, bar_h))
        pygame.draw.rect(screen, col,            pygame.Rect(bar_x, by, int(bar_w * pct), bar_h))
        pygame.draw.rect(screen, (65, 65, 105), pygame.Rect(bar_x, by, bar_w, bar_h), 1)
        screen.blit(fsm.render(lbl, True, (180, 180, 180)), (bar_x - 22, by))
        val_surf = fsm.render(val_str, True, (200, 200, 200))
        screen.blit(val_surf, (bar_x + bar_w + 4, by))

    # ── Testo HUD (due righe) ─────────────────────────────────────────────────
    tx    = bar_x + bar_w + 90   # spazio sufficiente dopo i valori barra
    max_w = PANEL_X - tx - 4
    char_w = max(1, fsm.size("A")[0])
    max_ch = max(10, max_w // char_w)

    row1 = f"Age:{p.age} {p.life_stage.value}  Gold:{p.gold}g"
    row2 = time_str
    row3 = "I Inventario   J Diario   M Mappa   ESC Pausa"

    screen.blit(fsm.render(row1[:max_ch], True, (220, 220, 150)), (tx, HUD_Y + 4))
    screen.blit(fsm.render(row2[:max_ch], True, (150, 200, 150)), (tx, HUD_Y + 22))
    screen.blit(fsm.render(row3[:max_ch], True, (120, 150, 200)), (tx, HUD_Y + 40))

# =============================================================================
# OVERLAY NOTTE
# =============================================================================
def draw_night_overlay(screen, time_of_day: str):
    ov = NIGHT_OVERLAYS.get(time_of_day)
    if ov is None:
        return
    color, alpha = ov
    s = pygame.Surface((VIEW_COLS * TILE_W, VIEW_ROWS * TILE_H), pygame.SRCALPHA)
    s.fill((*color, alpha))
    screen.blit(s, (0, 0))

# =============================================================================
# combat/combat_ui.py — Rendering HUD combattimento a turni
# =============================================================================
import pygame
from combat.combat import CombatPhase, MenuFocus, ActionButton


C_BG        = (12, 10, 18)
C_BORDER    = (90, 70, 130)
C_BORDER_HL = (180, 150, 220)
C_TEXT      = (210, 200, 230)
C_DIM       = (100, 90, 110)
C_HP_BAR    = (50, 200, 80)
C_HP_LOW    = (220, 60, 60)
C_BTN_BG    = (25, 20, 38)
C_BTN_HL    = (55, 45, 80)
C_TITLE     = (200, 170, 255)
C_LOG       = (160, 150, 180)


BIOME_COLORS = {
    "Grassland": (20, 40, 20),
    "Forest":    (10, 30, 15),
    "Mountain":  (30, 30, 40),
    "Swamp":     (20, 35, 25),
    "Road":      (35, 30, 20),
    "River":     (15, 25, 45),
    "Desert":    (50, 40, 15),
}

BUTTON_LABELS = ["Attacco", "Abilità", "Guardia", "Oggetti", "Fuga"]


def _draw_rect_border(surf, color, rect, width=2, radius=6):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def _draw_hp_bar(surf, x, y, w, h, cur, mx):
    ratio = max(0.0, cur / mx) if mx > 0 else 0.0
    col   = C_HP_BAR if ratio > 0.3 else C_HP_LOW
    pygame.draw.rect(surf, (30, 30, 30), pygame.Rect(x, y, w, h), border_radius=3)
    if ratio > 0:
        pygame.draw.rect(surf, col, pygame.Rect(x, y, int(w * ratio), h), border_radius=3)
    _draw_rect_border(surf, C_DIM, pygame.Rect(x, y, w, h), 1, 3)


def draw_combat(screen, fonts, state):
    SW, SH = screen.get_size()
    PAD    = 18

    # ── schermo nero intro / outro ──────────────────────────────────────
    if state.phase in (CombatPhase.INTRO, CombatPhase.OUTRO):
        alpha = int(255 * (1 - state.intro_timer / 0.8)) if state.phase == CombatPhase.INTRO \
                else int(255 * (state.outro_timer / 0.8))
        alpha = max(0, min(255, alpha))
        fade  = pygame.Surface((SW, SH))
        fade.fill((0, 0, 0))
        fade.set_alpha(alpha)
        screen.fill(C_BG)
        screen.blit(fade, (0, 0))
        return

    screen.fill(C_BG)

    # ── layout ──────────────────────────────────────────────────────────
    top_h    = int(SH * 0.52)
    bot_h    = SH - top_h - PAD * 2
    top_rect = pygame.Rect(PAD, PAD, SW - PAD * 2, top_h)
    bot_rect = pygame.Rect(PAD, PAD + top_h + PAD, SW - PAD * 2, bot_h)

    btn_w    = int((SW - PAD * 2) * 0.22)
    sub_x    = PAD + btn_w + PAD
    sub_w    = SW - PAD * 2 - btn_w - PAD
    btn_rect = pygame.Rect(PAD,   bot_rect.y, btn_w, bot_h)
    sub_rect = pygame.Rect(sub_x, bot_rect.y, sub_w, bot_h)

    # ── rettangolo superiore ────────────────────────────────────────────
    bg_col = BIOME_COLORS.get(state.biome, (20, 20, 30))
    pygame.draw.rect(screen, bg_col, top_rect, border_radius=8)
    _draw_rect_border(screen, C_BORDER, top_rect, 2, 8)
    _draw_enemy_panel(screen, fonts, state, top_rect)

    # ── log messaggi temporizzati nel pannello superiore ────────────────
    _draw_log(screen, fonts, state, top_rect)

    # ── colonna sinistra: bottoni ────────────────────────────────────────
    pygame.draw.rect(screen, C_BTN_BG, btn_rect, border_radius=6)
    _draw_rect_border(screen, C_BORDER, btn_rect, 1, 6)
    _draw_buttons(screen, fonts, state, btn_rect)

    # ── colonna destra: sotto-menù o stats giocatore ────────────────────
    pygame.draw.rect(screen, C_BTN_BG, sub_rect, border_radius=6)
    _draw_rect_border(screen, C_BORDER, sub_rect, 1, 6)

    if state.phase == CombatPhase.FLEE_FAILED:
        _draw_flee_failed_banner(screen, fonts, sub_rect)
    elif state.focus in (MenuFocus.SUBMENU, MenuFocus.TARGET):
        _draw_submenu(screen, fonts, state, sub_rect)
    else:
        _draw_player_stats(screen, fonts, state, sub_rect)

    # ── floating damage texts ────────────────────────────────────────────
    _draw_floats(screen, fonts, state, top_rect, sub_rect)

    # ── popup Info ───────────────────────────────────────────────────────
    if state.info_popup:
        _draw_info_popup(screen, fonts, state.info_popup, SW, SH)

    # ── schermata vittoria / sconfitta ──────────────────────────────────
    if state.phase == CombatPhase.VICTORY:
        _draw_end_banner(screen, fonts, state, SW, SH, victory=True)
    elif state.phase == CombatPhase.DEFEAT:
        _draw_end_banner(screen, fonts, state, SW, SH, victory=False)


# ---------------------------------------------------------------------------
# Sotto-funzioni di rendering
# ---------------------------------------------------------------------------
def _draw_enemy_panel(screen, fonts, state, rect):
    e   = state.enemy
    fsm = fonts["small"]
    fno = fonts["normal"]
    cx  = rect.centerx
    cy  = rect.centery

    ph_r = min(rect.w, rect.h) // 4
    pygame.draw.circle(screen, e.color, (cx - rect.w // 5, cy), ph_r)
    sym = fno.render(e.symbol, True, (10, 10, 10))
    screen.blit(sym, sym.get_rect(center=(cx - rect.w // 5, cy)))

    if state.focus == MenuFocus.TARGET or state.phase == CombatPhase.VICTORY:
        tri_x = cx - rect.w // 5
        tri_y = cy - ph_r - 12
        pygame.draw.polygon(screen, (255, 220, 50),
                            [(tri_x, tri_y + 10), (tri_x - 8, tri_y), (tri_x + 8, tri_y)])

    name_s = fonts["bold"].render(f"{e.name} Lv.{getattr(e, 'level', 1)}", True, C_TITLE)
    screen.blit(name_s, (cx + 20, rect.y + 18))

    bar_x = cx + 20
    bar_y = rect.y + 18 + name_s.get_height() + 6
    bar_w = rect.right - bar_x - 20
    _draw_hp_bar(screen, bar_x, bar_y, bar_w, 14, e.health, e.max_health)

    hp_s = fsm.render(f"{max(0, e.health)} / {e.max_health} HP", True, C_TEXT)
    screen.blit(hp_s, (bar_x, bar_y + 18))


def _draw_log(screen, fonts, state, top_rect):
    """Messaggi temporizzati in basso a destra del rettangolo superiore, con fade out."""
    if not state.timed_log:
        return

    fnt  = fonts["small"]
    lh   = fnt.get_height() + 4
    PAD  = 12
    MAX_W = top_rect.w // 2      # occupa metà destra del pannello superiore

    msgs = state.timed_log[-4:]  # max 4 messaggi visibili
    total_h = len(msgs) * lh
    base_y  = top_rect.bottom - total_h - PAD
    base_x  = top_rect.right - MAX_W - PAD

    for i, msg in enumerate(msgs):
        # fade out nell'ultimo secondo
        alpha = min(255, int(255 * min(1.0, msg["timer"])))
        y = base_y + i * lh

        # sfondo semitrasparente per leggibilità sul bioma colorato
        bg = pygame.Surface((MAX_W, lh))
        bg.set_alpha(int(alpha * 0.6))
        bg.fill((0, 0, 0))
        screen.blit(bg, (base_x, y))

        # testo con fade
        s = fnt.render(msg["text"][:55], True, msg["color"])
        s.set_alpha(alpha)
        screen.blit(s, (base_x + 6, y + 2))


def _draw_buttons(screen, fonts, state, rect):
    PAD = 8
    fnt = fonts["small"]
    bh  = (rect.h - PAD * 2) // len(BUTTON_LABELS)

    for i, label in enumerate(BUTTON_LABELS):
        br  = pygame.Rect(rect.x + PAD, rect.y + PAD + i * bh, rect.w - PAD * 2, bh - 4)
        sel = (i == state.selected_button)
        bg  = C_BTN_HL if sel else C_BTN_BG
        pygame.draw.rect(screen, bg, br, border_radius=4)
        col = C_BORDER_HL if (sel and state.focus == MenuFocus.BUTTONS) else C_BORDER
        _draw_rect_border(screen, col, br, 1 + int(sel), 4)
        txt = fnt.render(label, True, C_TITLE if sel else C_TEXT)
        screen.blit(txt, txt.get_rect(center=br.center))


def _draw_player_stats(screen, fonts, state, rect):
    p   = state.player
    fsm = fonts["small"]
    fbo = fonts["bold"]
    x   = rect.x + 14
    y   = rect.y + 14

    name_s = fbo.render(f"{p.name} Lv.{p.level}", True, C_TITLE)
    screen.blit(name_s, (x, y))
    y += name_s.get_height() + 8

    _draw_hp_bar(screen, x, y, rect.w - 28, 14, p.health, p.max_health)
    y += 20
    hp_s = fsm.render(f"{max(0, p.health)} / {p.max_health} HP", True, C_TEXT)
    screen.blit(hp_s, (x, y))
    y += hp_s.get_height() + 10

    cls_s = fsm.render(p.char_class.value, True, C_DIM)
    screen.blit(cls_s, (x, y))

    if state.guard_active:
        g = fsm.render("[ IN GUARDIA ]", True, (150, 220, 255))
        screen.blit(g, g.get_rect(centerx=rect.centerx, y=y + 26))


def _draw_submenu(screen, fonts, state, rect):
    btn = ActionButton(state.selected_button)
    fsm = fonts["small"]
    PAD = 10
    x   = rect.x + PAD
    y   = rect.y + PAD
    lh  = 22

    if btn == ActionButton.FLEE:
        q = fsm.render("Vuoi tentare di fuggire?", True, C_TEXT)
        screen.blit(q, (x, y))
        y += lh + 8
        ox = x
        for idx, label in enumerate(["Sì", "No"]):
            sel = (idx == state.flee_cursor)
            col = C_TITLE if sel else C_TEXT
            br  = pygame.Rect(ox, y, 60, lh)
            if sel:
                pygame.draw.rect(screen, C_BTN_HL, br, border_radius=4)
                _draw_rect_border(screen, C_BORDER_HL, br, 1, 4)
            screen.blit(fsm.render(label, True, col), (ox + 8, y + 2))
            ox += 70
        return

    if btn == ActionButton.ATTACK:
        options = ["Mani nude (base)"]
        p = state.player
        if p.equipped_weapon:
            dmg = p.equipped_weapon.stats.get("damage", 5)
            options.append(f"{p.equipped_weapon.name} [{dmg} dmg]")
        items_list = options

    elif btn == ActionButton.ABILITY:
        items_list = [f'{a["name"]}' for a in state.get_abilities()]
        if not items_list:
            screen.blit(fsm.render("Nessuna abilità disponibile.", True, C_DIM), (x, y))
            return

    elif btn == ActionButton.ITEMS:
        usable = state.get_usable_items()
        if not usable:
            screen.blit(fsm.render("Nessun oggetto utilizzabile.", True, C_DIM), (x, y))
            return
        items_list = []
        for it in usable:
            if it.item_type == "potion":
                items_list.append(f'{it.name} [+{it.stats.get("heal", 0)} HP]')
            else:
                items_list.append(f'{it.name} [{it.stats.get("damage", 0)} dmg]')
    else:
        return

    hint = fsm.render("[I] Info  [Backspace] Indietro", True, C_DIM)
    screen.blit(hint, (x, rect.bottom - hint.get_height() - 6))

    for i, label in enumerate(items_list):
        sel = (i == state.submenu_cursor)
        col = C_TITLE if sel else C_TEXT
        br  = pygame.Rect(x, y, rect.w - PAD * 2, lh)
        if sel:
            pygame.draw.rect(screen, C_BTN_HL, br, border_radius=3)
            _draw_rect_border(screen, C_BORDER_HL, br, 1, 3)
        screen.blit(fsm.render(label[:45], True, col), (x + 4, y + 2))
        if btn in (ActionButton.ABILITY, ActionButton.ITEMS) and sel:
            info_s = fsm.render("[I]", True, (150, 200, 255))
            screen.blit(info_s, (rect.right - info_s.get_width() - PAD, y + 2))
        y += lh + 2

    if state.focus == MenuFocus.TARGET:
        msg = fsm.render("INVIO: conferma | Backspace: annulla", True, (150, 220, 150))
        screen.blit(msg, msg.get_rect(centerx=rect.centerx, y=rect.bottom - 22))


def _draw_flee_failed_banner(screen, fonts, sub_rect):
    fla = fonts["large"]
    fsm = fonts["small"]

    overlay = pygame.Surface((sub_rect.w, sub_rect.h))
    overlay.set_alpha(230)
    overlay.fill((28, 10, 10))
    screen.blit(overlay, (sub_rect.x, sub_rect.y))
    _draw_rect_border(screen, (200, 60, 60), sub_rect, 2, 6)

    title = fla.render("Fuga fallita!", True, (220, 80, 80))
    screen.blit(title, title.get_rect(
        centerx=sub_rect.centerx, y=sub_rect.y + sub_rect.h // 4
    ))

    sub = fsm.render("Il nemico approfitta della tua esitazione...", True, C_TEXT)
    screen.blit(sub, sub.get_rect(
        centerx=sub_rect.centerx, y=sub_rect.y + sub_rect.h // 2
    ))

    cont = fsm.render("[INVIO] continua", True, C_DIM)
    screen.blit(cont, cont.get_rect(
        centerx=sub_rect.centerx, y=sub_rect.bottom - 28
    ))


def _draw_floats(screen, fonts, state, top_rect, sub_rect):
    fnt = fonts["normal"]
    for f in state.floats:
        alpha = int(255 * min(1.0, f["timer"] / 0.6))
        surf  = fnt.render(f["text"], True, f["color"])
        surf.set_alpha(alpha)
        if f["side"] == "enemy":
            x = top_rect.centerx - top_rect.w // 5 + 20
            y = top_rect.centery - 30 + int((1.2 - f["timer"]) * 20)
        else:
            x = sub_rect.x + 40
            y = sub_rect.y + 30 + int((1.2 - f["timer"]) * 20)
        screen.blit(surf, (x, y))


def _draw_info_popup(screen, fonts, popup, SW, SH):
    fsm = fonts["small"]
    fbo = fonts["bold"]
    pw, ph = 340, 120
    px = (SW - pw) // 2
    py = (SH - ph) // 2
    prect = pygame.Rect(px, py, pw, ph)
    pygame.draw.rect(screen, (18, 14, 28), prect, border_radius=8)
    _draw_rect_border(screen, C_BORDER_HL, prect, 2, 8)
    name_s = fbo.render(popup.get("name", ""), True, C_TITLE)
    screen.blit(name_s, (px + 14, py + 12))
    desc  = popup.get("desc", popup.get("description", ""))
    words, line, lines = desc.split(), "", []
    for w in words:
        test = (line + " " + w).strip()
        if fsm.size(test)[0] < pw - 28:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    for i, l in enumerate(lines[:3]):
        screen.blit(fsm.render(l, True, C_TEXT), (px + 14, py + 38 + i * 18))
    hint = fsm.render("[Backspace] chiudi", True, C_DIM)
    screen.blit(hint, (px + 14, py + ph - 22))


def _draw_end_banner(screen, fonts, state, SW, SH, victory: bool):
    fla = fonts["large"]
    fsm = fonts["small"]
    bw, bh = 420, 140
    bx = (SW - bw) // 2
    by = (SH - bh) // 2
    brect = pygame.Rect(bx, by, bw, bh)
    pygame.draw.rect(screen, (10, 8, 20), brect, border_radius=10)
    col = (100, 220, 130) if victory else (220, 80, 80)
    _draw_rect_border(screen, col, brect, 2, 10)

    if victory:
        title = fla.render("VITTORIA!", True, col)
        sub   = fsm.render(f"+{state.xp_gained} XP  |  +{state.gold_gained} oro", True, C_TEXT)
        if state.loot_item:
            loot = fsm.render(f"Loot: {state.loot_item.name}!", True, (200, 180, 80))
            screen.blit(loot, loot.get_rect(centerx=SW // 2, y=by + 90))
    else:
        title = fla.render("SCONFITTA", True, col)
        sub   = fsm.render("Il tuo personaggio è caduto...", True, C_DIM)

    screen.blit(title, title.get_rect(centerx=SW // 2, y=by + 18))
    screen.blit(sub,   sub.get_rect(centerx=SW // 2,   y=by + 60))
    cont = fsm.render("[INVIO] continua", True, C_DIM)
    screen.blit(cont,  cont.get_rect(centerx=SW // 2,  y=by + bh - 24))

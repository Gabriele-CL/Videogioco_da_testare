# =============================================================================
# ui/journal_ui.py — Rendering del diario di gioco
# =============================================================================
import pygame
from core.journal import EVENT_CATEGORIES

C_BG       = (10,  8, 18)
C_BORDER   = (90, 70, 130)
C_TITLE    = (200, 170, 255)
C_DIM      = (100,  90, 110)
C_TEXT     = (210, 200, 230)
C_SELECTED = (55,  45,  80)
C_TAB_ACT  = (180, 150, 220)
C_TAB_IDLE = (60,  50,  90)

CATEGORIES = ["all"] + list(EVENT_CATEGORIES.keys())
CAT_LABELS  = ["Tutti"] + [v["label"] for v in EVENT_CATEGORIES.values()]


def draw_journal(screen, fonts, journal, cursor: int, tab: int) -> None:
    SW, SH = screen.get_size()
    PAD    = 24
    W, H   = SW - PAD * 2, SH - PAD * 2
    rect   = pygame.Rect(PAD, PAD, W, H)

    # sfondo
    overlay = pygame.Surface((SW, SH))
    overlay.set_alpha(220)
    overlay.fill(C_BG)
    screen.blit(overlay, (0, 0))
    pygame.draw.rect(screen, C_BG, rect, border_radius=10)
    pygame.draw.rect(screen, C_BORDER, rect, 2, border_radius=10)

    fsm  = fonts["small"]
    fbo  = fonts["bold"]
    fno  = fonts["normal"]

    # titolo
    title = fbo.render("📖  Diario di Avventura", True, C_TITLE)
    screen.blit(title, (PAD + 16, PAD + 12))

    hint = fsm.render("[J / ESC] chiudi   [←→] categoria   [↑↓] scorri", True, C_DIM)
    screen.blit(hint, (PAD + 16, PAD + 12 + title.get_height() + 4))

    # ── tab categorie ────────────────────────────────────────────────
    tab_y  = PAD + 12 + title.get_height() + hint.get_height() + 14
    tab_x  = PAD + 16
    tab_h  = 22
    tab_w  = (W - 32) // len(CATEGORIES)

    for i, label in enumerate(CAT_LABELS):
        tr  = pygame.Rect(tab_x + i * tab_w, tab_y, tab_w - 4, tab_h)
        sel = (i == tab)
        pygame.draw.rect(screen, C_TAB_ACT if sel else C_TAB_IDLE, tr, border_radius=4)
        col = (255, 255, 255) if sel else C_DIM
        ts  = fsm.render(label, True, col)
        screen.blit(ts, ts.get_rect(center=tr.center))

    # ── lista voci ───────────────────────────────────────────────────
    list_y     = tab_y + tab_h + 10
    list_h     = H - (list_y - PAD) - 12
    line_h     = fsm.get_height() + 5
    max_vis    = list_h // line_h

    # filtra per categoria
    cat_key = CATEGORIES[tab]
    if cat_key == "all":
        entries = list(reversed(journal.entries))   # più recenti prima
    else:
        entries = list(reversed(journal.get_by_category(cat_key)))

    if not entries:
        empty = fsm.render("Nessuna voce per questa categoria.", True, C_DIM)
        screen.blit(empty, (PAD + 16, list_y + 20))
        return

    # clamp cursore
    cursor = max(0, min(cursor, len(entries) - 1))

    # scroll: centra il cursore nella lista visibile
    start = max(0, cursor - max_vis // 2)
    start = min(start, max(0, len(entries) - max_vis))

    for i, entry in enumerate(entries[start: start + max_vis]):
        idx = start + i
        y   = list_y + i * line_h
        sel = (idx == cursor)

        if sel:
            pygame.draw.rect(screen, C_SELECTED,
                             pygame.Rect(PAD + 10, y - 2, W - 20, line_h), border_radius=3)

        col  = entry.color() if not sel else (255, 255, 255)
        text = entry.display_str()
        ts   = fsm.render(text[:95], True, col)
        screen.blit(ts, (PAD + 16, y))

    # scrollbar minimale
    if len(entries) > max_vis:
        sb_x   = PAD + W - 10
        sb_h   = list_h
        thumb  = max(20, int(sb_h * max_vis / len(entries)))
        thumb_y = list_y + int((sb_h - thumb) * start / max(1, len(entries) - max_vis))
        pygame.draw.rect(screen, C_DIM,    pygame.Rect(sb_x, list_y, 4, sb_h), border_radius=2)
        pygame.draw.rect(screen, C_BORDER, pygame.Rect(sb_x, thumb_y, 4, thumb), border_radius=2)
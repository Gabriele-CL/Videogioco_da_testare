# =============================================================================
# ui/menus.py — Tutte le schermate di menu del gioco
# =============================================================================
import pygame
from core.constants import (SCREEN_W, SCREEN_H,
                             ESSENZA_ATTRS, ESSENZA_POINTS,
                             ESSENZA_MIN, ESSENZA_MAX)

# ─────────────────────────────────────────────────────────────────────────────
# Utilità interne
# ─────────────────────────────────────────────────────────────────────────────
def _center_x(surf, screen_w=SCREEN_W):
    return (screen_w - surf.get_width()) // 2

def _title(screen, fonts, text="ROGUE LIFE", y=80):
    t = fonts["large"].render(text, True, (255, 220, 50))
    screen.blit(t, (_center_x(t), y))
    sub = fonts["normal"].render("Eldoria Chronicles", True, (150, 150, 200))
    screen.blit(sub, (_center_x(sub), y + 36))

# ─────────────────────────────────────────────────────────────────────────────
# 1. SPLASH — "Premi un qualsiasi tasto per continuare"
# ─────────────────────────────────────────────────────────────────────────────
def draw_splash(screen, fonts, tick: float):
    """Schermata di apertura. tick serve per far lampeggiare il testo."""
    screen.fill((5, 5, 15))
    _title(screen, fonts, y=180)
    if int(tick * 2) % 2 == 0:
        hint = fonts["normal"].render("Premi un qualsiasi tasto per continuare", True, (180, 180, 180))
        screen.blit(hint, (_center_x(hint), SCREEN_H - 120))

# ─────────────────────────────────────────────────────────────────────────────
# 2. MAIN MENU — Nuova Partita / Continua / Opzioni  (stile Dark Souls)
# ─────────────────────────────────────────────────────────────────────────────
MAIN_MENU_ITEMS = ["Nuova Partita", "Continua", "Opzioni"]

def draw_main_menu(screen, fonts, selected: int, has_save: bool):
    screen.fill((5, 5, 15))
    _title(screen, fonts, y=100)
    for i, item in enumerate(MAIN_MENU_ITEMS):
        active = (i == selected)
        # "Continua" è grigia se non c'è salvataggio
        if item == "Continua" and not has_save:
            col = (80, 80, 80)
        else:
            col = (255, 255, 200) if active else (160, 160, 180)
        prefix = ">  " if active else "   "
        line = fonts["large"].render(f"{prefix}{item}", True, col)
        y = SCREEN_H // 2 - 10 + i * 48
        screen.blit(line, (_center_x(line), y))
    hint = fonts["small"].render("SU/GIU per navigare  |  INVIO per selezionare", True, (80, 80, 100))
    screen.blit(hint, (_center_x(hint), SCREEN_H - 40))

# ─────────────────────────────────────────────────────────────────────────────
# 3. OPTIONS — schermata nera placeholder
# ─────────────────────────────────────────────────────────────────────────────
def draw_options(screen, fonts):
    screen.fill((0, 0, 0))
    t = fonts["large"].render("OPZIONI", True, (200, 200, 200))
    screen.blit(t, (_center_x(t), SCREEN_H // 2 - 30))
    h = fonts["normal"].render("Backspace per tornare indietro", True, (100, 100, 100))
    screen.blit(h, (_center_x(h), SCREEN_H // 2 + 20))

# ─────────────────────────────────────────────────────────────────────────────
# 4. MENU NOME — inserimento nome (senza Hall of Fame)
# ─────────────────────────────────────────────────────────────────────────────
def draw_menu_name(screen, fonts, name_input: str, dead_chars: list = None):
    screen.fill((5, 5, 15))
    _title(screen, fonts, y=80)
    prompt = fonts["normal"].render("Inserisci il tuo nome:", True, (200, 200, 200))
    screen.blit(prompt, (_center_x(prompt), 220))
    name_surf = fonts["bold"].render(name_input + "_", True, (255, 255, 100))
    screen.blit(name_surf, (_center_x(name_surf), 252))
    hint = fonts["small"].render("Premi INVIO per continuare", True, (100, 150, 100))
    screen.blit(hint, (_center_x(hint), 310))

# ─────────────────────────────────────────────────────────────────────────────
# 5. SCHERMATE INTRO (3 messaggi sequenziali)
# ─────────────────────────────────────────────────────────────────────────────
def draw_intro_screen(screen, fonts, message: str, tick: float):
    """Schermata nera con testo centrato + "continua..." lampeggiante."""
    screen.fill((5, 5, 15))
    msg = fonts["large"].render(message, True, (220, 200, 160))
    screen.blit(msg, (_center_x(msg), SCREEN_H // 2 - 20))
    if int(tick * 2) % 2 == 0:
        c = fonts["small"].render("Premi un tasto per continuare", True, (80, 80, 100))
        screen.blit(c, (_center_x(c), SCREEN_H // 2 + 40))

# ─────────────────────────────────────────────────────────────────────────────
# 6. ESSENZA — distribuzione punti stile SPECIAL / Fallout
# ─────────────────────────────────────────────────────────────────────────────
def draw_essenza(screen, fonts, attrs: dict, cursor: int):
    """
    attrs = {"Forza": 1, "Agilità": 1, ...}
    cursor = indice attributo selezionato
    """
    screen.fill((5, 5, 15))
    title = fonts["large"].render("E S S E N Z A", True, (255, 220, 50))
    screen.blit(title, (_center_x(title), 30))

    spent   = sum(attrs.values())
    remaining = ESSENZA_POINTS - spent
    rem_col = (100, 220, 100) if remaining > 0 else (220, 100, 100)
    rem_s   = fonts["bold"].render(f"Punti rimanenti: {remaining}", True, rem_col)
    screen.blit(rem_s, (_center_x(rem_s), 68))

    bar_x   = SCREEN_W // 2 - 200
    bar_y0  = 110
    row_h   = 48

    for i, attr in enumerate(ESSENZA_ATTRS):
        val    = attrs[attr]
        active = (i == cursor)
        y      = bar_y0 + i * row_h
        col    = (255, 255, 100) if active else (180, 180, 200)

        # Nome attributo
        name_s = fonts["bold"].render(attr, True, col)
        screen.blit(name_s, (bar_x, y))

        # Barra visuale  ■■■■■□□□□□
        for b in range(ESSENZA_MAX):
            filled = b < val
            bc     = (255, 200, 50) if (active and filled) else ((180, 140, 30) if filled else (50, 50, 60))
            pygame.draw.rect(screen, bc, (bar_x + 160 + b * 22, y + 2, 18, 14))

        # Valore numerico
        val_s = fonts["bold"].render(str(val), True, col)
        screen.blit(val_s, (bar_x + 160 + ESSENZA_MAX * 22 + 10, y))

        # Frecce se selezionato
        if active:
            screen.blit(fonts["bold"].render("◄", True, (200, 200, 50)), (bar_x + 148, y))
            screen.blit(fonts["bold"].render("►", True, (200, 200, 50)), (bar_x + 160 + ESSENZA_MAX * 22 + 28, y))

    # Controlli in basso
    hints = [
        "SU/GIU  — seleziona attributo",
        "SINISTRA/DESTRA  — modifica valore",
        "INVIO  — conferma scelte",
    ]
    for j, h in enumerate(hints):
        hs = fonts["small"].render(h, True, (90, 120, 90))
        screen.blit(hs, (_center_x(hs), SCREEN_H - 70 + j * 20))

# ─────────────────────────────────────────────────────────────────────────────
# 7. ESSENZA CONFIRM — "Sei sicuro delle tue scelte?"
# ─────────────────────────────────────────────────────────────────────────────
def draw_essenza_confirm(screen, fonts, selected_yes: bool):
    screen.fill((5, 5, 15))
    q = fonts["large"].render("Sei sicuro delle tue scelte?", True, (220, 200, 100))
    screen.blit(q, (_center_x(q), SCREEN_H // 2 - 60))
    sub = fonts["normal"].render("Non potrai cambiarle.", True, (180, 100, 100))
    screen.blit(sub, (_center_x(sub), SCREEN_H // 2 - 20))

    for i, label in enumerate(["  Sì  ", "  No  "]):
        active = (i == 0 and selected_yes) or (i == 1 and not selected_yes)
        col    = (255, 255, 100) if active else (140, 140, 160)
        bg     = (60, 60, 20) if active else (20, 20, 30)
        s      = fonts["bold"].render(label, True, col)
        rx     = SCREEN_W // 2 - 120 + i * 160
        ry     = SCREEN_H // 2 + 30
        pygame.draw.rect(screen, bg, (rx - 4, ry - 4, s.get_width() + 8, s.get_height() + 8), border_radius=4)
        screen.blit(s, (rx, ry))

    hint = fonts["small"].render("SINISTRA/DESTRA per selezionare  |  INVIO per confermare", True, (80, 80, 100))
    screen.blit(hint, (_center_x(hint), SCREEN_H - 50))

# ─────────────────────────────────────────────────────────────────────────────
# 8. PAUSA
# ─────────────────────────────────────────────────────────────────────────────
def draw_pause(screen, fonts, seed: int, draw_overlay_fn):
    lines = [
        (f"World Seed: {seed}", (120, 120, 180)),
        ("S – Salva partita",   (200, 200, 100)),
        ("Q – Esci",            (200, 100, 100)),
        ("ESC – Riprendi",      (100, 200, 100)),
    ]
    draw_overlay_fn("PAUSA", lines, y_start=110)

# ─────────────────────────────────────────────────────────────────────────────
# 9. MORTE
# ─────────────────────────────────────────────────────────────────────────────
def draw_dead(screen, fonts, player, draw_overlay_fn):
    p = player
    lines = [
        (f"{p.name} morto all'età di {p.age}, livello {p.level}.", (255, 100, 100)),
        (f"Causa: {p.death_cause}",     (220, 80, 80)),
        (f"Uccisioni totali: {p.kills}", (180, 80, 80)),
        ("", None),
        ("R – Nuovo personaggio", (100, 220, 100)),
        ("Q – Esci al desktop",   (200, 100, 100)),
    ]
    draw_overlay_fn("SEI MORTO", lines, y_start=100)

# ─────────────────────────────────────────────────────────────────────────────
# Mantenuta per compatibilità col vecchio codice
# ─────────────────────────────────────────────────────────────────────────────
def draw_menu_class(screen, fonts, selected_class: int):
    from core.enums import CharClass, CLASS_DESC
    screen.fill((5, 5, 15))
    title = fonts["large"].render("SCEGLI LA TUA CLASSE", True, (255, 220, 50))
    screen.blit(title, (_center_x(title), 60))
    for i, cls in enumerate(CharClass):
        sel = (i == selected_class)
        col = (255, 255, 0) if sel else (180, 180, 200)
        prefix = ">> " if sel else "   "
        screen.blit(fonts["bold"].render(f"{prefix}{cls.value}", True, col),
                    (SCREEN_W // 2 - 200, 160 + i * 60))
        screen.blit(fonts["small"].render(f"   {CLASS_DESC[cls]}", True, (150, 180, 150)),
                    (SCREEN_W // 2 - 200, 182 + i * 60))
    hint = fonts["normal"].render("SU/GIU per selezionare  INVIO per iniziare", True, (100, 200, 100))
    screen.blit(hint, (_center_x(hint), SCREEN_H - 70))

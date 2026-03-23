# =============================================================================
# ui/overlays.py — Overlay: inventario, mercante, dialogo, quest log.
# =============================================================================

import pygame
from core.constants import SCREEN_W, SCREEN_H, RARITY_COLORS

def _same_item(a, b) -> bool:
    """
    Confronto robusto item equip/slot anche dopo save/load:
    evita dipendenza dall'identità oggetto (is), che cambia con from_dict().
    """
    if a is None or b is None:
        return False
    return (
        a.name == b.name
        and a.item_type == b.item_type
        and a.rarity == b.rarity
        and a.stats == b.stats
        and a.value == b.value
    )


def draw_overlay(screen, fonts, title: str, lines: list, y_start: int = 80):
    """
    Disegna un pannello overlay centrato semitrasparente con titolo e righe.
    Usata da tutti gli altri overlay come funzione base comune.

    lines: lista di tuple (testo, colore) — colore None = riga vuota.
    Ritorna (ox, oy, ow, oh): posizione e dimensioni del pannello.
    """
    ow, oh = 700, 480
    ox = (SCREEN_W - ow) // 2
    oy = (SCREEN_H - oh) // 2

    surf = pygame.Surface((ow, oh), pygame.SRCALPHA)
    surf.fill((10,10,30,235))                                        # sfondo blu notte quasi opaco
    pygame.draw.rect(surf, (80,80,200), (0,0,ow,oh), 2)             # bordo blu
    screen.blit(surf, (ox, oy))

    t = fonts["large"].render(title, True, (255,220,80))
    screen.blit(t, (ox + (ow - t.get_width())//2, oy + 10))         # titolo centrato

    for i, (txt, col) in enumerate(lines):
        if col:
            screen.blit(fonts["normal"].render(txt, True, col), (ox+20, oy+y_start+i*22))

    return ox, oy, ow, oh


def draw_inventory(screen, fonts, player):
    """
    Overlay inventario: lista oggetti con rarità colorata,
    indicatore [E] per equipaggiati, statistica principale e prezzo.
    Cursore ">" sulla riga selezionata.
    """
    p = player; lines = []
    for i, item in enumerate(p.inventory):
        prefix = ">" if i == p.inv_cursor else " "
        is_equipped = any(
            _same_item(item, eq_item)
            for eq_item in (
                p.equipped_weapon, p.equipped_armor, p.equipped_head,
                p.equipped_legs, p.equipped_shield, p.equipped_boots
            )
        )
        eq     = "[E]" if is_equipped else ""
        col    = RARITY_COLORS.get(item.rarity, (200,200,200))
        extra  = ""
        if item.item_type   == "weapon": extra = f"  dmg:{item.stats.get('damage',0)}"
        elif item.item_type == "armor":  extra = f"  def:{item.stats.get('defense',0)}"
        elif item.item_type == "potion": extra = f"  +{item.stats.get('heal',0)}hp"
        lines.append((f"{prefix} {eq}{item.name} ({item.rarity}){extra}  [{item.value}g]", col))
    if not lines:
        lines = [("  Empty inventory — explore to find items!", (150,150,150))]
    lines += [("", None), ("Enter=Use/Equip    I/Esc=Close    D=Drop", (100,200,100))]
    draw_overlay(screen, fonts, "INVENTORY", lines)


def draw_merchant(screen, fonts, player, merchant, shop_cursor, sell_mode=False, sell_cursor=0):
    if merchant is None:
        return
    p      = player
    shop   = merchant.shop if merchant else []
    m_gold = getattr(merchant, "gold", 300)
    SW, SH = screen.get_size()

    # sfondo grigio scuro semitrasparente
    overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
    overlay.fill((20, 22, 20, 230))
    screen.blit(overlay, (0, 0))

    PAD     = 20
    col_w   = SW // 2 - PAD * 2
    left_x  = PAD
    right_x = SW // 2 + PAD
    top_y   = 50
    row_h   = 20
    list_h  = SH - top_y - 80
    vis_rows = list_h // row_h

    # titoli
    screen.blit(fonts["small"].render(f"── {p.name} ──",      True, (160,200,160)), (left_x,  top_y-24))
    screen.blit(fonts["small"].render(f"── {merchant.name} ──", True, (160,200,160)), (right_x, top_y-24))
    pygame.draw.line(screen, (60,80,60), (SW//2, top_y-30), (SW//2, SH-55), 1)

    # lista sinistra — inventario giocatore
    inv   = p.inventory
    start = max(0, sell_cursor - vis_rows + 1)
    for i, item in enumerate(inv[start: start + vis_rows]):
        idx = start + i
        sel = sell_mode and idx == sell_cursor
        iy  = top_y + i * row_h
        if sel:
            pygame.draw.rect(screen, (35,55,35), pygame.Rect(left_x-2, iy, col_w+4, row_h-1))
        col = RARITY_COLORS.get(getattr(item,"rarity","common"), (200,200,200))
        if not sel:
            col = tuple(max(0, c-60) for c in col)
        sell_price = max(1, item.value // 2)
        txt = f"{'>' if sel else ' '} {item.name[:20]:<20} {sell_price:>4}g"
        screen.blit(fonts["small"].render(txt, True, col), (left_x, iy+2))
    if not inv:
        screen.blit(fonts["small"].render("(empty)", True, (70,70,70)), (left_x, top_y))

    # lista destra — inventario mercante
    start2 = max(0, shop_cursor - vis_rows + 1)
    for i, item in enumerate(shop[start2: start2 + vis_rows]):
        idx = start2 + i
        sel = (not sell_mode) and idx == shop_cursor
        iy  = top_y + i * row_h
        if sel:
            pygame.draw.rect(screen, (35,55,35), pygame.Rect(right_x-2, iy, col_w+4, row_h-1))
        col = RARITY_COLORS.get(getattr(item,"rarity","common"), (200,200,200))
        if not sel:
            col = tuple(max(0, c-60) for c in col)
        txt = f"{'>' if sel else ' '} {item.name[:20]:<20} {item.value:>4}g"
        screen.blit(fonts["small"].render(txt, True, col), (right_x, iy+2))
    if not shop:
        screen.blit(fonts["small"].render("(empty)", True, (70,70,70)), (right_x, top_y))

    # barra fondo — oro e modalità
    pygame.draw.rect(screen, (15,18,15), pygame.Rect(0, SH-52, SW, 52))
    pygame.draw.line(screen, (60,80,60), (0, SH-52), (SW, SH-52), 1)
    screen.blit(fonts["small"].render(f"Gold: {p.gold}g",  True, (200,180,80)), (left_x, SH-44))
    mode_col  = (100,200,100) if sell_mode else (100,150,200)
    mode_surf = fonts["small"].render("[ SELL ]" if sell_mode else "[ BUY ]", True, mode_col)
    screen.blit(mode_surf, (SW//2 - mode_surf.get_width()//2, SH-44))
    gold_m    = fonts["small"].render(f"Gold: {m_gold}g", True, (200,180,80))
    screen.blit(gold_m, (SW - gold_m.get_width() - left_x, SH-44))
    hint = fonts["small"].render("TAB modo  |  W/S naviga  |  INVIO conferma  |  ESC esci", True, (80,100,80))
    screen.blit(hint, (SW//2 - hint.get_width()//2, SH-24))



def draw_dialog(screen, fonts, player, entity, dialog_text=None):
    """
    Pannello dialogo in basso schermo (~160px). Nome NPC + testo + quest opzionale.
    """
    if not entity: return
    e = entity
    SW, SH = screen.get_size()
    PH = 162
    PW = SW - 40
    px, py = 20, SH - PH - 10

    # Sfondo semitrasparente
    surf = pygame.Surface((PW, PH), pygame.SRCALPHA)
    surf.fill((10, 8, 28, 225))
    pygame.draw.rect(surf, (90, 70, 190), (0, 0, PW, PH), 2)
    screen.blit(surf, (px, py))

    # Barra nome NPC
    name_surf = fonts["normal"].render(e.name, True, (255, 220, 80))
    nbg = pygame.Surface((name_surf.get_width() + 22, 24), pygame.SRCALPHA)
    nbg.fill((55, 35, 115, 210))
    screen.blit(nbg, (px + 10, py + 8))
    screen.blit(name_surf, (px + 21, py + 10))

    # Testo dialogo (puo' essere sovrascritto dal chiamante per dialoghi contestuali)
    text = dialog_text if dialog_text is not None else e.dialogue
    screen.blit(fonts["normal"].render(f'"{text}"', True, (210, 210, 210)),
                (px + 20, py + 42))

    # Quest se disponibile
    row = py + 72
    if (e.has_quest and e.quest and not e.quest.completed
            and e.quest.qid not in player.completed_quests):
        screen.blit(fonts["small"].render(f"Quest: {e.quest.title}", True, (255, 200, 50)),
                    (px + 20, row)); row += 20
        screen.blit(fonts["small"].render(f"  {e.quest.desc}", True, (160, 160, 160)),
                    (px + 20, row)); row += 18
        screen.blit(fonts["small"].render(
            f"  Reward: {e.quest.reward_gold}g  +{e.quest.reward_xp}xp",
            True, (120, 200, 120)), (px + 20, row))

    # Hint chiusura
    hint = fonts["small"].render("ESC – chiudi", True, (100, 155, 100))
    screen.blit(hint, (px + PW - hint.get_width() - 14, py + PH - 20))


def draw_quest_log(screen, fonts, player):
    """
    Overlay diario quest: progresso di ogni missione attiva
    e contatore quest completate.
    """
    p = player; lines = []
    if not p.active_quests:
        lines = [("  No active quests. Talk to NPCs!", (180,180,180))]
    else:
        for q in p.active_quests:
            col = (100,255,100) if q.completed else (255,200,50)
            lines.append((f"[{q.progress_str}]  {q.title}", col))
            lines.append((f"   {q.desc}",                   (160,160,160)))
            lines.append((f"   Reward: {q.reward_gold}g +{q.reward_xp}xp", (120,200,120)))
            lines.append(("", None))
    lines += [(f"Completed: {len(p.completed_quests)}", (100,200,100)), ("", None),
              ("Q/Esc – Close", (100,180,100))]
    draw_overlay(screen, fonts, "QUEST LOG", lines)
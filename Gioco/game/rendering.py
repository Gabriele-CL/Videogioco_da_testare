from combat.combat_ui import draw_combat
from core.constants import *
from core.enums import GameState
from ui.hud import draw_equip_panel, draw_hud, draw_inventory_panel, draw_minimap, draw_night_overlay
from ui.menus import (
    draw_dead,
    draw_essenza,
    draw_essenza_confirm,
    draw_intro_screen,
    draw_main_menu,
    draw_menu_name,
    draw_options,
    draw_pause,
    draw_splash,
)
from ui.overlays import draw_dialog, draw_inventory, draw_merchant, draw_overlay
from ui.journal_ui import draw_journal
from ui.world_map_ui import draw_world_map
from world.buildings import draw_building_labels

from .bootstrap import pygame
from .helpers import ITEM_SYMBOL

PANEL_X = VIEW_COLS * TILE_W
PANEL_W = SCREEN_W - PANEL_X


class GameRenderingMixin:
    def _draw_world(self):
        screen = self.screen
        p = self.player
        half_c = VIEW_COLS // 2
        half_r = VIEW_ROWS // 2
        for row in range(VIEW_ROWS):
            for col in range(VIEW_COLS):
                wx = p.x - half_c + col
                wy = p.y - half_r + row
                t = self.world.get_tile(wx, wy)
                wc = self.world.get_wall_char(wx, wy)
                ch = wc if wc else TILE_CHAR.get(t, "?")
                fg = TILE_COLOR.get(t, (200, 200, 200))
                bg = TILE_BG.get(t, (0, 0, 0))
                px_ = col * TILE_W
                py_ = row * TILE_H
                pygame.draw.rect(screen, bg, (px_, py_, TILE_W, TILE_H))
                screen.blit(self.fonts["normal"].render(ch, True, fg), (px_, py_))
        for ts in self.tombstones:
            c_ = ts["x"] - p.x + half_c
            r_ = ts["y"] - p.y + half_r
            if 0 <= c_ < VIEW_COLS and 0 <= r_ < VIEW_ROWS:
                screen.blit(self.fonts["bold"].render("R", True, (160, 0, 200)), (c_ * TILE_W, r_ * TILE_H))
        for item in self.items_on_ground:
            c_ = item.x - p.x + half_c
            r_ = item.y - p.y + half_r
            if 0 <= c_ < VIEW_COLS and 0 <= r_ < VIEW_ROWS:
                screen.blit(
                    self.fonts["bold"].render(ITEM_SYMBOL, True, RARITY_COLORS.get(item.rarity, (255, 255, 255))),
                    (c_ * TILE_W, r_ * TILE_H),
                )
        for e in self.entities:
            c_ = e.x - p.x + half_c
            r_ = e.y - p.y + half_r
            if 0 <= c_ < VIEW_COLS and 0 <= r_ < VIEW_ROWS:
                screen.blit(self.fonts["bold"].render(e.symbol, True, e.color), (c_ * TILE_W, r_ * TILE_H))
        screen.blit(self.fonts["bold"].render("@", True, (255, 255, 255)), (half_c * TILE_W, half_r * TILE_H))
        dmap = {(0, -1): "^", (0, 1): "v", (1, 0): ">", (-1, 0): "<"}
        dc = dmap.get((getattr(self, "last_dx", 0), getattr(self, "last_dy", 1)), "v")
        ax = (half_c + getattr(self, "last_dx", 0)) * TILE_W
        ay = (half_r + getattr(self, "last_dy", 1)) * TILE_H
        arrow = self.fonts["small"].render(dc, True, (255, 255, 140))
        screen.blit(arrow, (ax + (TILE_W - arrow.get_width()) // 2, ay))
        if self.magic_aura_timer > 0 and self.player:
            px_s = half_c * TILE_W + TILE_W // 2
            py_s = half_r * TILE_H + TILE_H // 2
            aura_col = (100, 200, 255) if self.magic_aura_has_power else (180, 180, 180)
            alpha = int(180 * min(1.0, self.magic_aura_timer / 0.8))
            radius = int(TILE_W * 2.5)
            aura_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*aura_col, alpha), (radius, radius), radius)
            pygame.draw.circle(aura_surf, (*aura_col, min(255, alpha + 60)), (radius, radius), radius // 2)
            screen.blit(aura_surf, (px_s - radius, py_s - radius))
        for ft in self.floating_texts:
            ft.draw(screen, self.fonts["small"])
        draw_night_overlay(self.screen, self.get_time_of_day())
        if self.flee_immunity > 0:
            s = self.fonts["small"].render(f"[ IMMUN. FUGA: {self.flee_immunity:.1f}s ]", True, (100, 220, 255))
            self.screen.blit(s, s.get_rect(centerx=(VIEW_COLS // 2) * TILE_W, y=4))

    def render(self):
        self.screen.fill((5, 5, 15))
        s = self.state
        if s == GameState.SPLASH:
            draw_splash(self.screen, self.fonts, self.tick)
        elif s == GameState.MAIN_MENU:
            draw_main_menu(self.screen, self.fonts, self.main_menu_cursor, self.has_save)
        elif s == GameState.OPTIONS:
            draw_options(self.screen, self.fonts)
        elif s == GameState.MENU_NAME:
            draw_menu_name(self.screen, self.fonts, self.name_input)
        elif s in (GameState.INTRO_WELCOME, GameState.INTRO_ADVENTURE, GameState.INTRO_DESTINY):
            draw_intro_screen(self.screen, self.fonts, self._intro_message(), self.tick)
        elif s == GameState.ESSENZA:
            draw_essenza(self.screen, self.fonts, self.essenza_attrs, self.essenza_cursor)
        elif s == GameState.ESSENZA_CONFIRM:
            draw_essenza_confirm(self.screen, self.fonts, self.essenza_yes)
        elif s in (GameState.PLAYING, GameState.INVENTORY, GameState.MAP, GameState.MERCHANT, GameState.DIALOG, GameState.PAUSE, GameState.MAGIC_ASK, GameState.JOURNAL):
            if self.player:
                if s == GameState.MAP:
                    draw_world_map(self.screen, self.fonts, self.world, self.player)
                    return pygame.display.flip()
                pygame.draw.rect(self.screen, (10, 12, 10), pygame.Rect(PANEL_X, 0, PANEL_W, VIEW_ROWS * TILE_H))
                self._draw_world()
                try:
                    draw_hud(self.screen, self.fonts, self.player, self.world.get_biome_at(self.player.x, self.player.y), self.time_str())
                except Exception:
                    try:
                        draw_hud(self.screen, self.fonts, self.player, self.time_str(), self.messages)
                    except Exception:
                        pass
                if s == GameState.INVENTORY:
                    try:
                        draw_inventory_panel(self.screen, self.fonts, self.player, self.inv_cursor)
                    except Exception:
                        draw_inventory(self.screen, self.fonts, self.player, self.inv_cursor)
                else:
                    try:
                        draw_minimap(self.screen, self.fonts, self.minimap_surf, self.world, self.player)
                    except Exception:
                        pass
                    try:
                        draw_equip_panel(self.screen, self.fonts, self.player)
                    except Exception:
                        pass
                ov = lambda t, l, **kw: draw_overlay(self.screen, self.fonts, t, l, **kw)
                if s == GameState.PAUSE:
                    draw_pause(self.screen, self.fonts, self.seed, ov)
                    if self.save_flash > 0:
                        flash_surf = self.fonts["bold"].render("✔ Partita salvata!", True, (80, 255, 120))
                        alpha = min(255, int(255 * (self.save_flash / 2.0)))
                        flash_surf.set_alpha(alpha)
                        ow, oh = 700, 480
                        ox = (SCREEN_W - ow) // 2
                        oy = (SCREEN_H - oh) // 2
                        fx = ox + ow - flash_surf.get_width() - 12
                        fy = oy + oh - flash_surf.get_height() - 12
                        self.screen.blit(flash_surf, (fx, fy))
                elif s == GameState.MERCHANT and self.merchant_ent:
                    draw_merchant(self.screen, self.fonts, self.player, self.merchant_ent, self.shop_cursor, self.sell_mode, self.sell_cursor)
                elif s == GameState.DIALOG and self.dialog_ent:
                    try:
                        draw_dialog(self.screen, self.fonts, self.player, self.dialog_ent, self.dialog_text_override)
                    except Exception:
                        draw_dialog(self.screen, self.fonts, self.player, self.dialog_ent)
                elif s == GameState.MAGIC_ASK and self.dialog_ent:
                    choice = "SI" if self.magic_choice_yes else "NO"
                    ov("MAESTRO DI MAGIA", [("Vuoi procedere con il test magico?", (220, 220, 220)), ("", None), (f"Scelta: [{choice}]   (LEFT/RIGHT cambia)", (255, 220, 80)), ("INVIO conferma   ESC annulla", (120, 200, 120))])
                elif s == GameState.JOURNAL and getattr(self, "journal", None):
                    draw_journal(self.screen, self.fonts, self.journal, self.journal_cursor, self.journal_tab)
        elif s == GameState.DEAD:
            if self.player:
                ov = lambda t, l, **kw: draw_overlay(self.screen, self.fonts, t, l, **kw)
                draw_dead(self.screen, self.fonts, self.player, ov)
        elif s == GameState.COMBAT:
            if self.combat_state:
                draw_combat(self.screen, self.fonts, self.combat_state)
        pygame.display.flip()

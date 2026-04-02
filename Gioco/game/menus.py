import os

from core.constants import ESSENZA_ATTRS, ESSENZA_MAX, ESSENZA_MIN, ESSENZA_POINTS
from core.enums import GameState

from .bootstrap import pygame


class GameMenuMixin:
    def _handle_splash(self, event):
        if event.type == pygame.KEYDOWN:
            self.has_save = os.path.exists("savegame.json")
            self.state = GameState.MAIN_MENU

    def _handle_main_menu(self, event):
        self.has_save = os.path.exists("savegame.json")
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        num_items = 3 if self.has_save else 2
        if k == pygame.K_UP:
            self.main_menu_cursor = (self.main_menu_cursor - 1) % num_items
        elif k == pygame.K_DOWN:
            self.main_menu_cursor = (self.main_menu_cursor + 1) % num_items
        elif k == pygame.K_RETURN:
            if self.main_menu_cursor == 0:
                self.name_input = ""
                self.state = GameState.MENU_NAME
            elif self.main_menu_cursor == 1:
                self.has_save = os.path.exists("savegame.json")
                if self.has_save:
                    self.load_game()
                else:
                    self.log("Nessuna partita salvata!")
            elif self.main_menu_cursor == 2:
                self.state = GameState.OPTIONS

    def _handle_options(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
            self.state = GameState.MAIN_MENU

    def _handle_menu_name(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_RETURN and self.name_input.strip():
            self.state = GameState.INTRO_WELCOME
        elif event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
        elif len(self.name_input) < 20 and event.unicode.isprintable():
            self.name_input += event.unicode

    def _handle_intro(self, event):
        if event.type == pygame.KEYDOWN:
            self.state = self.INTRO_NEXT[self.state]
            if self.state == GameState.ESSENZA:
                self.essenza_attrs = {a: ESSENZA_MIN for a in ESSENZA_ATTRS}
                self.essenza_cursor = 0

    def _intro_message(self) -> str:
        name = self.name_input.strip() or "Eroe"
        return {
            GameState.INTRO_WELCOME: f"Benvenuto, {name}",
            GameState.INTRO_ADVENTURE: "La tua avventura sta per avere inizio",
            GameState.INTRO_DESTINY: "Il destino è nelle tue mani, fa la scelta giusta",
        }.get(self.state, "")

    def _essenza_spent(self) -> int:
        return sum(self.essenza_attrs.values())

    def _handle_essenza(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        attr = ESSENZA_ATTRS[self.essenza_cursor]
        val = self.essenza_attrs[attr]
        if k == pygame.K_UP:
            self.essenza_cursor = (self.essenza_cursor - 1) % len(ESSENZA_ATTRS)
        elif k == pygame.K_DOWN:
            self.essenza_cursor = (self.essenza_cursor + 1) % len(ESSENZA_ATTRS)
        elif k == pygame.K_RIGHT:
            if val < ESSENZA_MAX and self._essenza_spent() < ESSENZA_POINTS:
                self.essenza_attrs[attr] += 1
        elif k == pygame.K_LEFT:
            if val > ESSENZA_MIN:
                self.essenza_attrs[attr] -= 1
        elif k == pygame.K_RETURN:
            if self._essenza_spent() == ESSENZA_POINTS:
                self.essenza_yes = True
                self.state = GameState.ESSENZA_CONFIRM

    def _handle_essenza_confirm(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.essenza_yes = not self.essenza_yes
        elif event.key == pygame.K_RETURN:
            if self.essenza_yes:
                self.start_new_game()
            else:
                self.state = GameState.ESSENZA

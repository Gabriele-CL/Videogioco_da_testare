from combat.combat import CombatPhase
from core.enums import GameState

from .bootstrap import pygame
from ui.journal_ui import CATEGORIES


class GameEventMixin:
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif self.state == GameState.SPLASH:
                self._handle_splash(event)
            elif self.state == GameState.MAIN_MENU:
                self._handle_main_menu(event)
            elif self.state == GameState.OPTIONS:
                self._handle_options(event)
            elif self.state == GameState.MENU_NAME:
                self._handle_menu_name(event)
            elif self.state in (GameState.INTRO_WELCOME, GameState.INTRO_ADVENTURE, GameState.INTRO_DESTINY):
                self._handle_intro(event)
            elif self.state == GameState.ESSENZA:
                self._handle_essenza(event)
            elif self.state == GameState.ESSENZA_CONFIRM:
                self._handle_essenza_confirm(event)
            elif self.state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k == pygame.K_e:
                        self.interact()
                    elif k == pygame.K_i:
                        self.state = GameState.INVENTORY
                        self.inv_cursor = 0
                    elif k == pygame.K_m:
                        self.state = GameState.MAP
                    elif k == pygame.K_j or str(event.unicode).lower() == "j":
                        if not getattr(self, "journal", None):
                            from core.journal import Journal  # lazy import to avoid circular
                            self.journal = Journal()
                        self.journal_cursor = 0
                        self.state = GameState.JOURNAL
                    elif k == pygame.K_ESCAPE:
                        self.state = GameState.PAUSE
            elif self.state == GameState.PAUSE:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s or event.unicode in ("s", "S"):
                        if self.player:
                            self.save_game()
                    elif event.key == pygame.K_q:
                        self.running = False
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.PLAYING
            elif self.state == GameState.INVENTORY:
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    inv = self.player.inventory
                    if k == pygame.K_ESCAPE or k == pygame.K_i:
                        self.state = GameState.PLAYING
                    elif k in (pygame.K_UP, pygame.K_w):
                        self.inv_cursor = max(0, self.inv_cursor - 1)
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        self.inv_cursor = min(max(0, len(inv) - 1), self.inv_cursor + 1)
                    elif k == pygame.K_RETURN and inv:
                        self.use_item(inv[min(self.inv_cursor, len(inv) - 1)])
                        self.inv_cursor = min(self.inv_cursor, max(0, len(inv) - 1))
                    elif k == pygame.K_d and inv:
                        item = inv[min(self.inv_cursor, len(inv) - 1)]
                        item.x, item.y = self.player.x, self.player.y
                        self.items_on_ground.append(item)
                        inv.remove(item)
                        self.log(f"Buttato: {item.name}")
                        self.inv_cursor = min(self.inv_cursor, max(0, len(inv) - 1))
            elif self.state == GameState.MAP:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_m):
                        self.state = GameState.PLAYING
            elif self.state == GameState.MERCHANT:
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    shop = self.merchant_ent.shop if self.merchant_ent else []
                    inv = self.player.inventory
                    if k == pygame.K_TAB:
                        self.sell_mode = not self.sell_mode
                    elif k in (pygame.K_UP, pygame.K_w):
                        if self.sell_mode:
                            self.sell_cursor = max(0, self.sell_cursor - 1)
                        else:
                            self.shop_cursor = max(0, self.shop_cursor - 1)
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        if self.sell_mode:
                            self.sell_cursor = min(max(0, len(inv) - 1), self.sell_cursor + 1)
                        else:
                            self.shop_cursor = min(max(0, len(shop) - 1), self.shop_cursor + 1)
                    elif k == pygame.K_RETURN:
                        if self.sell_mode and inv:
                            item = inv[min(self.sell_cursor, len(inv) - 1)]
                            price = max(1, item.value // 2)
                            if self.merchant_ent.gold >= price:
                                self.player.gold += price
                                self.merchant_ent.gold -= price
                                self.merchant_ent.shop.append(item)
                                inv.remove(item)
                                self.log(f"Venduto {item.name} per {price}g")
                                self.sell_cursor = min(self.sell_cursor, max(0, len(inv) - 1))
                            else:
                                self.log("Il mercante non ha abbastanza oro!")
                        elif not self.sell_mode and shop:
                            item = shop[min(self.shop_cursor, len(shop) - 1)]
                            if self.player.gold >= item.value:
                                self.player.gold -= item.value
                                self.merchant_ent.gold += item.value
                                self.player.inventory.append(item)
                                shop.remove(item)
                                self.log(f"Comprato {item.name} per {item.value}g")
                                self.shop_cursor = min(self.shop_cursor, max(0, len(shop) - 1))
                            else:
                                self.log("Oro insufficiente!")
                    elif k == pygame.K_ESCAPE:
                        self.sell_mode = False
                        self.state = GameState.PLAYING
            elif self.state == GameState.DIALOG:
                if event.type == pygame.KEYDOWN:
                    if getattr(self, "merchant_pending", False):
                        self.merchant_pending = False
                        self.state = GameState.MERCHANT
                    elif getattr(self, "magic_pending_test", False):
                        self.magic_pending_test = False
                        self.magic_choice_yes = True
                        self.state = GameState.MAGIC_ASK
                    else:
                        self.dialog_text_override = None
                        self.state = GameState.PLAYING
            elif self.state == GameState.MAGIC_ASK:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        self.magic_choice_yes = not self.magic_choice_yes
                    elif event.key == pygame.K_ESCAPE:
                        self.dialog_text_override = None
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_RETURN:
                        if self.magic_choice_yes and self.player and self.dialog_ent:
                            p = self.player
                            p.magic_revealed = True
                            self.magic_aura_timer = 2.5
                            self.magic_aura_has_power = getattr(p, "magic_factor", 0) == 1
                            if self.magic_aura_has_power:
                                self.dialog_text_override = "C'e' della magia in te!"
                            else:
                                self.dialog_text_override = "Mi spiace... non c'e' potere in te."
                            self.state = GameState.DIALOG
                        else:
                            self.dialog_text_override = "Va bene. Torna quando te la sentirai."
                            self.state = GameState.DIALOG
            elif self.state == GameState.JOURNAL:
                if event.type == pygame.KEYDOWN and getattr(self, "journal", None):
                    k = event.key
                    uni = str(event.unicode).lower()
                    if k in (pygame.K_ESCAPE, pygame.K_j) or uni == "j":
                        self.state = GameState.PLAYING
                    elif k in (pygame.K_LEFT, pygame.K_a):
                        self.journal_tab = (self.journal_tab - 1) % len(CATEGORIES)
                        self.journal_cursor = 0
                    elif k in (pygame.K_RIGHT, pygame.K_d):
                        self.journal_tab = (self.journal_tab + 1) % len(CATEGORIES)
                        self.journal_cursor = 0
                    elif k in (pygame.K_UP, pygame.K_w):
                        self.journal_cursor = max(0, self.journal_cursor - 1)
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        cat = CATEGORIES[self.journal_tab]
                        entries = self.journal.entries if cat == "all" else self.journal.get_by_category(cat)
                        max_idx = max(0, len(entries) - 1)
                        self.journal_cursor = min(max_idx, self.journal_cursor + 1)
            elif self.state == GameState.DEAD:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.__init__()
                        self.has_save = False
                    elif event.key == pygame.K_q:
                        self.running = False
            elif self.state == GameState.COMBAT:
                if event.type == pygame.KEYDOWN and self.combat_state:
                    self.combat_state.handle_key(event.key)
                    cs = self.combat_state
                    if cs.phase == CombatPhase.OUTRO and cs.outro_timer >= 0.8:
                        self._end_combat()
                    elif cs.phase == CombatPhase.DEFEAT:
                        self.handle_death()
                    elif cs.phase == CombatPhase.FLED:
                        self._end_combat()

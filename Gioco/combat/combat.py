# =============================================================================
# combat/combat.py — Logica del sistema di combattimento a turni
# =============================================================================
import random
from enum import Enum, auto
from typing import Optional, List


class CombatPhase(Enum):
    INTRO       = auto()
    PLAYER_TURN = auto()
    ENEMY_TURN  = auto()
    VICTORY     = auto()
    DEFEAT      = auto()
    FLED        = auto()
    OUTRO       = auto()
    FLEE_FAILED = auto()


class MenuFocus(Enum):
    BUTTONS = auto()
    SUBMENU = auto()
    TARGET  = auto()


class ActionButton(Enum):
    ATTACK  = 0
    ABILITY = 1
    GUARD   = 2
    ITEMS   = 3
    FLEE    = 4


CLASS_ABILITIES = {
    "Warrior": [{"name": "Colpo Possente",  "damage_mult": 2.0, "desc": "Un attacco devastante che raddoppia il danno."}],
    "Rogue":   [{"name": "Attacco Furtivo", "damage_mult": 1.8, "desc": "Colpo rapido con alta probabilità di critico."}],
    "Mage":    [{"name": "Palla di Fuoco",  "damage_mult": 2.5, "desc": "Incantesimo elementale ad alto danno."}],
    "Ranger":  [{"name": "Freccia Precisa", "damage_mult": 1.6, "desc": "Tiro mirato che ignora parte della difesa."}],
    "Paladin": [{"name": "Luce Sacra",      "damage_mult": 1.5, "desc": "Attacco sacro che cura 5 HP al lanciatore."}],
}


class CombatState:
    def __init__(self, player, enemy, biome: str = "Grassland"):
        self.player = player
        self.enemy  = enemy
        self.biome  = biome

        self.phase: CombatPhase = CombatPhase.INTRO
        self.intro_timer: float = 0.0
        self.outro_timer: float = 0.0

        player_roll = random.randint(1, 20)
        enemy_roll  = random.randint(1, 20)
        self.player_first: bool = (player_roll >= enemy_roll)

        self.focus: MenuFocus        = MenuFocus.BUTTONS
        self.selected_button: int    = 0
        self.submenu_cursor: int     = 0
        self.flee_cursor: int        = 0
        self.info_popup: Optional[dict] = None

        self.guard_active: bool = False

        self.log: List[str]     = []
        self.timed_log: List[dict] = []
        self.floats: List[dict] = []

        self.loot_item  = None
        self.loot_shown = False

        self.xp_gained:   int = 0
        self.gold_gained: int = 0

        self._start()

    def _start(self):
        if self.player_first:
            self.add_log(f"Inizia {self.player.name}!")
        else:
            self.add_log(f"Inizia {self.enemy.name}!")
        self.phase = CombatPhase.INTRO

    def _log(self, msg: str):
        """Aggiunge un messaggio temporizzato (2s) nel pannello superiore."""
        self.add_log(msg)

    def add_log(self, text, color=None):
        """Aggiunge un messaggio che dura 2 secondi nel pannello superiore."""
        self.timed_log.append({
            "text":  text,
            "timer": 2.0,
            "color": color or (160, 150, 180)
        })
        # mantieni max 4 messaggi visibili contemporaneamente
        if len(self.timed_log) > 4:
            self.timed_log.pop(0)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def get_abilities(self) -> list:
        return CLASS_ABILITIES.get(self.player.char_class.value, [])

    def get_usable_items(self) -> list:
        return [i for i in self.player.inventory if i.item_type in ("potion", "weapon")]

    def _add_float(self, text: str, side: str, color=(255, 240, 80)):
        self.floats.append({"text": text, "side": side, "timer": 1.2, "color": color})

    # ------------------------------------------------------------------
    # Update — chiamato ogni frame
    # ------------------------------------------------------------------
    def update(self, dt: float):
        # aggiorna floating texts
        for f in self.floats:
            f["timer"] -= dt
        self.floats = [f for f in self.floats if f["timer"] > 0]

        # aggiorna timer messaggi log
        for m in self.timed_log:
            m["timer"] -= dt
        self.timed_log = [m for m in self.timed_log if m["timer"] > 0]

        if self.phase == CombatPhase.INTRO:
            self.intro_timer += dt
            if self.intro_timer >= 0.8:
                if self.player_first:
                    self.phase = CombatPhase.PLAYER_TURN
                else:
                    self._enemy_attack()
                    self._check_end()
                    if self.phase not in (CombatPhase.DEFEAT, CombatPhase.VICTORY):
                        self.phase = CombatPhase.PLAYER_TURN

        elif self.phase == CombatPhase.OUTRO:
            self.outro_timer += dt

    # ------------------------------------------------------------------
    # Input dal giocatore
    # ------------------------------------------------------------------
    def handle_key(self, key):
        import pygame

        if self.phase == CombatPhase.FLEE_FAILED:
            if key == pygame.K_RETURN:
                self._enemy_attack()
                self._check_end()
                if self.phase not in (CombatPhase.DEFEAT, CombatPhase.VICTORY):
                    self.phase = CombatPhase.PLAYER_TURN
            return

        if self.phase == CombatPhase.VICTORY:
            if key == pygame.K_RETURN:
                self.phase = CombatPhase.OUTRO
            return

        if self.phase != CombatPhase.PLAYER_TURN:
            return

        if self.info_popup is not None:
            if key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
                self.info_popup = None
            return

        if self.focus == MenuFocus.BUTTONS:
            self._handle_buttons(key)
        elif self.focus == MenuFocus.SUBMENU:
            self._handle_submenu(key)
        elif self.focus == MenuFocus.TARGET:
            self._handle_target(key)

    # ------------------------------------------------------------------
    def _handle_buttons(self, key):
        import pygame
        n = len(ActionButton)
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_button = max(0, self.selected_button - 1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_button = min(n - 1, self.selected_button + 1)
        elif key == pygame.K_RETURN:
            btn = ActionButton(self.selected_button)
            if btn == ActionButton.GUARD:
                self._do_guard()
            else:
                self.focus = MenuFocus.SUBMENU
                self.submenu_cursor = 0

    def _handle_submenu(self, key):
        import pygame
        btn = ActionButton(self.selected_button)

        if key == pygame.K_BACKSPACE:
            self.focus = MenuFocus.BUTTONS
            return

        if btn == ActionButton.FLEE:
            if key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT):
                self.flee_cursor = 0
            elif key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT):
                self.flee_cursor = 1
            elif key == pygame.K_RETURN:
                if self.flee_cursor == 0:
                    self._attempt_flee()
                else:
                    self.focus = MenuFocus.BUTTONS
            return

        if btn == ActionButton.ATTACK:
            options = ["Mani nude"]
            if self.player.equipped_weapon:
                options.append(self.player.equipped_weapon.name)
            n = len(options)
        elif btn == ActionButton.ABILITY:
            n = len(self.get_abilities())
        elif btn == ActionButton.ITEMS:
            n = len(self.get_usable_items())
        else:
            n = 0

        if n == 0:
            return

        if key in (pygame.K_UP, pygame.K_w):
            self.submenu_cursor = max(0, self.submenu_cursor - 1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.submenu_cursor = min(n - 1, self.submenu_cursor + 1)
        elif key == pygame.K_i:
            if btn == ActionButton.ABILITY:
                abilities = self.get_abilities()
                if abilities:
                    self.info_popup = abilities[self.submenu_cursor]
            elif btn == ActionButton.ITEMS:
                items = self.get_usable_items()
                if items:
                    item = items[self.submenu_cursor]
                    self.info_popup = {"name": item.name, "desc": item.description}
        elif key == pygame.K_RETURN:
            self.focus = MenuFocus.TARGET

    def _handle_target(self, key):
        import pygame
        if key == pygame.K_BACKSPACE:
            self.focus = MenuFocus.SUBMENU
        elif key == pygame.K_RETURN:
            self._execute_action()

    # ------------------------------------------------------------------
    # Azioni
    # ------------------------------------------------------------------
    def _execute_action(self):
        btn = ActionButton(self.selected_button)
        p   = self.player
        e   = self.enemy

        if btn == ActionButton.ATTACK:
            options = ["Mani nude"]
            if p.equipped_weapon:
                options.append(p.equipped_weapon.name)
            choice = options[min(self.submenu_cursor, len(options) - 1)]
            if choice == "Mani nude":
                dmg = max(1, int(3 * p.dmg_mult))
            else:
                dmg = p.attack_damage_with_crit()
            e.health -= dmg
            self._add_float(f"-{dmg}", "enemy")
            self.add_log(f"{p.name} attacca per {dmg} danni!", (255, 200, 100))

        elif btn == ActionButton.ABILITY:
            abilities = self.get_abilities()
            if abilities:
                ab  = abilities[self.submenu_cursor]
                dmg = int(p.attack_damage() * ab["damage_mult"])
                if ab["name"] == "Luce Sacra":
                    p.health = min(p.max_health, p.health + 5)
                    self.add_log(f"{p.name} recupera 5 HP!", (80, 255, 120))
                e.health -= dmg
                self._add_float(f"-{dmg}", "enemy")
                self.add_log(f'{p.name} usa {ab["name"]} per {dmg} danni!', (200, 170, 255))

        elif btn == ActionButton.ITEMS:
            items = self.get_usable_items()
            if items:
                item = items[self.submenu_cursor]
                if item.item_type == "potion":
                    heal = item.stats.get("heal", 0)
                    p.health = min(p.max_health, p.health + heal)
                    p.inventory.remove(item)
                    self._add_float(f"+{heal} HP", "player", (80, 255, 120))
                    self.add_log(f"{p.name} usa {item.name}: +{heal} HP", (80, 255, 120))
                elif item.item_type == "weapon":
                    dmg = item.stats.get("damage", 5)
                    e.health -= dmg
                    self._add_float(f"-{dmg}", "enemy")
                    self.add_log(f"{p.name} usa {item.name} per {dmg} danni!", (255, 200, 100))

        self.guard_active   = False
        self.focus          = MenuFocus.BUTTONS
        self.submenu_cursor = 0

        self._check_end()
        if self.phase == CombatPhase.PLAYER_TURN:
            self._enemy_turn()

    def _do_guard(self):
        self.guard_active = True
        self.add_log(f"{self.player.name} si mette in guardia!", (150, 220, 255))
        self._enemy_turn()

    def _attempt_flee(self):
        p_roll = random.randint(1, 36)
        e_roll = random.randint(1, 36)
        if p_roll > e_roll:
            self.add_log("Fuga riuscita!", (100, 220, 130))
            self.phase = CombatPhase.FLED
        else:
            self.add_log("Fuga fallita!", (220, 80, 80))
            self.phase = CombatPhase.FLEE_FAILED
            self.focus  = MenuFocus.BUTTONS

    def _enemy_turn(self):
        self.phase = CombatPhase.ENEMY_TURN
        self._enemy_attack()
        self._check_end()
        if self.phase == CombatPhase.ENEMY_TURN:
            self.phase = CombatPhase.PLAYER_TURN

    def _enemy_attack(self):
        p         = self.player
        e         = self.enemy
        def_bonus = p.defense() + (3 if self.guard_active else 0)
        dmg       = max(0, e.damage - def_bonus)
        p.health -= dmg
        self._add_float(f"-{dmg}", "player", (255, 80, 80))
        self.add_log(f"{e.name} attacca {p.name} per {dmg} danni!", (255, 100, 100))
        self.guard_active = False

    def _check_end(self):
        import random as _r
        from items.item import ITEM_GEN
        e = self.enemy
        p = self.player

        if e.health <= 0:
            e.health  = 0
            e.alive   = False
            xp        = {"Wolf": 15, "Goblin": 20, "Ghost": 30}.get(e.name, 10)
            self.xp_gained   = xp
            self.gold_gained = _r.randint(0, 10)
            if _r.random() < 0.4:
                self.loot_item = ITEM_GEN.generate_item()
            self.add_log(f"{e.name} sconfitto! +{xp} XP", (100, 220, 130))
            self.phase = CombatPhase.VICTORY
            return

        if p.health <= 0:
            p.health = 0
            p.alive  = False
            if not p.death_cause:
                p.death_cause = f"Ucciso da {e.name}"
            self.phase = CombatPhase.DEFEAT

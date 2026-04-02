import json
import os
import random
from typing import List, Optional

from combat.combat import CombatState
from core.constants import (
    CHUNK_SIZE,
    ESSENZA_ATTRS,
    ESSENZA_MIN,
    SCREEN_H,
    SCREEN_W,
    SECONDS_PER_GAME_HOUR_BASE,
    TILE_H,
)
from core.enums import GameState
from entities.entity import Entity
from entities.player import Player
from items.item import ITEM_GEN, Item
from world.world import World, WorldSettlements, WorldSpawner
from world.npc_behavior import NPCBehaviorEngine
from core.journal import Journal

from .bootstrap import pygame
from .floating_text import FloatingText


class GameBase:
    INTRO_NEXT = {
        GameState.INTRO_WELCOME: GameState.INTRO_ADVENTURE,
        GameState.INTRO_ADVENTURE: GameState.INTRO_DESTINY,
        GameState.INTRO_DESTINY: GameState.ESSENZA,
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("RogueLife - Eldoria Chronicles")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "normal": pygame.font.SysFont("Courier New", TILE_H, bold=False),
            "bold": pygame.font.SysFont("Courier New", TILE_H, bold=True),
            "large": pygame.font.SysFont("Courier New", 28, bold=True),
            "small": pygame.font.SysFont("Courier New", 15),
        }

        self.state = GameState.SPLASH
        self.running = True
        self.tick = 0.0

        self.player: Optional[Player] = None
        self.entities: List[Entity] = []
        self.items_on_ground: List[Item] = []
        self.tombstones: List[dict] = []
        self.dead_chars: List[dict] = []
        self.messages: List[str] = []
        self.journal: Journal = Journal()
        self.journal_cursor = 0
        self.journal_tab = 0

        self.seed = random.randint(0, 99999)
        self.world = World(self.seed, self.entities)
        self.spawner = WorldSpawner(self.world)
        self.settlements = WorldSettlements(self.world)
        self.npc_engine = NPCBehaviorEngine()
        self.game_time = 0.0
        self.day_number = 1

        self.name_input = ""
        self.inv_cursor = 0
        self.shop_cursor = 0
        self.sell_mode = False
        self.sell_cursor = 0
        self.dialog_ent: Optional[Entity] = None
        self.dialog_text_override: Optional[str] = None
        self.magic_aura_timer = 0.0
        self.magic_aura_has_power = False
        self.magic_pending_test = False
        self.magic_choice_yes = True
        self.last_dx = 0
        self.last_dy = 1
        self.merchant_ent: Optional[Entity] = None
        self.merchant_pending = False

        self.main_menu_cursor = 0
        self.has_save = os.path.exists("savegame.json")

        self.essenza_attrs = {a: ESSENZA_MIN for a in ESSENZA_ATTRS}
        self.essenza_cursor = 0
        self.essenza_yes = True

        self.move_timer = 0.0
        self.entity_tick = 0.0
        self.flee_immunity = 0.0
        self.save_flash = 0.0

        self.minimap_surf = pygame.Surface((180, 180))
        self.floating_texts: List[FloatingText] = []
        self.combat_state: Optional[CombatState] = None

        if os.path.exists("dead_characters.json"):
            try:
                with open("dead_characters.json") as f:
                    self.dead_chars = json.load(f)
            except Exception:
                pass

    def get_game_hour(self) -> float:
        return (self.game_time / SECONDS_PER_GAME_HOUR_BASE) % 24

    def get_time_of_day(self) -> str:
        h = self.get_game_hour()
        if 5 <= h < 8:
            return "DAWN"
        if 8 <= h < 18:
            return "DAY"
        if 18 <= h < 21:
            return "DUSK"
        return "NIGHT"

    def time_str(self) -> str:
        h = self.get_game_hour()
        hh = int(h)
        mm = int((h - hh) * 60)
        tod = self.get_time_of_day()
        icon = {"DAY": "[*]", "DAWN": "[^]", "DUSK": "[v]", "NIGHT": "[~]"}[tod]
        return f"{icon} Day {self.day_number} {hh:02d}:{mm:02d}"

    def log(self, msg: str):
        self.messages.append(msg)
        if len(self.messages) > 14:
            self.messages.pop(0)

    def journal_add(self, text: str, category: str = "misc"):
        if getattr(self, "journal", None):
            age = getattr(getattr(self, "player", None), "age", 0)
            try:
                self.journal.add(self.day_number, age, text, category)
            except Exception:
                pass

    def _spawn_in_house(self):
        if self.world.buildings:
            b = next((x for x in self.world.buildings if x.btype in ("casa", "locanda", "bottega", "ambulatorio", "chiesa", "scuola_magia")), None)
            if b is None:
                b = next((x for x in self.world.buildings if x.btype != "palace"), self.world.buildings[0])
            self.player.x = b.wx + b.w // 2
            self.player.y = b.wy + b.h // 2
        else:
            self.player.x = 0
            self.player.y = 0

    def start_new_game(self):
        name = self.name_input.strip() or "Eroe"
        self.player = Player(name)
        self.player.essenza = dict(self.essenza_attrs)
        self.entities = []
        self.items_on_ground = []
        self.tombstones = []
        self.messages = []
        self.journal = Journal()
        self.journal_cursor = 0
        self.journal_tab = 0
        self.game_time = 0.0
        self.day_number = 1
        self.world = World(self.seed, self.entities)
        self.spawner = WorldSpawner(self.world)
        self.settlements = WorldSettlements(self.world)
        self.npc_engine = NPCBehaviorEngine()
        self.spawner.bootstrap_all()
        self.settlements.bootstrap_all()
        self._spawn_in_house()
        self._preload_and_spawn(self.player.x, self.player.y)
        self.log(f"Benvenuto, {self.player.name}!")
        self.journal_add("L'avventura inizia.", "discovery")
        self.state = GameState.PLAYING

    def _preload_and_spawn(self, wx: int, wy: int, radius: int = 2):
        is_night = self.get_time_of_day() == "NIGHT"
        cx0 = wx // CHUNK_SIZE
        cy0 = wy // CHUNK_SIZE
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                self.world._ensure_chunk(cx0 + dx, cy0 + dy)
                self.spawner.populate_chunk_if_needed(cx0 + dx, cy0 + dy, is_night)
                self.settlements.try_generate(cx0 + dx, cy0 + dy)

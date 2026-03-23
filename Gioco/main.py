# =============================================================================
# main.py — RogueLife: Eldoria Chronicles  (versione consolidata)
# =============================================================================
import subprocess, sys

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import pygame
except ImportError:
    install("pygame"); import pygame

import random, json, os, math, time
from typing import Optional, List

from core.constants import *
from core.enums import GameState, LifeStage
from core.constants import ESSENZA_ATTRS, ESSENZA_POINTS, ESSENZA_MIN, ESSENZA_MAX
from core.utils import astar

from items.item import Item, ITEM_GEN
from entities.entity import Entity, make_entity
from entities.player import Player
from entities.quest import Quest
from world.world import World, WorldSpawner, WorldSettlements
from world.buildings import draw_building_labels
from combat.combat import CombatState, CombatPhase
from combat.combat_ui import draw_combat
from ui.hud import (draw_hud, draw_minimap, draw_night_overlay,
                    draw_equip_panel, draw_inventory_panel)
from ui.menus import (draw_splash, draw_main_menu, draw_options,
                      draw_menu_name, draw_intro_screen,
                      draw_essenza, draw_essenza_confirm,
                      draw_pause, draw_dead)
from ui.overlays import (draw_overlay, draw_inventory, draw_merchant,
                         draw_dialog, draw_quest_log)

ITEM_SYMBOL = "\xa7"
PANEL_X = VIEW_COLS * TILE_W
PANEL_W = SCREEN_W - PANEL_X



# =============================================================================
# MERCHANT AI — funzioni di supporto (a livello modulo)
# =============================================================================
def _merchant_open_gate(bottega, world):
    gx, gy = bottega.counter_gate_x, bottega.counter_gate_y
    from core.constants import FLOOR
    world.overrides[(gx, gy)] = FLOOR
    world.wall_chars[(gx, gy)] = "."
    bottega.counter_gate_open = True

def _merchant_close_gate(bottega, world):
    gx, gy = bottega.counter_gate_x, bottega.counter_gate_y
    from world.buildings import COUNTER
    world.overrides[(gx, gy)] = COUNTER
    world.wall_chars[(gx, gy)] = "|"
    bottega.counter_gate_open = False

def _merchant_blocked(nx, ny, entities, me):
    return any(o.x == nx and o.y == ny for o in entities if o is not me and o.alive)

# ─────────────────────────────────────────────────────────────────────────────
class FloatingText:
    def __init__(self, text, x, y, color, duration=1.2):
        self.text = text; self.x = x; self.y = y
        self.color = color; self.duration = duration
        self.age = 0.0; self.alive = True

    def update(self, dt):
        self.age += dt; self.y -= 30 * dt
        if self.age >= self.duration: self.alive = False

    def draw(self, screen, font):
        if self.alive:
            alpha = int(255 * (1 - self.age / self.duration))
            surf = font.render(self.text, True, self.color)
            surf.set_alpha(alpha)
            screen.blit(surf, (int(self.x), int(self.y)))


# ─────────────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("RogueLife - Eldoria Chronicles")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()
        self.fonts  = {
            "normal": pygame.font.SysFont("Courier New", TILE_H, bold=False),
            "bold":   pygame.font.SysFont("Courier New", TILE_H, bold=True),
            "large":  pygame.font.SysFont("Courier New", 28, bold=True),
            "small":  pygame.font.SysFont("Courier New", 15),
        }

        self.state   = GameState.SPLASH
        self.running = True
        self.tick    = 0.0

        self.player:          Optional[Player] = None
        self.entities:        List[Entity]     = []
        self.items_on_ground: List[Item]       = []
        self.tombstones:      List[dict]       = []
        self.dead_chars:      List[dict]       = []
        self.messages:        List[str]        = []

        self.seed       = random.randint(0, 99999)
        self.world      = World(self.seed, self.entities)
        self.spawner     = WorldSpawner(self.world)
        self.settlements = WorldSettlements(self.world)
        self.game_time  = 0.0
        self.day_number = 1

        self.name_input     = ""
        self.inv_cursor     = 0
        self.shop_cursor    = 0
        self.sell_mode      = False
        self.sell_cursor    = 0
        self.dialog_ent:   Optional[Entity] = None
        self.magic_aura_timer: float = 0.0   # > 0 = bagliore magia attivo
        self.magic_aura_has_power: bool = False
        self.last_dx: int = 0   # ultima direzione movimento player
        self.last_dy: int = 1   # default: giù
        self.merchant_ent: Optional[Entity] = None
        self.merchant_pending: bool = False

        self.main_menu_cursor = 0
        self.has_save         = os.path.exists("savegame.json")

        self.essenza_attrs  = {a: ESSENZA_MIN for a in ESSENZA_ATTRS}
        self.essenza_cursor = 0
        self.essenza_yes    = True

        self.move_timer    = 0.0
        self.entity_tick   = 0.0
        self.flee_immunity = 0.0
        self.save_flash    = 0.0   # secondi rimanenti del messaggio "partita salvata"

        self.minimap_surf   = pygame.Surface((180, 180))
        self.floating_texts: List[FloatingText] = []
        self.combat_state:  Optional[CombatState] = None

        if os.path.exists("dead_characters.json"):
            try:
                with open("dead_characters.json") as f:
                    self.dead_chars = json.load(f)
            except: pass

    # =========================================================================
    # TEMPO
    # =========================================================================
    def get_game_hour(self) -> float:
        return (self.game_time / SECONDS_PER_GAME_HOUR_BASE) % 24

    def get_time_of_day(self) -> str:
        h = self.get_game_hour()
        if 5  <= h < 8:  return "DAWN"
        if 8  <= h < 18: return "DAY"
        if 18 <= h < 21: return "DUSK"
        return "NIGHT"

    def time_str(self) -> str:
        h   = self.get_game_hour()
        hh  = int(h); mm = int((h - hh) * 60)
        tod = self.get_time_of_day()
        icon = {"DAY":"[*]","DAWN":"[^]","DUSK":"[v]","NIGHT":"[~]"}[tod]
        return f"{icon} Day {self.day_number} {hh:02d}:{mm:02d}"

    # =========================================================================
    # LOG
    # =========================================================================
    def log(self, msg: str):
        self.messages.append(msg)
        if len(self.messages) > 14: self.messages.pop(0)

    # =========================================================================
    # SPAWN INIZIALE
    # =========================================================================
    def _spawn_in_house(self):
        if self.world.buildings:
            b = self.world.buildings[0]
            self.player.x = b.wx + b.w // 2
            self.player.y = b.wy + b.h // 2
        else:
            self.player.x = 0; self.player.y = 0

    # =========================================================================
    # NUOVA PARTITA
    # =========================================================================
    def start_new_game(self):
        name = self.name_input.strip() or "Eroe"
        self.player = Player(name)
        self.player.essenza = dict(self.essenza_attrs)
        self.entities = []
        self.items_on_ground = []
        self.tombstones = []
        self.messages = []
        self.game_time = 0.0
        self.day_number = 1
        self.world = World(self.seed, self.entities)
        self.spawner     = WorldSpawner(self.world)
        self.settlements = WorldSettlements(self.world)
        self.world.place_starting_town(0, 0)
        self._spawn_in_house()
        self._preload_and_spawn(self.player.x, self.player.y)
        starter = ITEM_GEN.generate_item(rarity="common", item_type="weapon")
        self.player.inventory.append(starter)
        self.player.equipped_weapon = starter
        self.log(f"Benvenuto, {self.player.name}!")
        self.log(f"Arma iniziale: {starter.name}")
        self.state = GameState.PLAYING

    # =========================================================================
    # CARICA
    # =========================================================================
    def load_game(self):
        if not os.path.exists("savegame.json"):
            self.log("Nessun salvataggio trovato.")
            return
        try:
            with open("savegame.json", encoding="utf-8") as f:
                data = json.load(f)
            self.seed         = data.get("seed", self.seed)
            self.game_time    = data.get("game_time", 0.0)
            self.day_number   = data.get("day_number", 1)
            self.tombstones   = data.get("tombstones", [])
            self.messages     = data.get("messages", [])
            self.player       = Player.from_dict(data["player"])
            self.entities     = [Entity.from_dict(e) for e in data.get("entities", [])]
            self.items_on_ground = [Item.from_dict(i) for i in data.get("items_on_ground", [])]
            # Crea World DOPO aver popolato entities, così world.entities punta alla lista giusta
            self.world        = World(self.seed, self.entities)
            chunk_data        = data.get("world", data.get("chunks", {}))
            self.world.load_dict(chunk_data, self.seed)
            self.spawner = WorldSpawner(self.world)
            self.spawner.populated = set(self.world.chunks.keys())
            self._preload_and_spawn(self.player.x, self.player.y)
            self.state        = GameState.PLAYING
            self.log(f"Bentornato, {self.player.name}!")
        except KeyError as e:
            self.log(f"Salvataggio corrotto (chiave mancante: {e})")
            print(f"[LOAD ERROR - KeyError] {e}")
            self.state = GameState.MAIN_MENU
        except Exception as e:
            self.log(f"Errore caricamento: {e}")
            print(f"[LOAD ERROR] {type(e).__name__}: {e}")
            self.state = GameState.MAIN_MENU

    # =========================================================================
    # SALVA
    # =========================================================================
    def save_game(self):
        try:
            data = {
                "player":          self.player.to_dict(),
                "seed":            self.seed,
                "game_time":       self.game_time,
                "day_number":      self.day_number,
                "entities":        [e.to_dict() for e in self.entities],
                "world":           self.world.to_dict(),
                "items_on_ground": [i.to_dict() for i in self.items_on_ground],
                "tombstones":      self.tombstones,
                "messages":        self.messages,
            }
            with open("savegame.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.has_save = True
            self.save_flash = 2.0
            self.log("Partita salvata.")
            print("[SAVE OK] Partita salvata con successo")
        except Exception as e:
            self.log(f"Errore salvataggio: {e}")
            print(f"[SAVE ERROR] {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()

    # =========================================================================
    # HANDLER INPUT — menu
    # =========================================================================
    def _handle_splash(self, event):
        if event.type == pygame.KEYDOWN:
            self.has_save = os.path.exists("savegame.json")
            self.state = GameState.MAIN_MENU

    def _handle_main_menu(self, event):
        # Aggiorna has_save ogni volta (potrebbe essere stato creato in questa sessione)
        self.has_save = os.path.exists("savegame.json")
        if event.type != pygame.KEYDOWN: return
        k = event.key
        num_items = 3 if self.has_save else 2  # senza save: solo Nuova Partita + Opzioni
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
                if self.has_save: self.load_game()
                else: self.log("Nessuna partita salvata!")
            elif self.main_menu_cursor == 2:
                self.state = GameState.OPTIONS

    def _handle_options(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
            self.state = GameState.MAIN_MENU

    def _handle_menu_name(self, event):
        if event.type != pygame.KEYDOWN: return
        if event.key == pygame.K_RETURN and self.name_input.strip():
            self.state = GameState.INTRO_WELCOME
        elif event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
        elif len(self.name_input) < 20 and event.unicode.isprintable():
            self.name_input += event.unicode

    INTRO_NEXT = {
        GameState.INTRO_WELCOME:   GameState.INTRO_ADVENTURE,
        GameState.INTRO_ADVENTURE: GameState.INTRO_DESTINY,
        GameState.INTRO_DESTINY:   GameState.ESSENZA,
    }

    def _handle_intro(self, event):
        if event.type == pygame.KEYDOWN:
            self.state = self.INTRO_NEXT[self.state]
            if self.state == GameState.ESSENZA:
                self.essenza_attrs  = {a: ESSENZA_MIN for a in ESSENZA_ATTRS}
                self.essenza_cursor = 0

    def _intro_message(self) -> str:
        name = self.name_input.strip() or "Eroe"
        return {
            GameState.INTRO_WELCOME:   f"Benvenuto, {name}",
            GameState.INTRO_ADVENTURE: "La tua avventura sta per avere inizio",
            GameState.INTRO_DESTINY:   "Il destino è nelle tue mani, fa la scelta giusta",
        }.get(self.state, "")

    def _essenza_spent(self) -> int:
        return sum(self.essenza_attrs.values())

    def _handle_essenza(self, event):
        if event.type != pygame.KEYDOWN: return
        k    = event.key
        attr = ESSENZA_ATTRS[self.essenza_cursor]
        val  = self.essenza_attrs[attr]
        if k == pygame.K_UP:
            self.essenza_cursor = (self.essenza_cursor - 1) % len(ESSENZA_ATTRS)
        elif k == pygame.K_DOWN:
            self.essenza_cursor = (self.essenza_cursor + 1) % len(ESSENZA_ATTRS)
        elif k == pygame.K_RIGHT:
            if val < ESSENZA_MAX and self._essenza_spent() < ESSENZA_POINTS:
                self.essenza_attrs[attr] += 1
        elif k == pygame.K_LEFT:
            if val > ESSENZA_MIN: self.essenza_attrs[attr] -= 1
        elif k == pygame.K_RETURN:
            if self._essenza_spent() == ESSENZA_POINTS:
                self.essenza_yes = True
                self.state = GameState.ESSENZA_CONFIRM

    def _handle_essenza_confirm(self, event):
        if event.type != pygame.KEYDOWN: return
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.essenza_yes = not self.essenza_yes
        elif event.key == pygame.K_RETURN:
            if self.essenza_yes: self.start_new_game()
            else: self.state = GameState.ESSENZA

    # =========================================================================
    def _preload_and_spawn(self, wx: int, wy: int, radius: int = 2):
        """Precarica chunk intorno a (wx,wy), spawna nemici e genera villaggi."""
        is_night = self.get_time_of_day() == "NIGHT"
        cx0 = wx // CHUNK_SIZE
        cy0 = wy // CHUNK_SIZE
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                self.world._ensure_chunk(cx0+dx, cy0+dy)
                self.spawner.populate_chunk_if_needed(cx0+dx, cy0+dy, is_night)
                self.settlements.try_generate(cx0+dx, cy0+dy)

    # GAMEPLAY
    # =========================================================================
    def try_move(self, dx: int, dy: int):
        p = self.player
        if dx != 0 or dy != 0:
            self.last_dx = dx
            self.last_dy = dy
        nx, ny = p.x + dx, p.y + dy
        if abs(nx) > WORLD_LIMIT or abs(ny) > WORLD_LIMIT:
            self.log("Bordo del mondo!"); return
        if not self.world.is_passable(nx, ny): return
        for b in self.world.buildings:
            if getattr(b, "btype", "") == "bottega":
                if (nx, ny) in getattr(b, "merchant_zone", set()):
                    self.log("Zona riservata al mercante."); return
                if (nx, ny) == (getattr(b,"back_door_x",None), getattr(b,"back_door_y",None)):
                    self.log("Porta di servizio — solo per il mercante."); return
        for e in self.entities:
            if e.alive and e.x == nx and e.y == ny:
                if e.ai_type in ("aggressive", "ghost"):
                    if self.flee_immunity > 0: return
                    biome = self.world.get_biome_at(p.x, p.y)
                    self.combat_state = CombatState(p, e, biome)
                    self.state = GameState.COMBAT
                    return
                return
        p.x, p.y = nx, ny
        self._preload_and_spawn(p.x, p.y)
        for item in list(self.items_on_ground):
            if item.x == p.x and item.y == p.y:
                p.inventory.append(item)
                self.items_on_ground.remove(item)
                self.log(f"Raccolto: {item.name} [{item.rarity}]")
                fc  = RARITY_COLORS.get(item.rarity, (255,255,255))
                psx = (VIEW_COLS//2)*TILE_W + TILE_W//2
                psy = (VIEW_ROWS//2)*TILE_H - 24
                self.floating_texts.append(FloatingText(f"+ {item.name}", psx, psy, fc, 1.6))
                # ESSENZA Fortuna: cresce raccogliendo oggetti
                grew = p.register_action("loot")
                if grew:
                    self.log(f"[ESSENZA] {grew} aumenta a {p.essenza[grew]}!")
                for q in p.active_quests:
                    if q.obj_type=="collect" and q.obj_target in item.name and not q.completed:
                        q.current = min(q.current+1, q.obj_count)
                        self.log(f"Quest [{q.title}]: {q.progress_str}")
        for q in list(p.active_quests):
            if not q.completed and q.current >= q.obj_count:
                q.completed = True
                p.completed_quests.append(q.qid)
                p.gold += q.reward_gold
                for lv in p.add_xp(q.reward_xp): self.log(f"LEVEL UP! Livello {lv}!")
                self.log(f"Quest COMPLETATA: {q.title}! +{q.reward_gold}g +{q.reward_xp}xp")
                p.active_quests.remove(q)

        # Registra esplorazione per ESSENZA Percezione
        grew = p.register_action("esplorazione")
        if grew:
            self.log(f"[ESSENZA] {grew} aumenta a {p.essenza[grew]}!")

    def interact(self):
        p = self.player
        # Priorità interact: NPC nella direzione di sguardo
        _ldx, _ldy = getattr(self, 'last_dx', 0), getattr(self, 'last_dy', 1)
        def _ent_priority(e):
            ex, ey = e.x - p.x, e.y - p.y
            if ex == _ldx and ey == _ldy: return 0
            if ex == _ldx or ey == _ldy: return 1
            return 2
        _nearby = sorted(
            [e for e in self.entities if e.alive and abs(e.x-p.x)<=3 and abs(e.y-p.y)<=3],
            key=_ent_priority)
        for e in _nearby:
            if not e.alive: continue
            _interact_r = 3 if e.ai_type in ("merchant", "innkeeper") else 1
            if abs(e.x-p.x) <= _interact_r and abs(e.y-p.y) <= _interact_r:
                if e.ai_type in ("merchant", "innkeeper"):
                    if not hasattr(e, "gold"): e.gold = random.randint(100,400)
                    if not hasattr(e, "shop") or not e.shop:
                        e.populate_shop()
                    self.merchant_ent = e
                    self.shop_cursor = 0; self.sell_cursor = 0; self.sell_mode = False
                    self.dialog_ent = e
                    self.merchant_pending = True
                    self.state = GameState.DIALOG
                    self.log(f'{e.name}: "{e.dialogue}"')
                    return
                # Insegnante di magia: test speciale se il player ha < 8 anni non può
                if getattr(e, "npc_role", "") == "ins_magia":
                    if p.age < 8:
                        self.log(f'{e.name}: "Torna quando sarai più grande..."')
                        return
                    if not getattr(p, "magic_revealed", False):
                        # Primo incontro: attiva test magico
                        p.magic_revealed = True
                        self.log(f'{e.name}: "Lascia che provi a risvegliarti..."')
                        self.magic_aura_timer = 2.5
                        self.magic_aura_has_power = (getattr(p, "magic_factor", 0) == 1)
                        return
                    else:
                        # Già testato: dialogo normale
                        if getattr(p, "magic_factor", 0) == 1:
                            self.log(f'{e.name}: "La magia è in te. Coltivala."')
                        else:
                            self.log(f'{e.name}: "Il mondo ha bisogno anche di chi non usa la magia."')
                        return
                self.dialog_ent = e
                self.state = GameState.DIALOG
                self.log(f'{e.name}: "{e.dialogue}"')
                # ESSENZA Carisma: cresce con i dialoghi
                grew = p.register_action("dialoghi")
                if grew:
                    self.log(f"[ESSENZA] {grew} aumenta a {p.essenza[grew]}!")
                if (e.has_quest and e.quest and not e.quest.completed
                        and e.quest.qid not in p.completed_quests
                        and not any(q.qid==e.quest.qid for q in p.active_quests)
                        and len(p.active_quests) < 3):
                    p.active_quests.append(e.quest)
                    self.log(f"Nuova quest: {e.quest.title}!")
                return
        for ts in self.tombstones:
            if abs(ts["x"]-p.x) <= 1 and abs(ts["y"]-p.y) <= 1:
                self.log(f"'{ts['name']}, eta {ts['age']}. {ts['cause']}'")

    def use_item(self, item):
        p = self.player
        if item.item_type == "potion":
            heal = item.stats.get("heal", 0)
            p.health = min(p.max_health, p.health+heal)
            self.log(f"Usato {item.name}: +{heal} PF")
            p.inventory.remove(item)
        elif item.item_type == "weapon":  p.equipped_weapon = item; self.log(f"Equipaggiato {item.name}")
        elif item.item_type == "armor":   p.equipped_armor  = item; self.log(f"Equipaggiato {item.name}")
        elif item.item_type == "helmet":  p.equipped_head   = item; self.log(f"Equipaggiato {item.name}")
        elif item.item_type == "legs":    p.equipped_legs   = item; self.log(f"Equipaggiato {item.name}")
        elif item.item_type == "shield":  p.equipped_shield = item; self.log(f"Equipaggiato {item.name}")
        elif item.item_type == "boots":   p.equipped_boots  = item; self.log(f"Equipaggiato {item.name}")
        else: self.log(f"{item.name}: {item.description}")

    def handle_death(self):
        if self.state == GameState.DEAD: return
        p = self.player
        if not p.death_cause: p.death_cause = "Causa sconosciuta"
        ts = {"x":p.x,"y":p.y,"name":p.name,"age":p.age,
              "cause":p.death_cause,"level":p.level,"kills":p.kills}
        self.tombstones.append(ts)
        self.dead_chars.append(ts)
        try:
            with open("dead_characters.json","w") as f: json.dump(self.dead_chars, f, indent=2)
        except: pass
        # Elimina il salvataggio: ogni run è permanente, la morte è definitiva
        try:
            if os.path.exists("savegame.json"):
                os.remove("savegame.json")
        except: pass
        self.has_save = False
        # Piazza la tomba nel mondo (fuori dalle mura, casuale)
        self._place_tombstone(ts)
        self.state = GameState.DEAD

    def _place_tombstone(self, ts: dict):
        """Piazza una tomba fuori dalle mura della città in posizione casuale."""
        cw = getattr(self.world, "city_wall", None)
        rng = random.Random(hash(ts["name"]) ^ ts.get("level", 1))
        placed = False
        if cw is not None:
            # Prova posizioni casuali fuori dalle mura ma vicino
            for _ in range(40):
                angle_idx = rng.randint(0, 3)
                if angle_idx == 0:   tx = rng.randint(cw.x0 - 12, cw.x1 + 12); ty = cw.y0 - rng.randint(3, 10)
                elif angle_idx == 1: tx = rng.randint(cw.x0 - 12, cw.x1 + 12); ty = cw.y1 + rng.randint(3, 10)
                elif angle_idx == 2: tx = cw.x0 - rng.randint(3, 10);          ty = rng.randint(cw.y0, cw.y1)
                else:                tx = cw.x1 + rng.randint(3, 10);          ty = rng.randint(cw.y0, cw.y1)
                if self.world.is_passable(tx, ty):
                    self._build_grave(tx, ty, ts["name"])
                    placed = True; break
        if not placed:
            # Fallback: 15 tile a est del player
            tx, ty = ts["x"] + 15, ts["y"]
            self._build_grave(tx, ty, ts["name"])

    def _build_grave(self, cx: int, cy: int, name: str):
        """Struttura tomba 3x3: croce centrale + muri piccoli."""
        from core.constants import DEN, GRASS
        ov = self.world.overrides
        wc = self.world.wall_chars
        # struttura 3x3
        layout = [
            ("+", DEN), ("_", DEN), ("+", DEN),
            ("|", DEN), ("+", GRASS),("|", DEN),
            ("+", DEN), ("_", DEN), ("+", DEN),
        ]
        i = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                char, tile = layout[i]; i += 1
                ov[(cx+dx, cy+dy)] = tile
                if tile == DEN:
                    wc[(cx+dx, cy+dy)] = char
        # Centro: tile passabile con croce
        ov[(cx, cy)] = GRASS
        wc[(cx, cy)] = "†"
        # Registra come tombstone interagibile
        for ts2 in self.tombstones:
            if ts2["name"] == name:
                ts2["x"] = cx; ts2["y"] = cy; break

    def _end_combat(self):
        cs = self.combat_state
        if not cs: return
        p = self.player

        # Registra azioni ESSENZA dal combattimento
        if cs.phase != CombatPhase.FLED:
            grew = p.register_action("attacchi")
            if grew: self.log(f"[ESSENZA] {grew} aumenta a {p.essenza[grew]}!")
            grew = p.register_action("danni_subiti")
            if grew: self.log(f"[ESSENZA] {grew} aumenta a {p.essenza[grew]}!")
        else:
            # Fuga riuscita → Agilità
            grew = p.register_action("schivate")
            if grew: self.log(f"[ESSENZA] {grew} aumenta a {p.essenza[grew]}!")

        for lv in p.add_xp(cs.xp_gained):
            self.log(f"LEVEL UP! Livello {lv}!")
        p.gold += cs.gold_gained
        if cs.loot_item:
            cs.loot_item.x = p.x; cs.loot_item.y = p.y
            self.items_on_ground.append(cs.loot_item)
            self.log(f"Loot: {cs.loot_item.name}!")
        if not cs.enemy.alive:
            self.entities = [e for e in self.entities if e is not cs.enemy]
        if cs.phase == CombatPhase.FLED:
            self.flee_immunity = 3.0
            self.log("Sei fuggito! Immunita per 3 secondi.")
        self.combat_state = None
        self.state = GameState.PLAYING


    # =========================================================================
    # MERCHANT AI — logica giornaliera bottega
    # =========================================================================
    def _merchant_path(self, e, tx, ty, passable, limit=80):
        return astar(e.x, e.y, tx, ty, passable, limit)

    def _update_merchant_ai(self, e, passable):
        import random as _r
        tod   = self.get_time_of_day()
        world = self.world
        bottega = None
        for b in world.buildings:
            if b.btype == "bottega":
                zone  = getattr(b, "merchant_zone", set())
                spawn = getattr(b, "merchant_spawn", (b.wx, b.wy))
                back  = (getattr(b, "back_door_x", b.wx), getattr(b, "back_door_y", b.wy))
                if (e.x, e.y) in (zone | {spawn} | {back}):
                    bottega = b; break
        if bottega is None:
            for b in world.buildings:
                if b.btype == "bottega": bottega = b; break
        if bottega is None: return
        spawn_x, spawn_y = getattr(bottega, "merchant_spawn", (bottega.wx, bottega.wy))
        back_x = getattr(bottega, "back_door_x", bottega.wx)
        back_y = getattr(bottega, "back_door_y", bottega.wy)
        # DAWN
        if tod == "DAWN" and not getattr(e, "_dawn_rolled", False):
            e._dawn_rolled = True; e.daily_roll = _r.randint(1, 10); e.exits_today = 0
            cw = getattr(world, "city_wall", None)
            if cw and e.daily_roll >= 6:
                side = _r.choice(["n","s","e","w"]); dist = _r.randint(6, 16)
                if   side == "n": e.outdoor_x = cw.cx+_r.randint(-8,8); e.outdoor_y = cw.y0-dist
                elif side == "s": e.outdoor_x = cw.cx+_r.randint(-8,8); e.outdoor_y = cw.y1+dist
                elif side == "e": e.outdoor_x = cw.x1+dist;             e.outdoor_y = cw.cy+_r.randint(-8,8)
                else:             e.outdoor_x = cw.x0-dist;             e.outdoor_y = cw.cy+_r.randint(-8,8)
            else: e.outdoor_x = spawn_x; e.outdoor_y = spawn_y
        elif tod != "DAWN": e._dawn_rolled = False
        # NIGHT — mercante va nel retro
        if tod == "NIGHT":
            e.is_outside = False
            gate_x = getattr(bottega, "counter_gate_x", bottega.wx + 5)
            gate_y = getattr(bottega, "counter_gate_y", bottega.wy + 3)
            retro_x = bottega.wx + 11  # stanza retro mercante (FLOOR libero)
            retro_y = bottega.wy + 4
            if (e.x, e.y) == (retro_x, retro_y):
                _merchant_close_gate(bottega, world)
            else:
                _merchant_open_gate(bottega, world)
                def passable_with_gate(x, y, _p=passable,
                                       _gx=gate_x, _gy=gate_y,
                                       _bx=back_x, _by=back_y,
                                       _cx=bottega.wx+8, _cy0=bottega.wy+1, _cy1=bottega.wy+5):
                    if x == _gx and y == _gy: return True
                    if x == _bx and y == _by: return True
                    if x == _cx and _cy0 <= y <= _cy1: return True
                    return _p(x, y)
                path = self._merchant_path(e, retro_x, retro_y, passable_with_gate, limit=120)
                if path:
                    nx2, ny2 = path[0]
                    if not _merchant_blocked(nx2, ny2, self.entities, e):
                        e.x, e.y = nx2, ny2
            return
        # DUSK
        if tod == "DUSK":
            e.is_outside = False; _merchant_close_gate(bottega, world)
            if (e.x, e.y) == (back_x, back_y):
                e.x, e.y = spawn_x, spawn_y
            elif (e.x, e.y) != (spawn_x, spawn_y):
                path = self._merchant_path(e, back_x, back_y, passable)
                if not path: path = self._merchant_path(e, spawn_x, spawn_y, passable)
                if path:
                    nx2, ny2 = path[0]
                    if not _merchant_blocked(nx2, ny2, self.entities, e): e.x, e.y = nx2, ny2
            return
        # DAY
        goes_out = getattr(e, "daily_roll", 0) >= 6 and getattr(e, "exits_today", 0) == 0
        zone     = getattr(bottega, "merchant_zone", set())
        in_zone  = (e.x, e.y) in (zone | {spawn_x, spawn_y})
        if getattr(e, "is_outside", False):
            outdoor_x = getattr(e, "outdoor_x", spawn_x)
            outdoor_y = getattr(e, "outdoor_y", spawn_y)
            for item in list(self.items_on_ground):
                if abs(item.x-e.x)+abs(item.y-e.y) <= 2:
                    markup = int(item.value * _r.uniform(1.2, 1.8))
                    found  = Item(item.name, item.item_type, item.rarity,
                                  item.description, markup, item.stats.copy())
                    e.found_items = getattr(e, "found_items", [])
                    e.found_items.append(found); e.shop.append(found)
                    self.items_on_ground.remove(item)
                    self.log(f"Mercante raccoglie: {item.name}")
            dist_dest = abs(e.x-outdoor_x)+abs(e.y-outdoor_y)
            if dist_dest <= 2:
                path = self._merchant_path(e, back_x, back_y, passable)
                if path:
                    nx2, ny2 = path[0]
                    if not _merchant_blocked(nx2, ny2, self.entities, e): e.x, e.y = nx2, ny2
                if abs(e.x-back_x)+abs(e.y-back_y) <= 1:
                    e.is_outside = False; e.exits_today = 1
                    _merchant_close_gate(bottega, world); e.x, e.y = spawn_x, spawn_y
            else:
                path = self._merchant_path(e, outdoor_x, outdoor_y, passable)
                if path:
                    nx2, ny2 = path[0]
                    if not _merchant_blocked(nx2, ny2, self.entities, e): e.x, e.y = nx2, ny2
        elif goes_out and in_zone:
            _merchant_open_gate(bottega, world)
            path = self._merchant_path(e, back_x, back_y, passable)
            if path:
                nx2, ny2 = path[0]
                if not _merchant_blocked(nx2, ny2, self.entities, e): e.x, e.y = nx2, ny2
            if (e.x, e.y) == (back_x, back_y):
                sx, sy = back_x+1, back_y
                if passable(sx, sy): e.x, e.y = sx, sy
                e.is_outside = True; _merchant_close_gate(bottega, world)
        else:
            if _r.random() < 0.25 and zone:
                cands = list(zone); _r.shuffle(cands)
                for zx, zy in cands:
                    if not _merchant_blocked(zx, zy, self.entities, e):
                        e.x, e.y = zx, zy; break

    def _update_innkeeper_ai(self, e, passable):
        import random as _r
        tod   = self.get_time_of_day()
        world = self.world

        locanda = next((b for b in world.buildings if b.btype == "locanda"), None)
        if locanda is None: return

        spawn_x, spawn_y = getattr(locanda, "innkeeper_spawn", (locanda.wx+4, locanda.wy+2))
        back_x  = getattr(locanda, "back_door_x", locanda.wx + 11)
        back_y  = getattr(locanda, "back_door_y", locanda.wy + 2)
        gate_x  = getattr(locanda, "counter_gate_x", locanda.wx + 8)
        gate_y  = getattr(locanda, "counter_gate_y", locanda.wy + 2)
        inn_zone = getattr(locanda, "innkeeper_zone", set())

        # Retro: tile dentro l'edificio oltre back_door (dx=12, dy=1..3)
        # back_door è a wx+11 — il retro è a wx+12 (letto/scaffali a dy=1..3)
        # ma quelli sono furniture. Usiamo wx+10, dy=back_y che è inn_zone
        # Il percorso notturno: inn_zone → gate(wx+5,wy+4) → zona servizio
        # (wx+9..10,wy+1..4) → back_door(wx+11,wy+4) → retro(wx+10,wy+2)
        retro_x = locanda.wx + 12   # stanza retro (tile letto)
        retro_y = locanda.wy + 2

        def _blocked(nx, ny):
            return any(o.x==nx and o.y==ny for o in self.entities if o is not e and o.alive)

        # Passable SOLO dentro inn_zone (giorno)
        def _passable_zone(x, y):
            return (x, y) in inn_zone and not _blocked(x, y)

        # Passable notte/alba: gate + back_door attraversabili
        # NON include il bancone lato dx (wx+8) — quello è COUNTER e deve restare tale
        def _passable_gate(x, y,
                           _gx=gate_x, _gy=gate_y,
                           _bx=back_x, _by=back_y):
            if x == _gx and y == _gy: return True   # gate sportello
            if x == _bx and y == _by: return True   # porta retro
            # Zona servizio già in inn_zone: già passabile via is_passable
            return passable(x, y)

        def _move_zone(tx, ty):
            path = astar(e.x, e.y, tx, ty, _passable_zone, 60)
            if path:
                nx2, ny2 = path[0]
                if not _blocked(nx2, ny2): e.x, e.y = nx2, ny2

        def _move_free(tx, ty, lim=80):
            path = astar(e.x, e.y, tx, ty, _passable_gate, lim)
            if path:
                nx2, ny2 = path[0]
                if not _blocked(nx2, ny2): e.x, e.y = nx2, ny2

        # ── NOTTE ─────────────────────────────────────────────────────────
        if tod == "NIGHT":
            if (e.x, e.y) == (retro_x, retro_y):
                _merchant_close_gate(locanda, world)
            else:
                _merchant_open_gate(locanda, world)
                _move_free(retro_x, retro_y)
            return

        # ── ALBA ──────────────────────────────────────────────────────────
        if tod == "DAWN":
            if (e.x, e.y) not in inn_zone:
                _merchant_open_gate(locanda, world)
                _move_free(spawn_x, spawn_y)
            else:
                _merchant_close_gate(locanda, world)
            return

        # ── GIORNO/CREPUSCOLO: gate chiuso, oste dentro la zona ───────────
        _merchant_close_gate(locanda, world)

        if (e.x, e.y) not in inn_zone:
            _merchant_open_gate(locanda, world)
            _move_free(spawn_x, spawn_y)
            return

        table_seats = getattr(locanda, "table_seats", {})
        all_seats   = [s for seats in table_seats.values() for s in seats]

        target_npc = None
        for other in self.entities:
            if other is e or not other.alive: continue
            if other.ai_type in ("wander","npc") and (other.x, other.y) in all_seats:
                if abs(other.x-e.x)+abs(other.y-e.y) <= 10:
                    target_npc = other; break

        if target_npc:
            free_zone = [pos for pos in inn_zone if not _blocked(*pos)]
            if free_zone:
                best = min(free_zone, key=lambda p: abs(p[0]-target_npc.x)+abs(p[1]-target_npc.y))
                if (e.x, e.y) != best: _move_zone(best[0], best[1])
            if _r.random() < 0.12:
                e.gold = getattr(e, "gold", 0) + _r.randint(1, 3)
        else:
            free_zone = [pos for pos in inn_zone if not _blocked(*pos)]
            if free_zone and _r.random() < 0.25:
                _move_zone(*_r.choice(free_zone))

    # =========================================================================
    # UPDATE ENTITA
    # =========================================================================
    def update_entities(self, dt: float):
        if self.flee_immunity > 0:
            self.flee_immunity = max(0.0, self.flee_immunity - dt)
        self.game_time += dt
        old_day = self.day_number
        self.day_number = int(self.game_time / SECONDS_PER_GAME_HOUR_BASE) // 24 + 1
        if self.day_number != old_day: self.log(f"Giorno {self.day_number} inizia.")
        self.entity_tick += dt
        if self.entity_tick < 0.5: return
        self.entity_tick = 0.0
        p = self.player
        nm = 1.5 if self.get_time_of_day() == "NIGHT" else 1.0
        for e in list(self.entities):
            if not e.alive: continue
            dist = abs(e.x-p.x) + abs(e.y-p.y)
            def passable(x, y, _e=e):
                return (self.world.is_passable_ghost(x,y) if _e.ai_type=="ghost"
                        else self.world.is_passable(x,y))
            if e.ai_type == "aggressive":
                if self.flee_immunity > 0: continue
                if self.state == GameState.COMBAT and dist > 1: continue
                # Attacca NPC civili vicini (wander/flee) — non il player
                attacked_npc = False
                for other in self.entities:
                    if other is e or not other.alive: continue
                    if other.ai_type in ("wander", "flee", "npc"):
                        od = abs(other.x - e.x) + abs(other.y - e.y)
                        if od == 1:
                            dmg = max(1, e.damage - getattr(other, "defense", 0))
                            other.health -= dmg
                            # Floating damage sull'NPC colpito
                            half_c = VIEW_COLS//2; half_r = VIEW_ROWS//2
                            sx = (other.x - p.x + half_c) * TILE_W
                            sy = (other.y - p.y + half_r) * TILE_H
                            self.floating_texts.append(FloatingText(
                                str(dmg), sx, sy, (255, 80, 80), 1.2))
                            if other.health <= 0:
                                other.alive = False
                            attacked_npc = True
                            break
                        elif od <= int(6*nm):
                            path = astar(e.x, e.y, other.x, other.y, passable)
                            if path:
                                nx2, ny2 = path[0]
                                if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                    e.x, e.y = nx2, ny2
                            attacked_npc = True
                            break
                if attacked_npc: continue
                if dist <= int(8*nm):
                    if dist == 1:
                        self.combat_state = CombatState(p, e, self.world.get_biome_at(p.x,p.y))
                        self.state = GameState.COMBAT; break
                    else:
                        path = astar(e.x,e.y,p.x,p.y,passable)
                        if path:
                            nx2,ny2 = path[0]
                            if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                e.x,e.y = nx2,ny2
            elif e.ai_type == "flee":
                if dist < 5:
                    dx_=e.x-p.x; dy_=e.y-p.y
                    mx=(1 if dx_>0 else -1) if dx_!=0 else random.choice([-1,1])
                    my=(1 if dy_>0 else -1) if dy_!=0 else random.choice([-1,1])
                    opts=[(e.x+mx,e.y),(e.x,e.y+my),(e.x+mx,e.y+my)]
                    random.shuffle(opts)
                    for nx2,ny2 in opts:
                        if passable(nx2,ny2): e.x,e.y=nx2,ny2; break
            elif e.ai_type == "ghost":
                if self.state == GameState.COMBAT or self.flee_immunity > 0: continue
                if dist <= int(6*nm):
                    if dist == 1:
                        self.combat_state = CombatState(p, e, self.world.get_biome_at(p.x,p.y))
                        self.state = GameState.COMBAT; break
                    else:
                        path = astar(e.x,e.y,p.x,p.y,passable,30)
                        if path: e.x,e.y=path[0]
                        else:
                            dx_,dy_=random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                            e.x+=dx_; e.y+=dy_
            elif e.ai_type in ("merchant", "innkeeper", "npc"):
                if e.ai_type == "merchant" and getattr(e, "npc_role", "") == "merchant":
                    self._update_merchant_ai(e, passable)
                elif e.ai_type == "innkeeper" and getattr(e, "npc_role", "") == "oste":
                    self._update_innkeeper_ai(e, passable)
                else:
                    hx = getattr(e, "home_x", e.x)
                    hy = getattr(e, "home_y", e.y)
                    hr = getattr(e, "home_radius", 8)
                    home_dist = abs(e.x - hx) + abs(e.y - hy)
                    if home_dist > hr:
                        path = astar(e.x, e.y, hx, hy, passable, 40)
                        if path:
                            nx2, ny2 = path[0]
                            if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                e.x, e.y = nx2, ny2
                    elif dist > 10 and random.random() < 0.3:
                        dx_, dy_ = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                        nx2, ny2 = e.x+dx_, e.y+dy_
                        if passable(nx2, ny2):
                            e.x, e.y = nx2, ny2
            elif e.ai_type == "wander":
                # ── Schedule giornaliera per ruolo ──────────────────────
                hx  = getattr(e, "home_x",    e.x)
                hy  = getattr(e, "home_y",    e.y)
                hr  = getattr(e, "home_radius", 10)
                wx_ = getattr(e, "work_x",    hx)
                wy_ = getattr(e, "work_y",    hy)
                wr_ = getattr(e, "work_radius", 5)
                tx_ = getattr(e, "tavern_x",  hx)
                ty_ = getattr(e, "tavern_y",  hy)
                role= getattr(e, "npc_role",  "")
                hour= self.get_game_hour()
                tod = self.get_time_of_day()
                is_night = tod == "NIGHT"
                # Fase del giorno per schedule:
                # MATTINA 05-12: lavoro
                # POMERIGGIO 12-18: lavoro / casa (anziano/bambino: piazza)
                # SERA 18-21: locanda/piazza
                # NOTTE 21-05: casa
                if   5  <= hour < 12: phase = "WORK"
                elif 12 <= hour < 18: phase = "WORK" if role not in ("anziano","bambino") else "HOME"
                elif 18 <= hour < 21: phase = "TAVERN"
                else:                 phase = "NIGHT"
                # Ruoli che NON escono mai dalle mura
                indoor_roles = {"fabbro","prete","guaritore","ins_magia","anziano","bambino","guardia_civ"}
                # Ruoli outdoor: destinazione fuori dalle mura
                outdoor_roles = {"contadino","taglialegna","cacciatore","minatore"}
                cw_ref = getattr(self.world, "city_wall", None)
                if role in outdoor_roles and phase == "WORK" and cw_ref is not None:
                    if not getattr(e, "outdoor_dest_set", False):
                        e.outdoor_dest_set = True
                        import random as _r2
                        side = _r2.choice(["n","s","e","w"])
                        dist = _r2.randint(8, 18)
                        if side == "n":   e.work_x = cw_ref.cx + _r2.randint(-10,10); e.work_y = cw_ref.y0 - dist
                        elif side == "s": e.work_x = cw_ref.cx + _r2.randint(-10,10); e.work_y = cw_ref.y1 + dist
                        elif side == "e": e.work_x = cw_ref.x1 + dist; e.work_y = cw_ref.cy + _r2.randint(-10,10)
                        else:             e.work_x = cw_ref.x0 - dist; e.work_y = cw_ref.cy + _r2.randint(-10,10)
                    if phase == "WORK":
                        dest_x, dest_y = getattr(e, "work_x", dest_x), getattr(e, "work_y", dest_y)
                # Destinazione effettiva per questa fase
                if phase == "WORK":
                    dest_x, dest_y, dest_r = wx_, wy_, wr_
                elif phase == "TAVERN":
                    dest_x, dest_y, dest_r = tx_, ty_, 4
                elif phase == "HOME":
                    dest_x, dest_y, dest_r = hx, hy, hr
                else:  # NIGHT
                    dest_x, dest_y, dest_r = hx, hy, hr
                home_dist = abs(e.x - hx) + abs(e.y - hy)
                # Fuga da nemici aggressivi vicini (priorità massima)
                threat = None
                for other in self.entities:
                    if other is e or not other.alive: continue
                    if other.ai_type in ("aggressive", "ghost"):
                        td = abs(other.x - e.x) + abs(other.y - e.y)
                        if td <= 5:
                            threat = other; break
                if threat:
                    cw = getattr(self.world, "city_wall", None)
                    # Se fuori dalle mura, fuggi verso la porta della città
                    if cw is not None and not cw.is_inside(e.x, e.y):
                        gx, gy = cw.gate_outside_s()
                        gdist  = abs(e.x - gx) + abs(e.y - gy)
                        if gdist > 2:
                            path = astar(e.x, e.y, gx, gy, passable, 150)
                            if path:
                                nx2, ny2 = path[0]
                                if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                    e.x, e.y = nx2, ny2
                                continue
                    # Dentro le mura o nessuna mura: fuggi nella direzione opposta al nemico
                    dx_ = e.x - threat.x; dy_ = e.y - threat.y
                    mx = (1 if dx_ > 0 else -1) if dx_ != 0 else random.choice([-1,1])
                    my = (1 if dy_ > 0 else -1) if dy_ != 0 else random.choice([-1,1])
                    for nx2, ny2 in [(e.x+mx, e.y), (e.x, e.y+my), (e.x+mx, e.y+my)]:
                        if passable(nx2, ny2) and not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                            e.x, e.y = nx2, ny2; break
                    continue

                # Regole uscita dalle mura per fase e ruolo
                cw = getattr(self.world, "city_wall", None)
                outside = cw is not None and not cw.is_inside(e.x, e.y)
                # Ruoli indoor: se di notte o in fase non-lavoro, sempre verso casa
                if role in indoor_roles and outside:
                    phase = "NIGHT"  # forza rientro immediato
                    dest_x, dest_y, dest_r = hx, hy, hr
                # Ruoli outdoor: di notte devono rientrare
                actual_dest_x, actual_dest_y = dest_x, dest_y
                if phase == "NIGHT" or (outside and phase != "WORK"):
                    # Waypoint progressivo: porta esterna → interna → casa
                    if outside:
                        gx, gy = cw.gate_outside_s()
                        gdist  = abs(e.x - gx) + abs(e.y - gy)
                        if gdist > 1:
                            actual_dest_x, actual_dest_y = gx, gy
                        else:
                            actual_dest_x, actual_dest_y = cw.cx, cw.y1 - 2
                    else:
                        # Assegna sleep_x una sola volta
                        if getattr(e, "sleep_x", None) is None:
                            best = None; best_dist = 9999
                            for b in getattr(self.world, "buildings", []):
                                if b.btype != "casa": continue
                                for tx2, ty2 in b.interior_tiles():
                                    d2 = abs(tx2-hx)+abs(ty2-hy)
                                    if d2 < best_dist: best_dist = d2; best = (tx2, ty2)
                            if best is None:
                                for b in getattr(self.world, "buildings", []):
                                    for tx2, ty2 in b.interior_tiles():
                                        d2 = abs(tx2-hx)+abs(ty2-hy)
                                        if d2 < best_dist: best_dist = d2; best = (tx2, ty2)
                            e.sleep_x, e.sleep_y = best if best else (hx, hy)
                        sx = getattr(e, "sleep_x", hx)
                        sy = getattr(e, "sleep_y", hy)
                        actual_dest_x, actual_dest_y = sx, sy
                    # Muovi verso destinazione notturna
                    sdist = abs(e.x - actual_dest_x) + abs(e.y - actual_dest_y)
                    if sdist > 0:
                        path = astar(e.x, e.y, actual_dest_x, actual_dest_y, passable, 300)
                        if path:
                            nx2, ny2 = path[0]
                            if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                e.x, e.y = nx2, ny2
                        else:
                            dx_ = 0 if actual_dest_x==e.x else (1 if actual_dest_x>e.x else -1)
                            dy_ = 0 if actual_dest_y==e.y else (1 if actual_dest_y>e.y else -1)
                            for nx2, ny2 in [(e.x+dx_,e.y+dy_),(e.x+dx_,e.y),(e.x,e.y+dy_)]:
                                if passable(nx2, ny2) and not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                    e.x, e.y = nx2, ny2; break
                else:
                    # Fase diurna: vai verso dest_x/dest_y se lontano, altrimenti wander
                    cdist = abs(e.x - dest_x) + abs(e.y - dest_y)
                    if cdist > dest_r:
                        path = astar(e.x, e.y, dest_x, dest_y, passable, 80)
                        _moved = False
                        if path:
                            nx2, ny2 = path[0]
                            if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                e.x, e.y = nx2, ny2; _moved = True
                        if not _moved:
                            # Jitter anti-deadlock: prova tile laterale libero
                            _jdirs = [(0,1),(0,-1),(1,0),(-1,0)]
                            random.shuffle(_jdirs)
                            for jx, jy in _jdirs:
                                nx2, ny2 = e.x+jx, e.y+jy
                                if passable(nx2, ny2) and not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                    e.x, e.y = nx2, ny2; break
                        # Azioni lavoro sul posto (outdoor, fase WORK, nell'area)
                        if phase == "WORK" and cdist <= dest_r:
                            if role == "taglialegna":
                                for fdx, fdy in [(0,1),(0,-1),(1,0),(-1,0)]:
                                    fx, fy = e.x+fdx, e.y+fdy
                                    if self.world.get_tile(fx,fy) == FOREST and random.random() < 0.04:
                                        self.world.overrides[(fx,fy)] = GRASS
                                        self.log(f"{e.name} abbatte un albero."); break
                            elif role == "minatore":
                                if random.random() < 0.02:
                                    self.log(f"{e.name} estrae della pietra.")
                            elif role == "cacciatore":
                                for other in self.entities:
                                    if other is e or not other.alive: continue
                                    if other.ai_type == "flee":
                                        od = abs(other.x-e.x)+abs(other.y-e.y)
                                        if od <= 1:
                                            other.health -= random.randint(3,8)
                                            if other.health <= 0:
                                                other.alive = False
                                                self.log(f"{e.name} ha cacciato un {other.name}.")
                                            break
                                        elif od <= 5:
                                            _pth = astar(e.x,e.y,other.x,other.y,passable,20)
                                            if _pth:
                                                nx2,ny2 = _pth[0]
                                                if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                                    e.x,e.y = nx2,ny2
                                            break
                    else:
                        # Nell'area: movimento casuale (bambino più vivace)
                        move_chance = 0.8 if role == "bambino" else (0.2 if role == "anziano" else 0.5)
                        if random.random() < move_chance:
                            _dirs = [(0,1),(0,-1),(1,0),(-1,0)]
                            random.shuffle(_dirs)
                            for dx_, dy_ in _dirs:
                                nx2, ny2 = e.x+dx_, e.y+dy_
                                if passable(nx2, ny2) and not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                    e.x, e.y = nx2, ny2; break
            elif e.ai_type == "guard":
                # Trova il punto di guardia assegnato
                px_ = getattr(e, "patrol_x", getattr(e, "home_x", e.x))
                py_ = getattr(e, "patrol_y", getattr(e, "home_y", e.y))
                is_gate_guard = getattr(e, "is_gate_guard", False)

                # Cerca nemici aggressivi nel raggio 8
                target = None
                for other in self.entities:
                    if other is e or not other.alive: continue
                    if other.ai_type in ("aggressive", "ghost"):
                        od = abs(other.x - e.x) + abs(other.y - e.y)
                        if od <= 12:
                            target = other; break

                if target:
                    td = abs(target.x - e.x) + abs(target.y - e.y)
                    if td == 1:
                        dmg = max(1, e.damage - getattr(target, "defense", 0))
                        target.health -= dmg
                        half_c = VIEW_COLS//2; half_r = VIEW_ROWS//2
                        sx = (target.x - p.x + half_c) * TILE_W
                        sy = (target.y - p.y + half_r) * TILE_H
                        self.floating_texts.append(FloatingText(
                            str(dmg), sx, sy, (255, 200, 50), 1.2))
                        if target.health <= 0:
                            target.alive = False
                    else:
                        # Guardie di porta: inseguono il nemico solo se entra
                        # nel raggio ravvicinato (3 tile), altrimenti restano ferme
                        if is_gate_guard and td > 3:
                            pass  # rimane ferma
                        else:
                            path = astar(e.x, e.y, target.x, target.y, passable, 20)
                            if path:
                                nx2, ny2 = path[0]
                                if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                    e.x, e.y = nx2, ny2
                else:
                    pdist = abs(e.x - px_) + abs(e.y - py_)
                    if pdist > 0:
                        path = astar(e.x, e.y, px_, py_, passable, 30)
                        if path:
                            nx2, ny2 = path[0]
                            if not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive):
                                e.x, e.y = nx2, ny2
                    elif not is_gate_guard and random.random() < 0.2:
                        dx_, dy_ = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
                        nx2, ny2 = e.x+dx_, e.y+dy_
                        if (passable(nx2, ny2)
                                and abs(nx2-px_)+abs(ny2-py_) <= 3
                                and not any(o.x==nx2 and o.y==ny2 for o in self.entities if o is not e and o.alive)):
                            e.x, e.y = nx2, ny2
        self.entities[:] = [e for e in self.entities if e.alive]

    # =========================================================================
    # RENDERING
    # =========================================================================
    def _draw_world(self):
        screen = self.screen; p = self.player
        half_c = VIEW_COLS//2; half_r = VIEW_ROWS//2
        for row in range(VIEW_ROWS):
            for col in range(VIEW_COLS):
                wx = p.x - half_c + col; wy = p.y - half_r + row
                t  = self.world.get_tile(wx, wy)
                wc = self.world.get_wall_char(wx, wy)
                ch = wc if wc else TILE_CHAR.get(t, "?")
                fg = TILE_COLOR.get(t, (200,200,200))
                bg = TILE_BG.get(t, (0,0,0))
                px_ = col*TILE_W; py_ = row*TILE_H
                pygame.draw.rect(screen, bg, (px_, py_, TILE_W, TILE_H))
                screen.blit(self.fonts["normal"].render(ch, True, fg), (px_, py_))
        # Lapidi
        for ts in self.tombstones:
            c_=ts["x"]-p.x+half_c; r_=ts["y"]-p.y+half_r
            if 0<=c_<VIEW_COLS and 0<=r_<VIEW_ROWS:
                screen.blit(self.fonts["bold"].render("R",True,(160,0,200)),(c_*TILE_W,r_*TILE_H))
        # Oggetti
        for item in self.items_on_ground:
            c_=item.x-p.x+half_c; r_=item.y-p.y+half_r
            if 0<=c_<VIEW_COLS and 0<=r_<VIEW_ROWS:
                screen.blit(self.fonts["bold"].render(ITEM_SYMBOL,True,
                    RARITY_COLORS.get(item.rarity,(255,255,255))),(c_*TILE_W,r_*TILE_H))
        # Entita
        for e in self.entities:
            c_=e.x-p.x+half_c; r_=e.y-p.y+half_r
            if 0<=c_<VIEW_COLS and 0<=r_<VIEW_ROWS:
                screen.blit(self.fonts["bold"].render(e.symbol,True,e.color),(c_*TILE_W,r_*TILE_H))
        # Giocatore
        screen.blit(self.fonts["bold"].render("@",True,(255,255,255)),(half_c*TILE_W,half_r*TILE_H))
        # Indicatore freccia direzionale nel tile adiacente
        _dmap = {(0,-1):"^",(0,1):"v",(1,0):">",(- 1,0):"<"}
        _dc = _dmap.get((getattr(self,"last_dx",0), getattr(self,"last_dy",1)), "v")
        _ax = (half_c + getattr(self,"last_dx",0)) * TILE_W
        _ay = (half_r + getattr(self,"last_dy",1)) * TILE_H
        _as = self.fonts["small"].render(_dc, True, (255, 255, 140))
        screen.blit(_as, (_ax + (TILE_W - _as.get_width())//2, _ay))
        # Floating texts
        # Bagliore magico intorno al player
        if self.magic_aura_timer > 0 and self.player:
            p2 = self.player
            half_c = VIEW_COLS//2; half_r = VIEW_ROWS//2
            px_s = (p2.x - p2.x + half_c) * TILE_W + TILE_W//2
            py_s = (p2.y - p2.y + half_r) * TILE_H + TILE_H//2
            aura_col = (100,200,255) if self.magic_aura_has_power else (180,180,180)
            # Intensità: max nei primi 0.5s, poi sfuma
            alpha = int(180 * min(1.0, self.magic_aura_timer / 0.8))
            radius = int(TILE_W * 2.5)
            aura_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*aura_col, alpha), (radius, radius), radius)
            pygame.draw.circle(aura_surf, (*aura_col, min(255, alpha+60)), (radius, radius), radius//2)
            screen.blit(aura_surf, (px_s - radius, py_s - radius))
        for ft in self.floating_texts: ft.draw(screen, self.fonts["small"])
        # Night overlay
        draw_night_overlay(self.screen, self.get_time_of_day())
        # Immunita fuga
        if self.flee_immunity > 0:
            s = self.fonts["small"].render(f"[ IMMUN. FUGA: {self.flee_immunity:.1f}s ]",True,(100,220,255))
            self.screen.blit(s, s.get_rect(centerx=(VIEW_COLS//2)*TILE_W, y=4))

    def render(self):
        self.screen.fill((5,5,15))
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

        elif s in (GameState.PLAYING, GameState.INVENTORY, GameState.MERCHANT,
                   GameState.DIALOG, GameState.QUEST_LOG, GameState.PAUSE):
            if self.player:
                pygame.draw.rect(self.screen,(10,12,10),pygame.Rect(PANEL_X,0,PANEL_W,VIEW_ROWS*TILE_H))
                self._draw_world()
                try:
                    draw_hud(self.screen, self.fonts, self.player,
                             self.world.get_biome_at(self.player.x, self.player.y),
                             self.time_str())
                except Exception as e:
                    try: draw_hud(self.screen, self.fonts, self.player, self.time_str(), self.messages)
                    except: pass
                if s == GameState.INVENTORY:
                    try: draw_inventory_panel(self.screen, self.fonts, self.player, self.inv_cursor)
                    except: draw_inventory(self.screen, self.fonts, self.player, self.inv_cursor)
                else:
                    try: draw_minimap(self.screen, self.fonts, self.minimap_surf, self.world, self.player)
                    except: pass
                    try: draw_equip_panel(self.screen, self.fonts, self.player)
                    except: pass
                _ov = lambda t, l, **kw: draw_overlay(self.screen, self.fonts, t, l, **kw)
                if s == GameState.PAUSE:
                    draw_pause(self.screen, self.fonts, self.seed, _ov)
                    if self.save_flash > 0:
                        flash_surf = self.fonts["bold"].render("✔ Partita salvata!", True, (80, 255, 120))
                        alpha = min(255, int(255 * (self.save_flash / 2.0)))
                        flash_surf.set_alpha(alpha)
                        # Overlay centrato: 700x480, posizionato al centro schermo
                        ow, oh = 700, 480
                        ox = (SCREEN_W - ow) // 2
                        oy = (SCREEN_H - oh) // 2
                        # Basso a destra dentro il riquadro, con margine 12px
                        fx = ox + ow - flash_surf.get_width() - 12
                        fy = oy + oh - flash_surf.get_height() - 12
                        self.screen.blit(flash_surf, (fx, fy))
                elif s == GameState.MERCHANT and self.merchant_ent:
                    draw_merchant(self.screen, self.fonts, self.player,
                                  self.merchant_ent, self.shop_cursor,
                                  self.sell_mode, self.sell_cursor)
                elif s == GameState.DIALOG and self.dialog_ent:
                    try: draw_dialog(self.screen, self.fonts, self.player, self.dialog_ent)
                    except: draw_dialog(self.screen, self.fonts, self.dialog_ent)
                elif s == GameState.QUEST_LOG:
                    draw_quest_log(self.screen, self.fonts, self.player)

        elif s == GameState.DEAD:
            if self.player:
                _ov = lambda t, l, **kw: draw_overlay(self.screen, self.fonts, t, l, **kw)
                draw_dead(self.screen, self.fonts, self.player, _ov)

        elif s == GameState.COMBAT:
            if self.combat_state:
                draw_combat(self.screen, self.fonts, self.combat_state)

        pygame.display.flip()

    # =========================================================================
    # INPUT
    # =========================================================================
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False; return

            elif self.state == GameState.SPLASH:
                self._handle_splash(event)
            elif self.state == GameState.MAIN_MENU:
                self._handle_main_menu(event)
            elif self.state == GameState.OPTIONS:
                self._handle_options(event)
            elif self.state == GameState.MENU_NAME:
                self._handle_menu_name(event)
            elif self.state in (GameState.INTRO_WELCOME,
                                GameState.INTRO_ADVENTURE,
                                GameState.INTRO_DESTINY):
                self._handle_intro(event)
            elif self.state == GameState.ESSENZA:
                self._handle_essenza(event)
            elif self.state == GameState.ESSENZA_CONFIRM:
                self._handle_essenza_confirm(event)

            elif self.state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if   k == pygame.K_e:      self.interact()
                    elif k == pygame.K_i:      self.state = GameState.INVENTORY; self.inv_cursor = 0
                    elif k == pygame.K_q:      self.state = GameState.QUEST_LOG
                    elif k == pygame.K_ESCAPE: self.state = GameState.PAUSE

            elif self.state == GameState.PAUSE:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s or event.unicode in ('s', 'S'):
                        if self.player: self.save_game()
                    elif event.key == pygame.K_q:      self.running = False
                    elif event.key == pygame.K_ESCAPE: self.state = GameState.PLAYING

            elif self.state == GameState.INVENTORY:
                if event.type == pygame.KEYDOWN:
                    k = event.key; inv = self.player.inventory
                    if   k == pygame.K_ESCAPE or k == pygame.K_i:
                        self.state = GameState.PLAYING
                    elif k in (pygame.K_UP, pygame.K_w):
                        self.inv_cursor = max(0, self.inv_cursor-1)
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        self.inv_cursor = min(max(0,len(inv)-1), self.inv_cursor+1)
                    elif k == pygame.K_RETURN and inv:
                        self.use_item(inv[min(self.inv_cursor, len(inv)-1)])
                        self.inv_cursor = min(self.inv_cursor, max(0,len(inv)-1))
                    elif k == pygame.K_d and inv:
                        item = inv[min(self.inv_cursor, len(inv)-1)]
                        item.x, item.y = self.player.x, self.player.y
                        self.items_on_ground.append(item)
                        inv.remove(item)
                        self.log(f"Buttato: {item.name}")
                        self.inv_cursor = min(self.inv_cursor, max(0,len(inv)-1))

            elif self.state == GameState.MERCHANT:
                if event.type == pygame.KEYDOWN:
                    k    = event.key
                    shop = self.merchant_ent.shop if self.merchant_ent else []
                    inv  = self.player.inventory
                    if k == pygame.K_TAB:
                        self.sell_mode = not self.sell_mode
                    elif k in (pygame.K_UP, pygame.K_w):
                        if self.sell_mode: self.sell_cursor = max(0, self.sell_cursor-1)
                        else:              self.shop_cursor = max(0, self.shop_cursor-1)
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        if self.sell_mode: self.sell_cursor = min(max(0,len(inv)-1), self.sell_cursor+1)
                        else:              self.shop_cursor = min(max(0,len(shop)-1), self.shop_cursor+1)
                    elif k == pygame.K_RETURN:
                        if self.sell_mode and inv:
                            item = inv[min(self.sell_cursor, len(inv)-1)]
                            price = max(1, item.value//2)
                            if self.merchant_ent.gold >= price:
                                self.player.gold += price
                                self.merchant_ent.gold -= price
                                self.merchant_ent.shop.append(item)
                                inv.remove(item)
                                self.log(f"Venduto {item.name} per {price}g")
                                self.sell_cursor = min(self.sell_cursor, max(0,len(inv)-1))
                            else: self.log("Il mercante non ha abbastanza oro!")
                        elif not self.sell_mode and shop:
                            item = shop[min(self.shop_cursor, len(shop)-1)]
                            if self.player.gold >= item.value:
                                self.player.gold -= item.value
                                self.merchant_ent.gold += item.value
                                self.player.inventory.append(item)
                                shop.remove(item)
                                self.log(f"Comprato {item.name} per {item.value}g")
                                self.shop_cursor = min(self.shop_cursor, max(0,len(shop)-1))
                            else: self.log("Oro insufficiente!")
                    elif k == pygame.K_ESCAPE:
                        self.sell_mode = False; self.state = GameState.PLAYING

            elif self.state == GameState.DIALOG:
                if event.type == pygame.KEYDOWN:
                    if getattr(self, "merchant_pending", False):
                        self.merchant_pending = False
                        self.state = GameState.MERCHANT
                    else:
                        self.state = GameState.PLAYING

            elif self.state == GameState.QUEST_LOG:
                if event.type == pygame.KEYDOWN:
                    self.state = GameState.PLAYING

            elif self.state == GameState.DEAD:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # Nuovo gioco: reinizializza tutto, niente opzione carica
                        self.__init__()
                        self.has_save = False   # la morte cancella il save
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

    # =========================================================================
    # LOOP PRINCIPALE
    # =========================================================================
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.tick += dt

            self.handle_events()

            # Combat update (animazioni, timer)
            if self.state == GameState.COMBAT and self.combat_state:
                self.combat_state.update(dt)
                cs = self.combat_state
                if cs.phase == CombatPhase.OUTRO and cs.outro_timer >= 0.8:
                    self._end_combat()
                elif cs.phase == CombatPhase.FLED:
                    self._end_combat()
                elif cs.phase == CombatPhase.DEFEAT:
                    self.handle_death()

            # Aggiornamenti gioco
            if self.state == GameState.PLAYING and self.player and self.player.alive:
                try:
                    self.player.update_age(dt)
                    self.update_entities(dt)
                except Exception as e:
                    self.log(f"[ERR] {e}")
                if self.player.health <= 0:
                    self.player.alive = False
                    if not self.player.death_cause: self.player.death_cause = "Causa sconosciuta"

            # Update bagliore magia
            if self.magic_aura_timer > 0:
                self.magic_aura_timer -= dt
                if self.magic_aura_timer <= 0:
                    self.magic_aura_timer = 0
                    p2 = self.player
                    if p2 and self.magic_aura_has_power:
                        self.log("Maestro di Magia: \"C'e' della magia in te!\"")
                    elif p2:
                        self.log("Maestro di Magia: \"Mi spiace... non c'e' potere in te.\"")
            if self.state == GameState.PLAYING and self.player and not self.player.alive:
                self.handle_death()

            # Floating texts
            for ft in self.floating_texts: ft.update(dt)
            self.floating_texts = [ft for ft in self.floating_texts if ft.alive]
            # Decrementa timer flash salvataggio
            if self.save_flash > 0:
                self.save_flash = max(0.0, self.save_flash - dt)

            # Spawn casuale oggetti
            if self.state == GameState.PLAYING and self.player and random.random() < 0.0005:
                p = self.player
                ix = p.x + random.randint(-15,15)
                iy = p.y + random.randint(-15,15)
                if self.world.is_passable(ix,iy):
                    drop = ITEM_GEN.generate_item()
                    drop.x, drop.y = ix, iy
                    self.items_on_ground.append(drop)

            # Movimento continuo tasto tenuto
            if self.state == GameState.PLAYING and self.player and self.player.alive:
                keys = pygame.key.get_pressed()
                dx = (1 if keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_LEFT] else 0)
                dy = (1 if keys[pygame.K_DOWN]  else 0) - (1 if keys[pygame.K_UP]   else 0)
                if dx or dy:
                    self.move_timer += dt
                    if self.move_timer >= MOVE_DELAY:
                        self.move_timer = 0.0
                        self.try_move(dx, dy)
                else:
                    self.move_timer = MOVE_DELAY

            self.render()

        pygame.quit()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
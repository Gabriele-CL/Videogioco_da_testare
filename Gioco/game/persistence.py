import json
import os

from core.enums import GameState
from entities.entity import Entity
from entities.player import Player
from items.item import Item
from world.world import World, WorldSettlements, WorldSpawner
from core.journal import Journal
from world.npc_behavior import NPCBehaviorEngine


class GamePersistenceMixin:
    def load_game(self):
        if not os.path.exists("savegame.json"):
            self.log("Nessun salvataggio trovato.")
            return
        try:
            with open("savegame.json", encoding="utf-8") as f:
                data = json.load(f)
            self.seed = data.get("seed", self.seed)
            self.game_time = data.get("game_time", 0.0)
            self.day_number = data.get("day_number", 1)
            self.tombstones = data.get("tombstones", [])
            self.messages = data.get("messages", [])
            self.journal = Journal.from_dict(data.get("journal", {}))
            self.journal_cursor = 0
            self.journal_tab = 0
            self.player = Player.from_dict(data["player"])
            self.entities = [Entity.from_dict(e) for e in data.get("entities", [])]
            self.items_on_ground = [Item.from_dict(i) for i in data.get("items_on_ground", [])]
            self.world = World(self.seed, self.entities, bootstrap_static=False)
            chunk_data = data.get("world", data.get("chunks", {}))
            self.world.load_dict(chunk_data, self.seed)
            self.world.bootstrap_static_landmarks()
            self.npc_engine = NPCBehaviorEngine()
            self.spawner = WorldSpawner(self.world)
            self.spawner.populated = set(self.world.chunks.keys())
            self.settlements = WorldSettlements(self.world)
            sdata = data.get("settlements", {})
            try:
                self.settlements.evaluated = set(tuple(x) for x in sdata.get("evaluated", []))
                self.settlements.centers = [tuple(x) for x in sdata.get("centers", [])]
                self.settlements.generated_villages = set(tuple(x) for x in sdata.get("generated_villages", []))
            except Exception:
                self.settlements.evaluated = set()
                self.settlements.centers = []
                self.settlements.generated_villages = set()
            pdata = data.get("poi", {})
            try:
                self.spawner.generated_pois = set(tuple(x) for x in pdata.get("generated_pois", []))
                self.spawner.poi_markers = {
                    tuple(m.get("slot", [])): {k: v for k, v in m.items() if k != "slot"}
                    for m in pdata.get("poi_markers", [])
                    if m.get("slot")
                }
            except Exception:
                self.spawner.generated_pois = set()
                self.spawner.poi_markers = {}
            if not self.settlements.generated_villages:
                self.settlements.bootstrap_all()
            if not self.spawner.generated_pois:
                self.spawner.bootstrap_all()
            self._preload_and_spawn(self.player.x, self.player.y)
            self.state = GameState.PLAYING
            self.log(f"Bentornato, {self.player.name}!")
        except KeyError as e:
            self.log(f"Salvataggio corrotto (chiave mancante: {e})")
            print(f"[LOAD ERROR - KeyError] {e}")
            self.state = GameState.MAIN_MENU
        except Exception as e:
            self.log(f"Errore caricamento: {e}")
            print(f"[LOAD ERROR] {type(e).__name__}: {e}")
            self.state = GameState.MAIN_MENU

    def save_game(self):
        try:
            data = {
                "player": self.player.to_dict(),
                "seed": self.seed,
                "game_time": self.game_time,
                "day_number": self.day_number,
                "entities": [e.to_dict() for e in self.entities],
                "world": self.world.to_dict(),
                "items_on_ground": [i.to_dict() for i in self.items_on_ground],
                "tombstones": self.tombstones,
                "messages": self.messages,
                "journal": self.journal.to_dict() if getattr(self, "journal", None) else {},
                "settlements": {
                    "evaluated": [list(x) for x in getattr(self.settlements, "evaluated", set())],
                    "centers": [list(x) for x in getattr(self.settlements, "centers", [])],
                    "generated_villages": [list(x) for x in getattr(self.settlements, "generated_villages", set())],
                },
                "poi": {
                    "generated_pois": [list(x) for x in getattr(self.spawner, "generated_pois", set())],
                    "poi_markers": [
                        {"slot": list(slot), **marker}
                        for slot, marker in getattr(self.spawner, "poi_markers", {}).items()
                    ],
                },
            }
            with open("savegame.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.has_save = True
            self.save_flash = 2.0
            self.log("Partita salvata.")
            self.journal_add("Partita salvata.", "misc")
            print("[SAVE OK] Partita salvata con successo")
        except Exception as e:
            self.log(f"Errore salvataggio: {e}")
            print(f"[SAVE ERROR] {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()

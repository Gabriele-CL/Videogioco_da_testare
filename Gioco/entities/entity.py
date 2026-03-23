# =============================================================================
# entities/entity.py
# BUG FIX #5: bog_witch ai_type "ghost" → "aggressive"
# =============================================================================
import random
from typing import List, Optional
from items.item import Item, ITEM_GEN
from entities.quest import Quest, make_random_quest

NPC_NAMES = ["Tormund","Lyra","Brom","Seera","Dwin","Aldric","Mira","Gruk","Elara","Finn"]

NPC_DIALOGUES = [
    "Beware the forest at night!",
    "Ancient ruins lie to the east.",
    "Gold is life, friend.",
    "The wolves grow bolder each season.",
    "Stay on the road if you value your life.",
    "Strange lights in the swamp last night...",
    "They say a dragon sleeps under the mountain.",
]

class Entity:
    def __init__(self, name, symbol, x, y, health, damage, speed, ai_type, color=(0,255,255)):
        self.name       = name
        self.symbol     = symbol
        self.x          = x
        self.y          = y
        self.health     = health
        self.max_health = health
        self.damage     = damage
        self.speed      = speed
        self.ai_type    = ai_type
        self.color      = color
        self.alive      = True
        self.last_move  = 0.0
        self.dialogue   = random.choice(NPC_DIALOGUES)
        self.inventory: List[Item] = []
        self.shop: List[Item] = [ITEM_GEN.generate_item() for _ in range(5)]
        self.has_quest  = (ai_type == "npc") and (random.random() < 0.6)
        self.quest: Optional[Quest] = make_random_quest() if self.has_quest else None
        self.gold       = 0
        self.defense    = 0
        self.level      = 1
        self.home_x     = x
        self.home_y     = y
        self.home_radius = 8
        # Ruolo NPC e destinazione di lavoro
        self.npc_role   = ""
        self.work_x     = x
        self.work_y     = y
        self.work_radius = 4
        self.tavern_x   = x
        self.tavern_y   = y

    def populate_shop(self):
        """Popola lo shop in base all'ai_type e al livello."""
        level = getattr(self, "level", 1)
        rarity = ("common"   if level < 3 else
                  "uncommon" if level < 5 else
                  "rare"     if level < 7 else
                  "epic"     if level < 10 else "legendary")
        shop_size = max(3, level // 2 + 2)
        if self.ai_type == "innkeeper":
            self.shop = [ITEM_GEN.generate_innkeeper_item(rarity)
                         for _ in range(min(shop_size, 5))]
        else:
            self.shop = [ITEM_GEN.generate_merchant_item(rarity)
                         for _ in range(shop_size)]

    def to_dict(self) -> dict:
        """Serializza per il salvataggio JSON."""
        shop_data = []
        for item in getattr(self, "shop", []):
            try:
                shop_data.append(item.to_dict())
            except Exception:
                pass
        return {
            "name":      self.name,
            "symbol":    self.symbol,
            "x":         self.x,
            "y":         self.y,
            "health":    getattr(self, "health", 20),
            "max_health":getattr(self, "max_health", 20),
            "damage":    getattr(self, "damage", 0),
            "speed":     getattr(self, "speed", 0.5),
            "ai_type":   getattr(self, "ai_type", "npc"),
            "color":     list(getattr(self, "color", (0,255,255))),
            "alive":     getattr(self, "alive", True),
            "dialogue":  getattr(self, "dialogue", "..."),
            "level":     getattr(self, "level", 1),
            "defense":   getattr(self, "defense", 0),
            "gold":      getattr(self, "gold", 0),
            "shop":      shop_data,
            "npc_role":  getattr(self, "npc_role", ""),
            "work_x":    getattr(self, "work_x", self.x),
            "work_y":    getattr(self, "work_y", self.y),
            "tavern_x":  getattr(self, "tavern_x", self.x),
            "tavern_y":  getattr(self, "tavern_y", self.y),
        }

    @staticmethod
    def from_dict(d: dict) -> "Entity":
        e = Entity(
            d["name"], d["symbol"], d["x"], d["y"],
            d.get("health", 20), d.get("damage", 0), d.get("speed", 0.5),
            d.get("ai_type", "npc"), tuple(d.get("color", [0,255,255]))
        )
        e.max_health = d.get("max_health", e.health)
        e.alive      = d.get("alive", True)
        e.dialogue   = d.get("dialogue", "...")
        e.level      = d.get("level", 1)
        e.defense    = d.get("defense", 0)
        e.gold       = d.get("gold", 0)
        e.npc_role   = d.get("npc_role", "")
        e.work_x     = d.get("work_x", e.x)
        e.work_y     = d.get("work_y", e.y)
        e.tavern_x   = d.get("tavern_x", e.x)
        e.tavern_y   = d.get("tavern_y", e.y)
        saved_shop = d.get("shop", [])
        if saved_shop:
            e.shop = [Item.from_dict(i) for i in saved_shop if i]
        elif e.ai_type in ("merchant", "innkeeper"):
            e.populate_shop()
        else:
            e.shop = []
        return e


def make_entity(etype: str, x: int, y: int) -> "Entity":
    if etype == "wolf":
        e = Entity("Wolf", "w", x, y, 22, 8, 1.0, "aggressive", (220, 60, 60))
        e.level = random.randint(1, 5); return e
    elif etype == "goblin":
        e = Entity("Goblin", "g", x, y, 28, 7, 0.9, "aggressive", (60, 200, 60))
        e.level = random.randint(1, 6); return e
    elif etype == "ghost":
        e = Entity("Ghost", "G", x, y, 32, 12, 0.8, "ghost", (180, 180, 255))
        e.level = random.randint(2, 8); return e
    elif etype == "goblin_shaman":
        e = Entity("Goblin Shaman", "S", x, y, 40, 14, 0.7, "aggressive", (120, 220, 80))
        e.level = random.randint(4, 10); return e
    elif etype == "troll":
        e = Entity("Troll", "T", x, y, 90, 20, 0.6, "aggressive", (160, 120, 80))
        e.level = random.randint(8, 14); return e
    elif etype == "bog_witch":
        # FIX #5: era "ghost" (attraversava i muri), corretta in "aggressive"
        e = Entity("Bog Witch", "B", x, y, 70, 18, 0.7, "aggressive", (100, 180, 120))
        e.level = random.randint(8, 14); return e
    elif etype == "deer":
        return Entity("Deer",   "d", x, y, 15, 0, 1.2, "flee", (180, 140, 80))
    elif etype == "rabbit":
        return Entity("Rabbit", "r", x, y,  8, 0, 1.4, "flee", (220, 200, 180))
    elif etype == "bear":
        e = Entity("Bear", "b", x, y, 55, 14, 0.8, "aggressive", (140, 90, 50))
        e.level = random.randint(3, 8); return e
    elif etype == "fox":
        return Entity("Fox",  "f", x, y, 12, 0, 1.3, "flee", (200, 120, 40))
    elif etype == "boar":
        e = Entity("Boar", "o", x, y, 35, 10, 0.9, "aggressive", (160, 100, 60))
        e.level = random.randint(1, 4); return e
    elif etype == "merchant":
        e = Entity("Merchant", "M", x, y, 50, 2, 0.3, "merchant", (0, 220, 220))
        e.level = random.randint(1, 10)
        e.gold = random.randint(100, 400)
        e.populate_shop(); return e
    else:
        return Entity(random.choice(NPC_NAMES), "$", x, y,
                      40, 4, 0.5, "npc", (0, 255, 200))


# Spawn per bioma: (tipo, peso_giorno, peso_notte)
BIOME_SPAWNS = {
    "Grassland": [("wolf",3,5),("deer",6,2),("rabbit",8,1),("fox",4,2),("goblin",2,3),("ghost",0,4)],
    "Forest":    [("wolf",4,7),("deer",5,1),("rabbit",5,1),("bear",3,4),("boar",4,3),
                  ("goblin",3,4),("goblin_shaman",1,2),("ghost",0,5)],
    "Mountain":  [("wolf",3,6),("bear",4,5),("boar",2,2),("goblin",3,4),("troll",1,2),("ghost",0,3)],
    "Swamp":     [("ghost",2,8),("goblin",4,5),("goblin_shaman",2,4),("bog_witch",1,2),("fox",2,1)],
    "Road":      [("goblin",3,5),("wolf",2,4),("deer",3,1),("rabbit",4,1),("ghost",0,3)],
    "River":     [("deer",5,2),("fox",3,2),("rabbit",5,1),("ghost",0,4)],
}

# =============================================================================
# item.py — Struttura dati Item e generatore procedurale ItemGenerator.
# =============================================================================

import random
from dataclasses import dataclass
from typing import Dict


@dataclass
class Item:
    """
    Un oggetto del gioco: arma, armatura, pozione o materiale.
    Può stare nell'inventario, a terra o nel negozio del mercante.
    """
    name:        str    # nome (es. "Blessed Sword of Fire")
    item_type:   str    # "weapon" | "armor" | "potion" | "material"
    symbol:      str    # carattere ASCII sulla mappa
    rarity:      str    # "common" | "uncommon" | "rare" | "epic" | "legendary"
    stats:       Dict   # statistiche (es. {"damage": 12, "crit_chance": 0.1})
    description: str    # testo descrittivo
    value:       int    # prezzo in oro
    x:           int = -1   # posizione X a terra (-1 = in inventario/negozio)
    y:           int = -1   # posizione Y a terra

    def to_dict(self) -> dict:
        """Serializza in dizionario per il salvataggio JSON."""
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict) -> "Item":
        """Ricostruisce un Item da dizionario caricato dal JSON."""
        return Item(**d)


class ItemGenerator:
    """
    Genera oggetti casuali con nomi, statistiche e rarità procedurali.
    Rarità più alta = statistiche più alte = valore più alto.
    """

    PREFIXES  = ["Rusty","Enchanted","Shadow","Holy","Ancient",
                 "Broken","Gleaming","Cursed","Blessed","Void"]
    SUFFIXES  = ["of Fire","of the Forest","of Shadows","of Kings",
                 "of Thunder","of Ice","of the Lost"]
    W_BASES   = ["Sword","Axe","Dagger","Bow","Staff","Spear","Mace","Scythe"]
    A_BASES   = ["Leather Armor","Chainmail","Plate","Robe","Buckler","Brigandine"]
    P_BASES   = ["Health Potion","Stamina Potion","Elixir","Tonic","Remedy"]
    M_BASES   = ["Iron Ore","Crystal","Bone","Herb","Feather","Scale"]

    # ── Tipi oste ─────────────────────────────────────────────────────────────
    FOOD_BASES       = ["Roasted Meat","Bread Loaf","Mushroom Stew","Honey Cake","Dried Fish"]
    POISON_BASES     = ["Venom Extract","Nightshade Brew","Spider Toxin","Wyvern Bile","Miasma Flask"]
    DRINK_BASES      = ["Mead","Ale","Herbal Tea","Fire Spirits","Mystic Wine"]
    INGREDIENT_BASES = ["Dried Herb","Wild Mushroom","Bear Fat","River Root",
                        "Night Flower","Venomous Fang","Honey","Ash Bark"]

    RARITIES  = ["common","uncommon","rare","epic","legendary"]
    R_WEIGHTS = [55, 25, 12, 6, 2]   # comune molto più frequente di leggendario

    # Moltiplicatore statistiche per rarità
    RARITY_SCALE = {"common":1.0,"uncommon":1.3,"rare":1.7,"epic":2.2,"legendary":3.0}

    # Categorie che l'oste raccoglie/vende
    INNKEEPER_TYPES = ("potion", "food", "poison", "drink", "ingredient")

    def generate_item(self, rarity: str = None, item_type: str = None) -> "Item":
        """
        Genera un Item casuale. Se rarity o item_type sono None,
        vengono scelti con pesi. La rarità scala tutte le statistiche.
        """
        if rarity is None:
            rarity = random.choices(self.RARITIES, weights=self.R_WEIGHTS)[0]
        if item_type is None:
            item_type = random.choices(
                ["weapon", "armor", "legs", "helmet", "shield", "boots", "potion", "material"],
            weights=[22, 18, 12, 10, 10, 8, 12, 8]
            )[0]

        scale      = self.RARITY_SCALE[rarity]
        use_suffix = rarity in ("rare","epic","legendary")

        if item_type == "weapon":
            base   = random.choice(self.W_BASES); symbol = "/"
            dmg    = int(random.randint(5,15) * scale)
            stats  = {"damage": dmg,
                      "speed":  round(random.uniform(0.8,1.4)*scale, 2),
                      "crit_chance": min(round(random.uniform(0.03,0.10)*scale, 3), 0.5)}
            val    = int(10*scale + dmg*2)

        elif item_type == "armor":
            base   = random.choice(self.A_BASES); symbol = "["
            df     = int(random.randint(3,10) * scale)
            stats  = {"defense": df, "weight": round(random.uniform(1,5)/scale, 2)}
            val    = int(8*scale + df*3)

        elif item_type == "potion":
            base   = random.choice(self.P_BASES); symbol = "!"
            heal   = int(random.randint(15,40) * scale)
            stats  = {"heal": heal, "duration": 0}
            val    = int(5*scale + heal)

        elif item_type == "food":
            base   = random.choice(self.FOOD_BASES); symbol = "%"
            heal   = int(random.randint(5, 20) * scale)
            stats  = {"heal": heal, "buff": "satiety", "duration": int(30 * scale)}
            val    = int(4*scale + heal)

        elif item_type == "poison":
            base   = random.choice(self.POISON_BASES); symbol = "x"
            dmg    = int(random.randint(5, 25) * scale)
            stats  = {"poison_dmg": dmg, "duration": int(10 * scale)}
            val    = int(6*scale + dmg)

        elif item_type == "drink":
            base   = random.choice(self.DRINK_BASES); symbol = "u"
            st_heal = int(random.randint(10, 30) * scale)
            stats  = {"stamina_heal": st_heal, "duration": int(20 * scale)}
            val    = int(4*scale + st_heal)

        elif item_type == "ingredient":
            base   = random.choice(self.INGREDIENT_BASES); symbol = "i"
            stats  = {"ingredient_value": int(random.randint(1,8)*scale), "craft_type": "consumable"}
            val    = int(3*scale)

        else:   # material
            base   = random.choice(self.M_BASES); symbol = "o"
            stats  = {"material_value": int(random.randint(1,10)*scale)}
            val    = int(3*scale)

        prefix = random.choice(self.PREFIXES)
        name   = f"{prefix} {base}"
        if use_suffix:
            name += f" {random.choice(self.SUFFIXES)}"

        return Item(
            name=name, item_type=item_type, symbol=symbol,
            rarity=rarity, stats=stats,
            description=f"A {rarity} {item_type}. Quality: {rarity.capitalize()}",
            value=val
        )

    def generate_innkeeper_item(self, rarity: str = None) -> "Item":
        """Genera un oggetto da oste: pozioni, cibo, veleni, bevande, ingredienti."""
        item_type = random.choices(
            ["potion", "food", "poison", "drink", "ingredient"],
            weights=[30, 25, 15, 20, 10]
        )[0]
        return self.generate_item(rarity=rarity, item_type=item_type)

    def generate_merchant_item(self, rarity: str = None) -> "Item":
        """Genera un oggetto da mercante: armi, armature, materiali, pozioni."""
        item_type = random.choices(
            ["weapon", "armor", "legs", "helmet", "shield", "boots", "potion", "material"],
            weights=[25, 20, 12, 10, 10, 8, 10, 5]
        )[0]
        return self.generate_item(rarity=rarity, item_type=item_type)


# Istanza globale: creata una volta, importata ovunque serve
ITEM_GEN = ItemGenerator()
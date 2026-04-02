import random
from typing import List, Optional
from core.enums import LifeStage
from items.item import Item

# Secondi di game_time reali necessari per invecchiare di 1 anno, per fase vita
# 1 anno = 1 giorno di gioco (20 min reali). Uniforme per tutte le fasi.
SECONDS_PER_YEAR = {
    LifeStage.CHILD: 1200.0,
    LifeStage.TEEN:  1200.0,
    LifeStage.ADULT: 1200.0,
    LifeStage.ELDER: 1200.0,
}


class Player:
    def __init__(self, name):
        self.name       = name
        self.x = 0
        self.y = 0
        self.angle = 0.0

        self.age        = 5
        self.life_stage = LifeStage.CHILD
        self._age_accum = 0.0   # secondi accumulati verso il prossimo anno

        self.max_health  = 30
        self.health      = 30
        self.max_stamina = 100
        self.stamina     = 100

        self.gold  = 0
        self.xp    = 0
        self.level = 1
        self.kills = 0

        self.inventory: List[Item] = []

        # Tutti gli slot equipaggiamento esplicitamente inizializzati
        self.equipped_weapon: Optional[Item] = None
        self.equipped_armor:  Optional[Item] = None
        self.equipped_head:   Optional[Item] = None
        self.equipped_legs:   Optional[Item] = None
        self.equipped_shield: Optional[Item] = None
        self.equipped_boots:  Optional[Item] = None

        self.alive       = True
        self.death_cause = ""

        # ── Sistema età massima (nascosto al giocatore) ───────────────────────
        self.max_age: int    = random.randint(40, 100)
        self.peaceful_days: int = 0
        # Morte neonatale (0.5%)
        if random.random() < 0.005:
            self.alive       = False
            self.death_cause = "Nato senza vita"
        self.inv_cursor  = 0

        self.magic_factor   = random.randint(0, 1)
        self.magic_revealed = False

        # ESSENZA — attributi core, modificabili durante la partita
        self.essenza = {
            "Forza":        1,
            "Agilità":      1,
            "Intelligenza": 1,
            "Resistenza":   1,
            "Carisma":      1,
            "Fortuna":      1,
            "Percezione":   1,
        }

        # Contatori azioni per crescita tramite uso
        self._action_counts: dict = {}

        # Accumulo interno (compatibilità save/load): usato da alcune build per heal over time
        # Deve esistere per evitare errori in to_dict() anche se la feature non è attiva.
        self._last_heal_accum: float = 0.0



    # ── Livelli ───────────────────────────────────────────────────────────────
    def xp_to_next(self) -> int:
        return self.level * 60

    def add_xp(self, amount: int) -> list:
        """Aggiunge XP con bonus Intelligenza; ritorna lista livelli raggiunti."""
        bonus = 1.0 + (self.essenza.get("Intelligenza", 1) - 1) * 0.02
        self.xp += int(amount * bonus)
        leveled = []
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            self.max_health = int(self.max_health * 1.10)
            self.health     = min(self.health + 15, self.max_health)
            leveled.append(self.level)
        return leveled

    # ── Invecchiamento agganciato al game_time ────────────────────────────────
    def update_age(self, dt: float) -> str:
        """
        dt = delta time in secondi reali.
        Ritorna il valore della nuova fase vita se è appena cambiata, '' altrimenti.
        """
        secs = SECONDS_PER_YEAR[self.life_stage]
        self._age_accum += dt
        new_stage = ""
        if self._age_accum >= secs:
            self._age_accum -= secs
            self.age += 1
            new_stage = self._update_life_stage()

        return new_stage

    def _update_life_stage(self) -> str:
        """Aggiorna la fase vita. Ritorna il nome della nuova fase se è cambiata, '' altrimenti."""
        old = self.life_stage
        if   self.age < 13: self.life_stage = LifeStage.CHILD
        elif self.age < 18: self.life_stage = LifeStage.TEEN
        elif self.age < 61: self.life_stage = LifeStage.ADULT
        else:               self.life_stage = LifeStage.ELDER

        if self.life_stage == old:
            return ""

        stage_hp = {
            LifeStage.CHILD: 30, LifeStage.TEEN: 70,
            LifeStage.ADULT: 100, LifeStage.ELDER: 60,
        }
        res_bonus = 1.0 + (self.essenza.get("Resistenza", 1) - 1) * 0.03
        self.max_health = int(stage_hp[self.life_stage] * res_bonus)
        self.health = min(self.health, self.max_health)

        # Crescita ESSENZA da evento "cambio fase vita"
        # Ogni transizione regala +1 a un attributo diverso
        _stage_essenza = {
            LifeStage.TEEN:  "Agilità",       # adolescente: diventi più scattante
            LifeStage.ADULT: "Forza",          # adulto: raggiungi la piena potenza
            LifeStage.ELDER: "Intelligenza",   # anziano: la saggezza cresce
        }
        attr = _stage_essenza.get(self.life_stage)
        if attr:
            self.grant_essenza_event(attr)

        return self.life_stage.value

    # ── Statistiche combattimento ─────────────────────────────────────────────
    @property
    def dmg_mult(self) -> float:
        stage_m = {
            LifeStage.CHILD: 0.5, LifeStage.TEEN: 0.8,
            LifeStage.ADULT: 1.0, LifeStage.ELDER: 0.7,
        }
        forza_bonus = 1.0 + (self.essenza.get("Forza", 1) - 1) * 0.02
        return stage_m[self.life_stage] * forza_bonus

    def attack_damage(self) -> int:
        base = self.equipped_weapon.stats.get("damage", 5) if self.equipped_weapon else 5
        return max(1, int(base * self.dmg_mult))

    def attack_damage_with_crit(self) -> int:
        base        = self.equipped_weapon.stats.get("damage", 5) if self.equipped_weapon else 5
        crit_chance = self.equipped_weapon.stats.get("crit_chance", 0.05) if self.equipped_weapon else 0.05
        crit_chance += (self.essenza.get("Agilità", 1) - 1) * 0.02

        dmg = max(1, int(base * self.dmg_mult))
        if random.random() < crit_chance:
            dmg *= 2
        return dmg

    def defense(self) -> int:
        base = sum(
            getattr(self, slot).stats.get("defense", 0)
            for slot in ("equipped_armor", "equipped_head", "equipped_legs",
                         "equipped_shield", "equipped_boots")
            if getattr(self, slot) is not None
        )

        base += (self.essenza.get("Resistenza", 1) - 1)
        return base

    # ── Bonus ESSENZA esposti come metodi ─────────────────────────────────────
    # ── Sistema età massima ───────────────────────────────────────────────────
    def modify_max_age(self, delta: int, reason: str = ""):
        """Modifica max_age. Non può scendere sotto age+1 né salire oltre 150."""
        self.max_age = max(self.age + 1, min(150, self.max_age + delta))

    def grant_immortality(self):
        self.max_age = 9999

    def check_old_age(self) -> bool:
        """Chiamato ogni anno. Ritorna True se il personaggio muore di vecchiaia."""
        if self.age >= self.max_age:
            self.alive       = False
            self.death_cause = f"Vecchiaia ({self.age} anni)"
            return True
        return False

    def on_combat_kill(self):
        """Ogni 10 kill: max_age -1 (stile aggressivo)."""
        if self.kills > 0 and self.kills % 10 == 0:
            self.modify_max_age(-1, "stile di vita aggressivo")

    def on_severe_wound(self):
        """HP < 10%: max_age da -1 a -3."""
        self.modify_max_age(-random.randint(1, 3), "ferita grave")

    def on_peaceful_day(self):
        """Ogni 30 giorni pacifici: max_age +1."""
        self.peaceful_days += 1
        if self.peaceful_days % 30 == 0:
            self.modify_max_age(+1, "vita pacifica")

    def loot_bonus(self) -> float:
        """Moltiplicatore drop chance. Es: Fortuna 5 → 1.08"""
        return 1.0 + (self.essenza.get("Fortuna", 1) - 1) * 0.02

    def flee_bonus(self) -> int:
        """Bonus al dado fuga (d36). Es: Fortuna 5 → +4"""
        return self.essenza.get("Fortuna", 1) - 1

    def merchant_discount(self) -> float:
        """Sconto acquisti. Es: Carisma 5 → 4%"""
        return (self.essenza.get("Carisma", 1) - 1) * 0.01

    def aggro_reduction(self) -> float:
        """Riduzione raggio aggro nemici. Es: Percezione 5 → 0.08"""
        return (self.essenza.get("Percezione", 1) - 1) * 0.02

    # ── Crescita ESSENZA tramite azioni ───────────────────────────────────────
    _ACTION_MAP = {
        "attacchi":     ("Forza",        25),
        "schivate":     ("Agilità",      10),   # fuga riuscita
        "abilita":      ("Intelligenza", 20),
        "danni_subiti": ("Resistenza",   30),
        "dialoghi":     ("Carisma",      15),
        "loot":         ("Fortuna",      20),
        "esplorazione": ("Percezione",   50),
    }
    # Tetto totale: impedisce di portare tutto al massimo
    # Con 7 attributi × min 1 = 7 base; cap 42 = spazio per ~35 punti extra
    _ESSENZA_TOTAL_CAP = 42

    def register_action(self, action_type: str) -> Optional[str]:
        """
        Registra un'azione. Se raggiunge la soglia, tenta di incrementare
        l'attributo collegato. Applica resistenza crescente se l'attributo
        è già molto sopra la media degli altri.
        Ritorna il nome dell'attributo cresciuto, o None.
        """
        if action_type not in self._ACTION_MAP:
            return None
        attr, threshold = self._ACTION_MAP[action_type]
        self._action_counts[action_type] = self._action_counts.get(action_type, 0) + 1
        if self._action_counts[action_type] < threshold:
            return None

        if sum(self.essenza.values()) >= self._ESSENZA_TOTAL_CAP:
            return None

        # Resistenza crescente: se l'attributo è 3+ sopra la media, solo 30% chance
        avg   = sum(self.essenza.values()) / len(self.essenza)
        val   = self.essenza.get(attr, 1)
        if val - avg >= 3 and random.random() > 0.30:
            return None

        self._action_counts[action_type] = 0
        self.essenza[attr] = min(val + 1, 10)
        return attr

    def grant_essenza_event(self, attr: str, amount: int = 1) -> bool:
        """
        Crescita da evento speciale (maestro, cambio fase vita, ecc.).
        Rispetta il cap totale ma ignora la resistenza progressiva.
        """
        if sum(self.essenza.values()) >= self._ESSENZA_TOTAL_CAP:
            return False
        old = self.essenza.get(attr, 1)
        if old >= 10:
            return False
        self.essenza[attr] = old + amount
        return True

    # ── Serializzazione ───────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        def _item(i): return i.to_dict() if i else None
        return {
            "name":       self.name,
            "x": self.x, "y": self.y, "angle": self.angle,
            "age":         self.age,
            "life_stage":  self.life_stage.value,
            "_age_accum":  self._age_accum,
            "max_health":  self.max_health,
            "health":      self.health,
            "max_stamina": self.max_stamina,
            "stamina":     self.stamina,
            "gold":        self.gold,
            "xp":          self.xp,
            "level":       self.level,
            "kills":       self.kills,
            "inventory":        [i.to_dict() for i in self.inventory],
            "equipped_weapon":  _item(self.equipped_weapon),
            "equipped_armor":   _item(self.equipped_armor),
            "equipped_head":    _item(self.equipped_head),
            "equipped_legs":    _item(self.equipped_legs),
            "equipped_shield":  _item(self.equipped_shield),
            "equipped_boots":   _item(self.equipped_boots),
            "magic_factor":     self.magic_factor,
            "magic_revealed":   self.magic_revealed,
            "essenza":          self.essenza,
            "_action_counts":   self._action_counts,
            "_last_heal_accum": getattr(self, "_last_heal_accum", 0.0),
            "max_age":          getattr(self, "max_age", random.randint(40, 100)),
            "peaceful_days":    getattr(self, "peaceful_days", 0),
        }

    @staticmethod
    def from_dict(d: dict) -> "Player":
        def _item(k): return Item.from_dict(d[k]) if d.get(k) else None
        p = Player.__new__(Player)
        p.name       = d["name"]
        p.x, p.y     = d["x"], d["y"]
        p.angle      = d.get("angle", 0.0)
        p.age        = d["age"]
        p.life_stage = LifeStage(d["life_stage"])
        p._age_accum = d.get("_age_accum", 0.0)
        p.max_health = d["max_health"]
        p.health     = d["health"]
        p.max_stamina= d["max_stamina"]
        p.stamina    = d["stamina"]
        p.gold       = d["gold"]
        p.xp         = d.get("xp", 0)
        p.level      = d.get("level", 1)
        p.kills      = d.get("kills", 0)
        p.max_age        = d.get("max_age", random.randint(40, 100))
        p.peaceful_days  = d.get("peaceful_days", 0)
        p.inventory        = [Item.from_dict(i) for i in d.get("inventory", [])]
        p.equipped_weapon  = _item("equipped_weapon")
        p.equipped_armor   = _item("equipped_armor")
        p.equipped_head    = _item("equipped_head")
        p.equipped_legs    = _item("equipped_legs")
        p.equipped_shield  = _item("equipped_shield")
        p.equipped_boots   = _item("equipped_boots")
        p.magic_factor     = d.get("magic_factor", random.randint(0, 1))
        p.magic_revealed   = d.get("magic_revealed", False)
        p.essenza          = d.get("essenza", {a: 1 for a in
                             ["Forza","Agilità","Intelligenza","Resistenza",
                              "Carisma","Fortuna","Percezione"]})
        p._action_counts   = d.get("_action_counts", {})
        p._last_heal_accum = d.get("_last_heal_accum", 0.0)
        p.alive       = True
        p.death_cause = ""
        p.inv_cursor  = 0
        return p

import time
import random
from typing import List, Optional
from core.enums import LifeStage, CharClass
from items.item import Item
from entities.quest import Quest

class Player:
    def __init__(self, name, char_class):
        self.name = name
        self.char_class = char_class
        self.x = 0
        self.y = 0
        self.angle = 0.0
        self.age = 5
        self.life_stage = LifeStage.CHILD
        self.max_health = 30
        self.health = 30
        self.max_stamina = 100
        self.stamina = 100
        self.gold = 0
        self.xp = 0
        self.level = 1
        self.kills = 0
        self.inventory = []
        self.equipped_weapon = None
        self.equipped_armor = None
        self.active_quests = []
        self.completed_quests = []
        self.birth_time = time.time()
        self.last_age_tick = time.time()
        self.last_heal = time.time()
        self.alive = True
        self.death_cause = ''
        self.inv_cursor = 0
        # Fattore magico: 0 = nessun potere, 1 = potere magico latente
        # Nascosto al giocatore, scopribile solo tramite l'insegnante di magia
        self.magic_factor = random.randint(0, 1)
        self.magic_revealed = False   # True dopo il test con l'insegnante
        self._apply_class()

    def _apply_class(self):
        c = self.char_class
        if c == CharClass.WARRIOR:
            self.max_health = int(self.max_health * 1.30)
        elif c == CharClass.ROGUE:
            self.max_stamina = int(self.max_stamina * 1.30)
            self.max_health = int(self.max_health * 0.80)
        elif c == CharClass.MAGE:
            self.max_health = int(self.max_health * 0.70)
        elif c == CharClass.RANGER:
            self.max_health = int(self.max_health * 0.90)
        elif c == CharClass.PALADIN:
            self.max_health = int(self.max_health * 1.20)
        self.health = self.max_health
        self.stamina = self.max_stamina

    def xp_to_next(self):
        return self.level * 60

    def add_xp(self, amount):
        self.xp += amount
        leveled = []
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            self.max_health = int(self.max_health * 1.10)
            self.health = min(self.health + 15, self.max_health)
            leveled.append(self.level)
        return leveled

    def update_age(self):
        now = time.time()
        if now - self.last_age_tick >= 60:
            self.age += 1
            self.last_age_tick = now
            self._update_life_stage()
        if self.char_class == CharClass.PALADIN and now - self.last_heal >= 30:
            self.health = min(self.max_health, self.health + 5)
            self.last_heal = now

    def _update_life_stage(self):
        old = self.life_stage
        if self.age < 13: self.life_stage = LifeStage.CHILD
        elif self.age < 18: self.life_stage = LifeStage.TEEN
        elif self.age < 61: self.life_stage = LifeStage.ADULT
        else: self.life_stage = LifeStage.ELDER
        if self.life_stage != old:
            stage_hp = {LifeStage.CHILD:30, LifeStage.TEEN:70, LifeStage.ADULT:100, LifeStage.ELDER:60}
            class_mods = {CharClass.WARRIOR:1.30, CharClass.ROGUE:0.80, CharClass.MAGE:0.70, CharClass.RANGER:0.90, CharClass.PALADIN:1.20}
            self.max_health = int(stage_hp[self.life_stage] * class_mods.get(self.char_class, 1.0))
            self.health = min(self.health, self.max_health)

    @property
    def dmg_mult(self):
        sm = {LifeStage.CHILD:0.5, LifeStage.TEEN:0.8, LifeStage.ADULT:1.0, LifeStage.ELDER:0.7}
        cm = {CharClass.WARRIOR:1.20, CharClass.ROGUE:1.00, CharClass.MAGE:0.80, CharClass.RANGER:1.00, CharClass.PALADIN:1.00}
        return sm[self.life_stage] * cm.get(self.char_class, 1.0)

    def attack_damage(self):
        base = self.equipped_weapon.stats.get('damage', 5) if self.equipped_weapon else 5
        return int(base * self.dmg_mult)
    
    

    def attack_damage_with_crit(self):
        base        = self.equipped_weapon.stats.get('damage', 5) if self.equipped_weapon else 5
        crit_chance = self.equipped_weapon.stats.get('crit_chance', 0.05) if self.equipped_weapon else 0.05
        if self.char_class == CharClass.ROGUE:
            crit_chance *= 1.5
        dmg = int(base * self.dmg_mult)
        if random.random() < crit_chance:
            dmg *= 2
        return dmg




    def defense(self):
        base = self.equipped_armor.stats.get('defense', 0) if self.equipped_armor else 0
        if self.char_class == CharClass.PALADIN:
            base = int(base * 1.10) + 2
        return base

    def to_dict(self):
        return {
            'name': self.name, 'char_class': self.char_class.value,
            'x': self.x, 'y': self.y, 'angle': self.angle,
            'age': self.age, 'life_stage': self.life_stage.value,
            'max_health': self.max_health, 'health': self.health,
            'stamina': self.stamina, 'max_stamina': self.max_stamina,
            'gold': self.gold, 'xp': self.xp, 'level': self.level, 'kills': self.kills,
            'inventory': [i.to_dict() for i in self.inventory],
            'equipped_weapon': self.equipped_weapon.to_dict() if self.equipped_weapon else None,
            'equipped_armor': self.equipped_armor.to_dict() if self.equipped_armor else None,
            'active_quests': [q.to_dict() for q in self.active_quests],
            'completed_quests': self.completed_quests,
            'magic_factor':    getattr(self, 'magic_factor', 0),
            'magic_revealed':  getattr(self, 'magic_revealed', False),
            'birth_time': self.birth_time,
            'last_age_tick': self.last_age_tick,
        }

    @staticmethod
    def from_dict(d):
        p = Player.__new__(Player)
        p.name = d['name']
        p.char_class = CharClass(d['char_class'])
        p.x, p.y = d['x'], d['y']
        p.angle = d.get('angle', 0.0)
        p.age = d['age']
        p.life_stage = LifeStage(d['life_stage'])
        p.max_health = d['max_health']
        p.health = d['health']
        p.max_stamina = d['max_stamina']
        p.stamina = d['stamina']
        p.gold = d['gold']
        p.xp = d.get('xp', 0)
        p.level = d.get('level', 1)
        p.kills = d.get('kills', 0)
        p.inventory = [Item.from_dict(i) for i in d['inventory']]
        p.equipped_weapon = Item.from_dict(d['equipped_weapon']) if d['equipped_weapon'] else None
        p.equipped_armor = Item.from_dict(d['equipped_armor']) if d['equipped_armor'] else None
        p.active_quests = [Quest.from_dict(q) for q in d.get('active_quests', [])]
        p.completed_quests = d.get('completed_quests', [])
        p.magic_factor   = d.get('magic_factor', random.randint(0,1))
        p.magic_revealed = d.get('magic_revealed', False)
        p.birth_time = d.get('birth_time', time.time())
        p.last_age_tick = d.get('last_age_tick', time.time())
        p.last_heal = time.time()
        p.alive = True
        p.death_cause = ''
        p.inv_cursor = 0
        return p
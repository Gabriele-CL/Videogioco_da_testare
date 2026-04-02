from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark:
    kind: str
    name: str
    x: int
    y: int
    radius: int
    stable: bool = True


class WorldLayout:
    """
    Layer di layout stabile sopra la generazione chunk-based.

    Tiene traccia dei grandi centri urbani, delle aree protette e dei POI
    che devono restare coerenti tra le run.
    """

    WORLD_EXTENT = 1200

    CAPITALS = (
        Landmark("capital", "Eldoria", 0, 0, 48, True),
        Landmark("capital", "Northgate", -720, -420, 44, True),
        Landmark("capital", "Sunspire", 760, -360, 44, True),
        Landmark("capital", "Stonewatch", -660, 420, 44, True),
        Landmark("capital", "Riverhollow", 680, 420, 44, True),
        Landmark("capital", "Frostholm", -900, 120, 42, True),
        Landmark("capital", "Goldmere", 900, 120, 42, True),
    )

    def __init__(self, seed: int):
        self.seed = seed
        self.capitals = list(self.CAPITALS)
        self.village_slots = self.choose_village_slots()
        self.wild_slots = self.choose_wild_slots()
        self.world_extent = self.WORLD_EXTENT

    def city_centers(self):
        return [(c.x, c.y) for c in self.capitals]

    def is_capital_zone(self, wx: int, wy: int) -> bool:
        for c in self.capitals:
            dx = wx - c.x
            dy = wy - c.y
            if dx * dx + dy * dy <= c.radius * c.radius:
                return True
        return False

    def safe_distance_from_capitals(self, wx: int, wy: int, margin: int = 0) -> bool:
        for c in self.capitals:
            dx = wx - c.x
            dy = wy - c.y
            if dx * dx + dy * dy <= (c.radius + margin) ** 2:
                return False
        return True

    def choose_village_slots(self):
        """
        Slot semi-stabili per villaggi piccoli.
        Si spostano leggermente ad ogni run, ma restano legati alle aree generali.
        """
        import random

        rng = random.Random(self.seed ^ 0x5A17)
        offsets_a = [(-160, -90), (150, -70)]
        offsets_b = [(-130, 120), (120, 110)]
        villages = []
        for idx, cap in enumerate(self.capitals):
            offsets = offsets_a if idx % 2 == 0 else offsets_b
            for ox, oy in offsets:
                jx = rng.randint(-26, 26)
                jy = rng.randint(-26, 26)
                x = cap.x + ox + jx
                y = cap.y + oy + jy
                villages.append((f"village-{idx}-{ox}-{oy}", x, y))
        rng.shuffle(villages)
        return villages[:14]

    def choose_wild_slots(self):
        """
        Slot di massima per accampamenti e marker selvatici.
        """
        import random

        rng = random.Random(self.seed ^ 0xD00D)
        slots = []
        for cap in self.capitals:
            for dx, dy in [(-220, -150), (210, -120), (-200, 160), (180, 190), (-140, 40), (140, 40)]:
                x = cap.x + dx + rng.randint(-36, 36)
                y = cap.y + dy + rng.randint(-36, 36)
                slots.append((x, y))
        rng.shuffle(slots)
        return slots[:18]

from entities.entity import Entity
from world.npc_behavior import NPCBehaviorEngine


class DummyWorld:
    def __init__(self):
        self.buildings = []
        self.layout = None

    def is_safe_zone(self, wx, wy):
        return False


def make_npc(role: str, x: int = 0, y: int = 0):
    e = Entity.__new__(Entity)
    e.x = x
    e.y = y
    e.name = role.title()
    e.symbol = "p"
    e.color = (255, 255, 255)
    e.ai_type = "wander"
    e.alive = True
    e.home_x = 0
    e.home_y = 0
    e.home_radius = 4
    e.work_x = 30
    e.work_y = 0
    e.work_radius = 1
    e.tavern_x = 0
    e.tavern_y = 0
    e.npc_role = role
    e.behavior_seed = 1234
    e.behavior_state = "idle"
    e.social_bias = 0.5
    e.outdoor_dest_set = False
    return e


def test_npc_moves_toward_work_and_returns_home():
    world = DummyWorld()
    engine = NPCBehaviorEngine()
    npc = make_npc("contadino")
    entities = [npc]
    passable = lambda x, y: True

    engine.update(npc, world, entities, passable, player=None, hour=10.0, tod="DAY")
    assert npc.x != 0 or npc.y != 0
    assert abs(npc.x - npc.work_x) + abs(npc.y - npc.work_y) < 30

    npc.x = 30
    npc.y = 0
    before_home = abs(npc.x - npc.home_x) + abs(npc.y - npc.home_y)
    engine.update(npc, world, entities, passable, player=None, hour=23.0, tod="NIGHT")
    after_home = abs(npc.x - npc.home_x) + abs(npc.y - npc.home_y)
    assert after_home < before_home

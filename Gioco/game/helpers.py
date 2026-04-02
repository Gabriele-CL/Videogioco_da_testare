from core.constants import FLOOR
from world.buildings import COUNTER


ITEM_SYMBOL = "\xa7"


def merchant_open_gate(bottega, world):
    gx, gy = bottega.counter_gate_x, bottega.counter_gate_y
    world.overrides[(gx, gy)] = FLOOR
    world.wall_chars[(gx, gy)] = "."
    bottega.counter_gate_open = True


def merchant_close_gate(bottega, world):
    gx, gy = bottega.counter_gate_x, bottega.counter_gate_y
    world.overrides[(gx, gy)] = COUNTER
    world.wall_chars[(gx, gy)] = "|"
    bottega.counter_gate_open = False


def merchant_blocked(nx, ny, entities, me):
    return any(o.x == nx and o.y == ny for o in entities if o is not me and o.alive)

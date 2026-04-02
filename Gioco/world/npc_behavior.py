# =============================================================================
# world/npc_behavior.py - Motore leggero per routine NPC
# =============================================================================
import random
from dataclasses import dataclass

from core.utils import astar


OUTDOOR_WORK_ROLES = {"contadino", "cacciatore", "taglialegna", "minatore"}
SOCIAL_ROLES = {"popolano", "anziano", "bambino", "nobile", "amministratore", "servitore"}
WORK_ROLES = {"contadino", "fabbro", "prete", "guaritore", "ins_magia", "cacciatore", "taglialegna", "minatore", "amministratore", "servitore"}


@dataclass(frozen=True)
class NPCProfile:
    role: str
    home_radius: int
    work_radius: int
    social_radius: int
    roam_chance: float


ROLE_PROFILES = {
    "merchant": NPCProfile("merchant", 6, 4, 4, 0.10),
    "oste": NPCProfile("oste", 6, 5, 4, 0.12),
    "popolano": NPCProfile("popolano", 7, 7, 5, 0.35),
    "contadino": NPCProfile("contadino", 8, 16, 5, 0.15),
    "fabbro": NPCProfile("fabbro", 6, 6, 4, 0.10),
    "bambino": NPCProfile("bambino", 4, 4, 4, 0.55),
    "anziano": NPCProfile("anziano", 5, 5, 4, 0.18),
    "prete": NPCProfile("prete", 5, 5, 4, 0.08),
    "guaritore": NPCProfile("guaritore", 5, 5, 4, 0.08),
    "ins_magia": NPCProfile("ins_magia", 5, 5, 4, 0.08),
    "cacciatore": NPCProfile("cacciatore", 7, 18, 4, 0.12),
    "taglialegna": NPCProfile("taglialegna", 7, 18, 4, 0.12),
    "minatore": NPCProfile("minatore", 7, 18, 4, 0.10),
    "guardia_civ": NPCProfile("guardia_civ", 6, 12, 4, 0.10),
    "guardia": NPCProfile("guardia", 6, 12, 4, 0.08),
    "amministratore": NPCProfile("amministratore", 6, 7, 4, 0.10),
    "nobile": NPCProfile("nobile", 6, 6, 5, 0.18),
    "servitore": NPCProfile("servitore", 4, 10, 3, 0.08),
    "re": NPCProfile("re", 0, 0, 0, 0.0),
    "regina": NPCProfile("regina", 0, 0, 0, 0.0),
}


def _is_occupied(entities, x, y, self_entity=None):
    for other in entities:
        if other is self_entity or not getattr(other, "alive", False):
            continue
        if other.x == x and other.y == y:
            return True
    return False


def _pick_anchor(buildings, btypes, fallback):
    if not buildings:
        return fallback
    for b in buildings:
        if b.btype in btypes:
            return (b.wx + b.w // 2, b.wy + b.h // 2)
    return fallback


class NPCBehaviorEngine:
    @staticmethod
    def configure_npc(entity, buildings):
        role = getattr(entity, "npc_role", "") or getattr(entity, "ai_type", "npc")
        profile = ROLE_PROFILES.get(role)
        entity.behavior_profile = role
        entity.behavior_state = getattr(entity, "behavior_state", "idle") or "idle"
        entity.social_bias = getattr(entity, "social_bias", random.random())

        if profile:
            entity.home_radius = profile.home_radius
            entity.work_radius = profile.work_radius
        if role in OUTDOOR_WORK_ROLES:
            entity.outdoor_dest_set = False

        palace = next((b for b in buildings if getattr(b, "btype", "") == "palace"), None)
        if palace:
            entity.palace_x = palace.wx + palace.w // 2
            entity.palace_y = palace.wy + palace.h // 2
        else:
            entity.palace_x = getattr(entity, "home_x", entity.x)
            entity.palace_y = getattr(entity, "home_y", entity.y)

        if role in {"amministratore", "nobile", "servitore"} and palace:
            entity.work_x = entity.palace_x
            entity.work_y = entity.palace_y
            entity.tavern_x = entity.palace_x
            entity.tavern_y = entity.palace_y
        elif role in {"re", "regina"} and palace:
            entity.home_x = entity.palace_x
            entity.home_y = entity.palace_y
            entity.work_x = entity.palace_x
            entity.work_y = entity.palace_y
            entity.tavern_x = entity.palace_x
            entity.tavern_y = entity.palace_y
            entity.home_radius = 0
            entity.work_radius = 0

        if role == "servitore" and palace:
            entity.sleep_x = entity.sleep_x or (palace.wx + 2)
            entity.sleep_y = entity.sleep_y or (palace.wy + 11)

        if role in SOCIAL_ROLES:
            entity.social_anchor = (getattr(entity, "tavern_x", entity.x), getattr(entity, "tavern_y", entity.y))

    @staticmethod
    def _phase_for(role: str, hour: float, tod: str) -> str:
        if role in {"re", "regina"}:
            return "PALACE"
        if tod == "NIGHT":
            return "HOME"
        if 5 <= hour < 8:
            return "COMMUTE"
        if 8 <= hour < 12:
            return "WORK"
        if 12 <= hour < 18:
            return "WORK" if role not in {"bambino", "anziano"} else "WANDER"
        if 18 <= hour < 21:
            return "SOCIAL"
        return "HOME"

    @staticmethod
    def _destination(entity, world, role: str, phase: str):
        if phase == "PALACE":
            return (getattr(entity, "palace_x", entity.home_x), getattr(entity, "palace_y", entity.home_y), 4)
        if phase == "SOCIAL":
            return (getattr(entity, "tavern_x", entity.home_x), getattr(entity, "tavern_y", entity.home_y), 5)
        if phase == "WORK":
            if role in OUTDOOR_WORK_ROLES:
                if getattr(entity, "work_x", None) is not None and getattr(entity, "work_y", None) is not None:
                    return (entity.work_x, entity.work_y, max(8, getattr(entity, "work_radius", 12)))
                return (entity.home_x, entity.home_y, getattr(entity, "home_radius", 8))
            return (getattr(entity, "work_x", entity.home_x), getattr(entity, "work_y", entity.home_y), getattr(entity, "work_radius", 6))
        if phase == "COMMUTE":
            if role in OUTDOOR_WORK_ROLES:
                return (getattr(entity, "work_x", entity.home_x), getattr(entity, "work_y", entity.home_y), getattr(entity, "work_radius", 8))
            return (getattr(entity, "work_x", entity.home_x), getattr(entity, "work_y", entity.home_y), getattr(entity, "work_radius", 6))
        if phase == "WANDER":
            return (getattr(entity, "home_x", entity.x), getattr(entity, "home_y", entity.y), getattr(entity, "home_radius", 6))
        return (getattr(entity, "home_x", entity.x), getattr(entity, "home_y", entity.y), getattr(entity, "home_radius", 6))

    @staticmethod
    def _find_threat(entity, entities):
        for other in entities:
            if other is entity or not getattr(other, "alive", False):
                continue
            if getattr(other, "ai_type", "") in ("aggressive", "ghost"):
                dist = abs(other.x - entity.x) + abs(other.y - entity.y)
                if dist <= 5:
                    return other
        return None

    @staticmethod
    def _flee(entity, threat, passable, entities):
        dx = entity.x - threat.x
        dy = entity.y - threat.y
        mx = (1 if dx > 0 else -1) if dx != 0 else random.choice([-1, 1])
        my = (1 if dy > 0 else -1) if dy != 0 else random.choice([-1, 1])
        candidates = [(entity.x + mx, entity.y), (entity.x, entity.y + my), (entity.x + mx, entity.y + my)]
        random.shuffle(candidates)
        for nx, ny in candidates:
            if passable(nx, ny) and not _is_occupied(entities, nx, ny, entity):
                entity.x, entity.y = nx, ny
                return True
        return False

    @staticmethod
    def _move_towards(entity, dest_x, dest_y, passable, entities, limit=60):
        path = astar(entity.x, entity.y, dest_x, dest_y, passable, limit)
        if path:
            nx, ny = path[0]
            if not _is_occupied(entities, nx, ny, entity):
                entity.x, entity.y = nx, ny
                return True
        return False

    @staticmethod
    def update(entity, world, entities, passable, player, hour, tod, dt=0.0):
        role = getattr(entity, "npc_role", "") or getattr(entity, "ai_type", "npc")
        if role in {"merchant", "oste", "re", "regina"}:
            return

        profile = ROLE_PROFILES.get(role, ROLE_PROFILES["popolano"])
        phase = NPCBehaviorEngine._phase_for(role, hour, tod)
        entity.behavior_state = phase.lower()

        threat = NPCBehaviorEngine._find_threat(entity, entities)
        if threat:
            if NPCBehaviorEngine._flee(entity, threat, passable, entities):
                return

        dest_x, dest_y, dest_r = NPCBehaviorEngine._destination(entity, world, role, phase)
        dist = abs(entity.x - dest_x) + abs(entity.y - dest_y)

        if role in OUTDOOR_WORK_ROLES and phase in ("WORK", "COMMUTE"):
            if getattr(entity, "outdoor_dest_set", False) is False:
                entity.outdoor_dest_set = True
            if phase == "COMMUTE" or dist > dest_r:
                if NPCBehaviorEngine._move_towards(entity, dest_x, dest_y, passable, entities, 120):
                    return

        if phase in ("HOME", "PALACE"):
            if dist > dest_r:
                if NPCBehaviorEngine._move_towards(entity, dest_x, dest_y, passable, entities, 120):
                    return

        if phase == "SOCIAL" and role in SOCIAL_ROLES:
            if dist > dest_r:
                if NPCBehaviorEngine._move_towards(entity, dest_x, dest_y, passable, entities, 90):
                    return

        if phase == "WORK" and dist > dest_r:
            if NPCBehaviorEngine._move_towards(entity, dest_x, dest_y, passable, entities, 90):
                return

        rng = random.Random(getattr(entity, "behavior_seed", 0) ^ int(hour * 100) ^ int(entity.x * 131 + entity.y * 17))
        move_chance = profile.roam_chance
        if phase == "SOCIAL":
            move_chance += 0.15
        elif phase == "HOME":
            move_chance *= 0.5
        elif role in {"anziano"}:
            move_chance *= 0.6
        elif role in {"bambino"}:
            move_chance += 0.15

        if rng.random() < move_chance:
            dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            rng.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = entity.x + dx, entity.y + dy
                if passable(nx, ny) and not _is_occupied(entities, nx, ny, entity):
                    entity.x, entity.y = nx, ny
                    break

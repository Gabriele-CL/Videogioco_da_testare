from entities.player import Player
from entities.quest import Quest
from items.item import Item


def test_player_to_dict_from_dict_roundtrip_keeps_core_state():
    p = Player("Tester")
    p.x, p.y, p.angle = 12, -5, 1.5
    p.gold, p.xp, p.level, p.kills = 42, 99, 4, 7
    p._last_heal_accum = 3.25
    p.essenza["Forza"] = 4
    p.essenza["Fortuna"] = 3

    sword = Item("Sword", "weapon", "/", "common", {"damage": 10}, "Simple sword", 25)
    armor = Item("Armor", "armor", "[", "uncommon", {"defense": 4}, "Simple armor", 30)
    p.inventory.extend([sword, armor])
    p.equipped_weapon = sword
    p.equipped_armor = armor

    q = Quest("q_test", "Test Quest", "Do things", "NPC", "kill", "Wolf", 2, 10, 20)
    p.active_quests.append(q)
    p.completed_quests.append("q_old")

    data = p.to_dict()
    restored = Player.from_dict(data)

    assert restored.name == p.name
    assert (restored.x, restored.y) == (p.x, p.y)
    assert restored.angle == p.angle
    assert restored.gold == p.gold
    assert restored.xp == p.xp
    assert restored.level == p.level
    assert restored.kills == p.kills
    assert restored.essenza == p.essenza
    assert restored._last_heal_accum == p._last_heal_accum
    assert len(restored.inventory) == 2
    assert restored.equipped_weapon is not None
    assert restored.equipped_weapon.name == "Sword"
    assert restored.equipped_armor is not None
    assert restored.equipped_armor.name == "Armor"
    assert len(restored.active_quests) == 1
    assert restored.active_quests[0].qid == "q_test"
    assert restored.completed_quests == ["q_old"]

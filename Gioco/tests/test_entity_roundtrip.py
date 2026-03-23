from entities.entity import Entity


def test_guard_roundtrip_keeps_patrol_and_gate_flags():
    g = Entity("Guardia", "G", 5, 6, 50, 12, 0.8, "guard", (200, 200, 60))
    g.npc_role = "guardia"
    g.home_x, g.home_y, g.home_radius = 10, 11, 7
    g.patrol_x, g.patrol_y = 13, 14
    g.is_gate_guard = True
    g.sleep_x, g.sleep_y = 8, 9
    g.outdoor_dest_set = True

    data = g.to_dict()
    restored = Entity.from_dict(data)

    assert restored.ai_type == "guard"
    assert restored.npc_role == "guardia"
    assert (restored.home_x, restored.home_y, restored.home_radius) == (10, 11, 7)
    assert (restored.patrol_x, restored.patrol_y) == (13, 14)
    assert restored.is_gate_guard is True
    assert (restored.sleep_x, restored.sleep_y) == (8, 9)
    assert restored.outdoor_dest_set is True

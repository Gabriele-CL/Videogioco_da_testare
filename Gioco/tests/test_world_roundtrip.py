from world.world import World, WorldSettlements


def test_world_to_dict_load_dict_roundtrip_preserves_maps():
    w = World(12345, [])
    w.preload_around(0, 0, radius=1)
    w.overrides[(1, 2)] = 99
    w.wall_chars[(1, 2)] = "+"
    w.overrides[(3, 4)] = 2
    w.wall_chars[(3, 4)] = "|"

    data = w.to_dict()

    w2 = World(12345, [])
    w2.load_dict(data, 12345)

    assert w2.chunks == w.chunks
    assert w2.overrides == w.overrides
    assert w2.wall_chars == w.wall_chars


def test_rebuild_starting_town_runtime_sets_runtime_structures_only():
    w = World(42, [])
    original_overrides = dict(w.overrides)
    original_wall_chars = dict(w.wall_chars)

    w.rebuild_starting_town_runtime(0, 0)

    assert w.city_wall is not None
    assert len(w.buildings) > 0
    # Must not mutate persisted tile maps when rebuilding runtime-only objects.
    assert w.overrides == original_overrides
    assert w.wall_chars == original_wall_chars


def test_world_settlements_state_conversion_matches_save_load_format():
    w = World(77, [])
    s = WorldSettlements(w)
    s.evaluated = {(0, 0), (1, -1)}
    s.centers = [(16, 16), (-32, 48)]

    # Same shape used in main.py save_game()
    payload = {
        "evaluated": [list(x) for x in s.evaluated],
        "centers": [list(x) for x in s.centers],
    }

    s2 = WorldSettlements(w)
    s2.evaluated = set(tuple(x) for x in payload.get("evaluated", []))
    s2.centers = [tuple(x) for x in payload.get("centers", [])]

    assert s2.evaluated == s.evaluated
    assert s2.centers == s.centers

# ── Mission Data ──────────────────────────────────────────────────────────────
# All level-specific constants extracted from main.py

# Стены для каждой миссии: {(x, y): "brick" | "steel"}
MISSION_WALLS: dict[int, dict[tuple[int, int], str]] = {
    1: {(4, 1): "brick", (4, 2): "brick", (4, 3): "steel", (7, 4): "brick", (7, 5): "steel"},
    2: {(3, 4): "brick", (4, 4): "brick", (5, 4): "steel", (7, 2): "steel", (7, 3): "brick"},
    3: {(3, 3): "steel", (4, 3): "brick", (5, 3): "brick", (6, 3): "steel", (8, 4): "brick", (8, 5): "steel"},
    4: {(3, 2): "brick", (4, 2): "brick", (5, 4): "steel", (6, 4): "steel", (8, 5): "brick"},
    5: {(4, 2): "brick", (4, 3): "brick", (4, 4): "steel", (6, 4): "steel", (7, 4): "brick", (8, 4): "brick"},
    6: {(3, 2): "steel", (3, 3): "steel", (5, 4): "brick", (6, 4): "brick", (7, 4): "steel", (8, 4): "steel", (6, 2): "brick"},
    7: {(3, 2): "brick", (3, 3): "steel", (5, 1): "brick", (5, 2): "brick", (6, 5): "steel", (7, 5): "brick"},
    8: {(2, 3): "steel", (3, 3): "brick", (4, 3): "brick", (6, 2): "steel", (6, 3): "brick", (6, 4): "brick", (8, 5): "steel"},
    9: {(2, 2): "brick", (3, 2): "steel", (4, 2): "brick", (5, 4): "brick", (6, 4): "steel", (7, 4): "brick", (4, 6): "steel", (7, 6): "brick"},
}

# Враги для каждой миссии: (x, y, hp)
MISSION_ENEMIES: dict[int, list[tuple[int, int, int]]] = {
    1: [(8, 5, 100)], 2: [(8, 1, 100)], 3: [(7, 5, 100)],
    4: [(7, 2, 100)], 5: [(6, 2, 100)], 6: [(8, 2, 150)],
    7: [(8, 1, 100), (8, 6, 100)],
    8: [(7, 1, 100), (8, 6, 150)],
    9: [(8, 1, 100), (8, 6, 100), (5, 1, 150)],
}

FULL_MISSIONS = {
    1: {
        "title": "Прямой маршрут", "combat": False, "goal": {"x": 1, "y": 2},
        "enemy": {"x": 8, "y": 5, "skin": "red"},
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[1].items()]
    },
    2: {
        "title": "Первый поворот", "combat": False, "goal": {"x": 5, "y": 2},
        "enemy": {"x": 8, "y": 1, "skin": "dark"},
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[2].items()]
    },
    3: {
        "title": "Маршрут командира", "combat": False, "goal": {"x": 8, "y": 1},
        "enemy": {"x": 7, "y": 5, "skin": "red"},
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[3].items()]
    },
    4: {
        "title": "Первый бой", "combat": True, "goal": {"x": 7, "y": 1},
        "enemy": {"x": 7, "y": 2, "skin": "red"},
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[4].items()]
    },
    5: {
        "title": "Огневой коридор", "combat": True, "goal": {"x": 8, "y": 2},
        "enemy": {"x": 6, "y": 2, "skin": "dark"},
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[5].items()]
    },
    6: {
        "title": "Стальная крепость", "combat": True, "goal": {"x": 8, "y": 1},
        "enemy": {"x": 8, "y": 2, "skin": "red"},
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[6].items()]
    },
    7: {"title": "Двойная угроза", "combat": True, "goal": {"x": 8, "y": 3},
        "enemy": {"x": 8, "y": 1, "skin": "red"},
        "enemies": [{"x": 8, "y": 1, "skin": "red"}, {"x": 8, "y": 6, "skin": "green"}],
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[7].items()]},
    8: {"title": "Перекрёстный огонь", "combat": True, "goal": {"x": 8, "y": 3},
        "enemy": {"x": 7, "y": 1, "skin": "dark"},
        "enemies": [{"x": 7, "y": 1, "skin": "dark"}, {"x": 8, "y": 6, "skin": "sand"}],
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[8].items()]},
    9: {"title": "Тройная осада", "combat": True, "goal": {"x": 8, "y": 3},
        "enemy": {"x": 8, "y": 1, "skin": "red"},
        "enemies": [{"x": 8, "y": 1, "skin": "red"}, {"x": 8, "y": 6, "skin": "green"}, {"x": 5, "y": 1, "skin": "heavy"}],
        "walls": [{"x": x, "y": y, "type": t} for (x, y), t in MISSION_WALLS[9].items()]}
}

# Стены для PvP-арены (неразрушаемые)
PVP_WALLS: set[tuple[int, int]] = {
    (3, 1), (3, 2), (6, 1), (6, 2),
    (4, 3), (5, 3), (4, 4), (5, 4),
    (3, 5), (3, 6), (6, 5), (6, 6),
}

PVP_MAPS: dict[int, set[tuple[int, int]]] = {
    1: set(PVP_WALLS),
    2: {(2, 1), (2, 2), (2, 3), (7, 4), (7, 5), (7, 6), (4, 2), (5, 2), (4, 5), (5, 5)},
    3: {(3, 1), (4, 1), (5, 2), (6, 2), (2, 4), (3, 4), (6, 5), (7, 5), (4, 6), (5, 6)},
}

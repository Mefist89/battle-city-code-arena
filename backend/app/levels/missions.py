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
}

# Враги для каждой миссии: (x, y, hp)
MISSION_ENEMIES: dict[int, tuple[int, int, int]] = {
    1: (8, 5, 100),
    2: (8, 1, 100),
    3: (7, 5, 100),
    4: (7, 2, 100),
    5: (6, 2, 100),
    6: (8, 2, 150),
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
    }
}

# Стены для PvP-арены (неразрушаемые)
PVP_WALLS: set[tuple[int, int]] = {
    (3, 1), (3, 2), (6, 1), (6, 2),
    (4, 3), (5, 3), (4, 4), (5, 4),
    (3, 5), (3, 6), (6, 5), (6, 6),
}

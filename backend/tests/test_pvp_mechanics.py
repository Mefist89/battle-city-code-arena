import unittest

from app.simulator.pvp_engine import resolve_pvp_tick


def make_room() -> dict:
    return {
        "tanks": {
            "1": {"x": 1, "y": 6, "direction": "UP", "hp": 100},
            "2": {"x": 8, "y": 1, "direction": "DOWN", "hp": 100},
        },
        "walls": {},
        "winner": None,
    }


class PvpSimultaneousMechanicsTests(unittest.TestCase):
    def test_brick_is_destroyed_but_steel_survives(self):
        brick_room = make_room()
        brick_room["tanks"]["1"].update({"x": 1, "y": 1, "direction": "RIGHT"})
        brick_room["walls"] = {(2, 1): "brick"}

        brick_events = resolve_pvp_tick(brick_room, {"1": "fire", "2": "scan"})

        self.assertNotIn((2, 1), brick_room["walls"])
        self.assertTrue(brick_events[0]["wall"]["destroyed"])

        steel_room = make_room()
        steel_room["tanks"]["1"].update({"x": 1, "y": 1, "direction": "RIGHT"})
        steel_room["walls"] = {(2, 1): "steel"}

        steel_events = resolve_pvp_tick(steel_room, {"1": "fire", "2": "scan"})

        self.assertEqual(steel_room["walls"][(2, 1)], "steel")
        self.assertFalse(steel_events[0]["wall"]["destroyed"])

    def test_perpendicular_projectiles_collide_without_damage(self):
        room = make_room()
        room["tanks"]["1"].update({"x": 1, "y": 3, "direction": "RIGHT"})
        room["tanks"]["2"].update({"x": 3, "y": 1, "direction": "DOWN"})

        events = resolve_pvp_tick(room, {"1": "fire", "2": "fire"})

        self.assertEqual(room["tanks"]["1"]["hp"], 100)
        self.assertEqual(room["tanks"]["2"]["hp"], 100)
        self.assertTrue(events[0]["collision"])
        self.assertTrue(events[1]["collision"])

    def test_destroyed_second_player_still_completes_same_tick_shot(self):
        room = make_room()
        room["tanks"]["1"].update({"x": 1, "y": 3, "direction": "RIGHT"})
        room["tanks"]["2"].update({"x": 3, "y": 3, "direction": "UP", "hp": 25})

        events = resolve_pvp_tick(room, {"1": "fire", "2": "fire"})

        self.assertEqual(room["tanks"]["2"]["hp"], 0)
        self.assertEqual(room["winner"], "1")
        self.assertGreater(len(events[1]["path"]), 0)

    def test_tanks_cannot_move_into_same_cell(self):
        room = make_room()
        room["tanks"]["1"].update({"x": 1, "y": 1, "direction": "RIGHT"})
        room["tanks"]["2"].update({"x": 3, "y": 1, "direction": "LEFT"})

        events = resolve_pvp_tick(room, {"1": "move", "2": "move"})

        self.assertEqual((room["tanks"]["1"]["x"], room["tanks"]["1"]["y"]), (1, 1))
        self.assertEqual((room["tanks"]["2"]["x"], room["tanks"]["2"]["y"]), (3, 1))
        self.assertEqual(events[0]["blocked"], "tank conflict")
        self.assertEqual(events[1]["blocked"], "tank conflict")

    def test_tanks_cannot_swap_cells(self):
        room = make_room()
        room["tanks"]["1"].update({"x": 1, "y": 1, "direction": "RIGHT"})
        room["tanks"]["2"].update({"x": 2, "y": 1, "direction": "LEFT"})

        resolve_pvp_tick(room, {"1": "move", "2": "move"})

        self.assertEqual((room["tanks"]["1"]["x"], room["tanks"]["1"]["y"]), (1, 1))
        self.assertEqual((room["tanks"]["2"]["x"], room["tanks"]["2"]["y"]), (2, 1))


if __name__ == "__main__":
    unittest.main()

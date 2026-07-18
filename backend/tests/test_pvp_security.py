import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.security.rate_limit import SlidingWindowRateLimiter
from app.simulator import pvp_engine


class RateLimiterTests(unittest.TestCase):
    def test_blocks_after_limit_and_allows_after_window(self):
        limiter = SlidingWindowRateLimiter()
        self.assertEqual(limiter.consume("user", 2, 10, now=1), (True, 0))
        self.assertEqual(limiter.consume("user", 2, 10, now=2), (True, 0))
        allowed, retry_after = limiter.consume("user", 2, 10, now=3)
        self.assertFalse(allowed)
        self.assertEqual(retry_after, 8)
        self.assertEqual(limiter.consume("user", 2, 10, now=12), (True, 0))


class PvpOwnershipTests(unittest.TestCase):
    def setUp(self):
        pvp_engine.rooms.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(
            pvp_engine, "DATA_FILE", Path(self.temp_dir.name) / "pvp_rooms.json"
        )
        self.data_patch.start()

    def tearDown(self):
        self.data_patch.stop()
        self.temp_dir.cleanup()
        pvp_engine.rooms.clear()

    def test_room_owns_slots_and_public_state_hides_account_ids(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")

        self.assertEqual(room["player_ids"], {"1": "user-1", "2": "user-2"})
        self.assertNotIn("player_ids", pvp_engine.public_room(room))

    def test_only_public_waiting_rooms_are_listed(self):
        public = pvp_engine.create_room("user-1", "Public host", 1)
        private = pvp_engine.create_room("user-2", "Private host", 2, private=True)
        full = pvp_engine.create_room("user-3", "Full host", 3)
        pvp_engine.join_room(full["code"], "user-4", "Guest")

        listed_codes = {room["code"] for room in pvp_engine.list_open_rooms()}

        self.assertIn(public["code"], listed_codes)
        self.assertNotIn(private["code"], listed_codes)
        self.assertNotIn(full["code"], listed_codes)

    def test_user_cannot_create_or_join_multiple_active_rooms(self):
        first = pvp_engine.create_room("user-1", "Commander One", 1)
        second = pvp_engine.create_room("user-2", "Commander Two", 2)

        with self.assertRaises(pvp_engine.RoomConflictError):
            pvp_engine.create_room("user-1", "Commander One", 3)
        with self.assertRaises(pvp_engine.RoomConflictError):
            pvp_engine.join_room(second["code"], "user-1", "Commander One")
        with self.assertRaises(pvp_engine.RoomConflictError):
            pvp_engine.join_room(first["code"], "user-1", "Commander One")

    def test_legacy_room_without_owner_ids_is_not_restored(self):
        pvp_engine.DATA_FILE.write_text(
            '{"ABC123":{"code":"ABC123","map_id":1,"players":{"1":"Guest"}}}',
            encoding="utf-8",
        )
        pvp_engine.load_rooms_from_disk()
        self.assertEqual(pvp_engine.rooms, {})

    def test_legacy_ready_room_is_reopened_after_restart(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")
        room["programs"] = {"1": ["move"], "2": ["fire"]}
        room["ready"] = {"1", "2"}
        # This is the broken state persisted by the previous route ordering.
        room["phase"] = "prepare"
        pvp_engine.save_rooms_to_disk()

        pvp_engine.rooms.clear()
        pvp_engine.load_rooms_from_disk()
        restored = pvp_engine.rooms[room["code"]]

        self.assertEqual(restored["phase"], "prepare")
        self.assertEqual(restored["ready"], set())
        self.assertEqual(restored["programs"], {})
        self.assertEqual(restored["tick"], 0)

    def test_active_battle_is_safely_reset_after_restart(self):
        room = pvp_engine.create_room("user-1", "Commander One", 2)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")
        room["phase"] = "battle"
        room["ready"] = {"1", "2"}
        room["programs"] = {"1": ["move"], "2": ["fire"]}
        room["indexes"] = {"1": 4, "2": 4}
        room["tick"] = 4
        room["tanks"]["1"]["hp"] = 50
        pvp_engine.save_rooms_to_disk()

        pvp_engine.rooms.clear()
        pvp_engine.load_rooms_from_disk()
        restored = pvp_engine.rooms[room["code"]]

        self.assertEqual(restored["phase"], "prepare")
        self.assertEqual(restored["ready"], set())
        self.assertEqual(restored["programs"], {})
        self.assertEqual(restored["indexes"], {"1": 0, "2": 0})
        self.assertEqual(restored["tanks"]["1"]["hp"], 100)
        self.assertEqual(restored["walls"], dict(pvp_engine.PVP_MAP_WALLS[2]))

    def test_old_action_list_program_is_reset_after_upgrade(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")
        room["ready"] = {"1"}
        room["programs"] = {"1": ["move", "fire"]}
        pvp_engine.save_rooms_to_disk()

        pvp_engine.rooms.clear()
        pvp_engine.load_rooms_from_disk()
        restored = pvp_engine.rooms[room["code"]]

        self.assertEqual(restored["ready"], set())
        self.assertEqual(restored["programs"], {})

    def test_pvp_python_for_loop_repeats_as_a_strategy(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")
        room["programs"]["1"] = "for i in range(3):\n    move()"

        stream = pvp_engine.strategy_stream(room, "1")

        self.assertEqual([next(stream) for _ in range(4)], ["move"] * 4)

    def test_invalid_pvp_python_is_rejected_before_ready(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")

        with self.assertRaises(ValueError):
            pvp_engine.validate_pvp_strategy(room, "1", "import os")

    def test_pvp_python_if_uses_live_scan_result(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")
        room["programs"]["1"] = (
            "if scan():\n    fire()\nelse:\n    rotate('LEFT')"
        )

        stream = pvp_engine.strategy_stream(room, "1")

        self.assertEqual([next(stream), next(stream)], ["scan", "left"])

    def test_pvp_python_while_uses_live_scan_result(self):
        room = pvp_engine.create_room("user-1", "Commander One", 1)
        pvp_engine.join_room(room["code"], "user-2", "Commander Two")
        room["walls"] = set()
        room["tanks"]["1"].update({"x": 1, "y": 1, "direction": "RIGHT"})
        room["tanks"]["2"].update({"x": 3, "y": 1, "direction": "LEFT"})
        room["programs"]["1"] = "while scan():\n    fire()"

        stream = pvp_engine.strategy_stream(room, "1")

        self.assertEqual([next(stream), next(stream)], ["scan", "fire"])


if __name__ == "__main__":
    unittest.main()

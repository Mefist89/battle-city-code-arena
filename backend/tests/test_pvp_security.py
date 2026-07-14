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


if __name__ == "__main__":
    unittest.main()

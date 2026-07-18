import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import profile_store


class ProfileStoreTests(unittest.TestCase):
    def test_completion_tracks_best_score_and_unique_missions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            with patch.object(profile_store, "DATA_FILE", path):
                profile_store.complete_mission("user-1", 1, 100)
                profile_store.complete_mission("user-1", 1, 80)
                progress = profile_store.complete_mission("user-1", 2, 250)

        self.assertEqual(progress["completed_missions"], [1, 2])
        self.assertEqual(progress["completed_count"], 2)
        self.assertEqual(progress["total_score"], 350)
        self.assertEqual(progress["missions"]["1"]["completions"], 2)

    def test_corrupted_progress_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            damaged = '{"user-1": {"missions": '
            path.write_text(damaged, encoding="utf-8")

            with patch.object(profile_store, "DATA_FILE", path):
                with self.assertRaises(profile_store.ProfileStoreCorrupted):
                    profile_store.complete_mission("user-2", 1, 999)

            self.assertEqual(path.read_text(encoding="utf-8"), damaged)

    def test_challenge_result_tracks_stats_code_and_achievements(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            with patch.object(profile_store, "DATA_FILE", path):
                progress = profile_store.record_challenge_result(
                    "user-1",
                    difficulty="hard",
                    map_id=2,
                    winner="PLAYER",
                    score=2400,
                    shots=12,
                    hits=10,
                    walls_destroyed=10,
                    code="scan()\nfire()",
                )

        self.assertEqual(progress["challenge"]["matches"], 1)
        self.assertEqual(progress["challenge"]["wins"], 1)
        self.assertEqual(progress["challenge"]["best_score"], 2400)
        self.assertEqual(progress["last_code"]["challenge"]["code"], "scan()\nfire()")
        achievement_ids = {item["id"] for item in progress["achievements"]}
        self.assertTrue({"ai_first_win", "ai_hard_win", "brick_breaker", "sharpshooter"} <= achievement_ids)

    def test_pvp_result_is_counted_for_each_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            with patch.object(profile_store, "DATA_FILE", path):
                profile_store.record_pvp_result("user-1", "win")
                profile_store.record_pvp_result("user-1", "loss")
                progress = profile_store.record_pvp_result("user-1", "draw")

        self.assertEqual(
            progress["pvp"],
            {"matches": 3, "wins": 1, "losses": 1, "draws": 1, "rating": 1000},
        )
        self.assertIn("pvp_first_win", {item["id"] for item in progress["achievements"]})

    def test_pvp_match_updates_both_ratings_and_server_history_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            with patch.object(profile_store, "DATA_FILE", path):
                profile_store.record_pvp_match(
                    match_id="match-1",
                    room_code="ABC123",
                    map_id=2,
                    player_ids={"1": "user-1", "2": "user-2"},
                    player_names={"1": "Alpha", "2": "Bravo"},
                    winner="1",
                    hp={"1": 50, "2": 0},
                    reason="destroyed",
                )
                # Retrying the server write must be idempotent.
                profile_store.record_pvp_match(
                    match_id="match-1",
                    room_code="ABC123",
                    map_id=2,
                    player_ids={"1": "user-1", "2": "user-2"},
                    player_names={"1": "Alpha", "2": "Bravo"},
                    winner="1",
                    hp={"1": 50, "2": 0},
                    reason="destroyed",
                )
                winner = profile_store.get_progress("user-1")
                loser = profile_store.get_progress("user-2")
                leaderboard = profile_store.get_pvp_leaderboard()

        self.assertEqual(winner["pvp"]["matches"], 1)
        self.assertEqual(loser["pvp"]["matches"], 1)
        self.assertGreater(winner["pvp"]["rating"], 1000)
        self.assertLess(loser["pvp"]["rating"], 1000)
        self.assertTrue(winner["pvp_history"][0]["server_confirmed"])
        self.assertEqual(leaderboard[0]["name"], "Alpha")

    def test_last_code_is_saved_per_game_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            with patch.object(profile_store, "DATA_FILE", path):
                profile_store.save_last_code("user-1", "mission", "move()")
                progress = profile_store.save_last_code("user-1", "pvp", "scan()\nfire()")

        self.assertEqual(progress["last_code"]["mission"]["code"], "move()")
        self.assertEqual(progress["last_code"]["pvp"]["code"], "scan()\nfire()")

    def test_named_strategies_can_be_saved_updated_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            with patch.object(profile_store, "DATA_FILE", path):
                saved = profile_store.save_named_strategy(
                    "user-1", mode="challenge", name="Wall hunter", code="scan()"
                )
                updated = profile_store.save_named_strategy(
                    "user-1",
                    mode="challenge",
                    name="Wall hunter",
                    code="scan()\nfire()",
                    strategy_id=saved["id"],
                )
                progress = profile_store.get_progress("user-1")
                deleted = profile_store.delete_named_strategy("user-1", saved["id"])
                after_delete = profile_store.get_progress("user-1")

        self.assertEqual(updated["id"], saved["id"])
        self.assertEqual(progress["strategies"]["challenge"][0]["code"], "scan()\nfire()")
        self.assertTrue(deleted)
        self.assertEqual(after_delete["strategies"]["challenge"], [])


if __name__ == "__main__":
    unittest.main()

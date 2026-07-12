import unittest

from app.simulator.challenge_engine import simulate_challenge
from app.simulator.mission_engine import MissionState
from app.simulator.python_runner import run_user_code, validate_user_code


class SandboxTests(unittest.TestCase):
    def test_import_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_code("import os")

    def test_file_access_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_code("open('secret.txt')")

    def test_for_loop_executes_expected_commands(self):
        state = MissionState()
        state.reset(1)
        result = run_user_code("for i in range(3):\n    move()", state)
        player_ticks = [tick for tick in result["ticks"] if tick["command"] != "wait"]
        self.assertEqual(len(player_ticks), 3)


class ChallengeTests(unittest.TestCase):
    def test_single_command_is_not_repeated(self):
        result = simulate_challenge(["rotate_right"], "easy", 1)
        player_events = [
            event
            for tick in result["ticks"]
            for event in tick["events"]
            if event.get("slot") == "PLAYER"
        ]
        self.assertEqual(len(player_events), 1)

    def test_for_loop_is_interpreted(self):
        code = "for i in range(3):\n    rotate('RIGHT')"
        result = simulate_challenge([], "easy", 1, code)
        player_events = [
            event
            for tick in result["ticks"]
            for event in tick["events"]
            if event.get("slot") == "PLAYER"
        ]
        self.assertEqual(
            [event["kind"] for event in player_events[:3]],
            ["rotate_right", "rotate_right", "rotate_right"],
        )


class MultiEnemyTests(unittest.TestCase):
    def test_mission_nine_has_three_enemies(self):
        state = MissionState()
        state.reset(9)
        self.assertEqual(len(state.enemies), 3)
        self.assertTrue(all(enemy.alive for enemy in state.enemies))


if __name__ == "__main__":
    unittest.main()

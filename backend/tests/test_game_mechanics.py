import unittest
from unittest.mock import patch

from app.simulator.challenge_engine import (
    ai_turn,
    fire_tank,
    resolve_challenge_turn,
    simulate_challenge,
)
from app.schemas.game import Command, EnemyState, TankState
from app.simulator.mission_engine import MissionState, execute_command
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
    def test_challenge_shot_reports_its_exact_impact(self):
        player = {"x": 1, "y": 3, "direction": "RIGHT", "hp": 100}
        ai = {"x": 3, "y": 3, "direction": "LEFT", "hp": 50}

        hit_event = fire_tank(player, ai, set(), "PLAYER")
        wall_event = fire_tank(player, ai, {(2, 3)}, "PLAYER")

        self.assertEqual(hit_event["hit"], "AI")
        self.assertEqual(hit_event["target_hp"], 25)
        self.assertEqual(wall_event["wall"], {"x": 2, "y": 3, "destroyed": True})

    def test_easy_ai_waits_about_one_second_between_decisions(self):
        result = simulate_challenge([], "easy", 1)
        action_ticks = [
            index
            for index, tick in enumerate(result["ticks"])
            if any(event.get("slot") == "AI" for event in tick["events"])
        ]

        action_times = [(index + 1) * result["tick_ms"] for index in action_ticks]

        self.assertGreater(len(action_ticks), 2)
        self.assertEqual(action_times[0], 1_000)
        self.assertLessEqual(len(action_ticks), 30)
        self.assertTrue(
            all(
                current - previous == 1_000
                for previous, current in zip(action_times, action_times[1:])
            )
        )

    def test_easy_ai_waits_two_seconds_between_shots(self):
        def forced_shot(ai, player, walls, difficulty, can_fire=True):
            return {
                "kind": "fire" if can_fire else "scan",
                "slot": "AI",
                "path": [],
            }

        with patch(
            "app.simulator.challenge_engine.ai_turn", side_effect=forced_shot
        ):
            result = simulate_challenge([], "easy", 1)

        shot_times = [
            (index + 1) * result["tick_ms"]
            for index, tick in enumerate(result["ticks"])
            if any(
                event.get("slot") == "AI" and event.get("kind") == "fire"
                for event in tick["events"]
            )
        ]

        self.assertEqual(shot_times[:4], [1_000, 3_000, 5_000, 7_000])
        self.assertTrue(
            all(
                current - previous >= 2_000
                for previous, current in zip(shot_times, shot_times[1:])
            )
        )

    def test_medium_and_hard_use_distinct_fire_cooldowns(self):
        def forced_shot(ai, player, walls, difficulty, can_fire=True):
            return {
                "kind": "fire" if can_fire else "scan",
                "slot": "AI",
                "path": [],
            }

        expected_intervals = {"medium": 840, "hard": 1_260}
        for difficulty, expected_interval in expected_intervals.items():
            with self.subTest(difficulty=difficulty), patch(
                "app.simulator.challenge_engine.ai_turn", side_effect=forced_shot
            ):
                result = simulate_challenge([], difficulty, 1)
                shot_times = [
                    (index + 1) * result["tick_ms"]
                    for index, tick in enumerate(result["ticks"])
                    if any(
                        event.get("slot") == "AI" and event.get("kind") == "fire"
                        for event in tick["events"]
                    )
                ]

                self.assertGreater(len(shot_times), 2)
                self.assertTrue(
                    all(
                        current - previous == expected_interval
                        for previous, current in zip(shot_times, shot_times[1:])
                    )
                )

    def test_easy_ai_does_not_fire_through_wall_destroyed_in_same_tick(self):
        player = {"x": 1, "y": 1, "direction": "RIGHT", "hp": 100}
        ai = {"x": 3, "y": 1, "direction": "LEFT", "hp": 50}
        walls = {(2, 1)}

        with patch("app.simulator.challenge_engine.random.random", return_value=0.1):
            player_event, ai_event, remaining, *_ = resolve_challenge_turn(
                player, ai, walls, "fire", "easy"
            )

        self.assertEqual(player_event["path"], [{"x": 2, "y": 1}])
        self.assertEqual(ai_event["kind"], "scan")
        self.assertEqual(remaining, set())

    def test_medium_ai_shoots_a_wall_blocking_its_route(self):
        player = {"x": 1, "y": 3, "direction": "UP", "hp": 100}
        ai = {"x": 3, "y": 1, "direction": "LEFT", "hp": 100}
        walls = {(2, 1)}

        event = ai_turn(ai, player, walls, "medium")

        self.assertEqual(event["kind"], "fire")
        self.assertEqual(event["path"], [{"x": 2, "y": 1}])
        self.assertEqual(walls, set())

    def test_hard_ai_dodges_a_shot_when_player_is_aiming_at_it(self):
        player = {"x": 1, "y": 3, "direction": "RIGHT", "hp": 100}
        ai = {"x": 4, "y": 3, "direction": "LEFT", "hp": 150}

        player_event, ai_event, *_ = resolve_challenge_turn(
            player, ai, set(), "fire", "hard"
        )

        self.assertEqual(ai_event["kind"], "move")
        self.assertTrue(ai_event["dodged"])
        self.assertNotEqual(ai["y"], 3)
        self.assertEqual(ai["hp"], 150)
        self.assertNotEqual(player_event["path"][-1], {"x": ai["x"], "y": ai["y"]})

    def test_hard_ai_does_not_spam_shots_during_cooldown(self):
        player = {"x": 1, "y": 3, "direction": "UP", "hp": 100}
        ai = {"x": 4, "y": 3, "direction": "LEFT", "hp": 150}

        event = ai_turn(ai, player, set(), "hard", can_fire=False)

        self.assertEqual(event["kind"], "scan")
        self.assertEqual(player["hp"], 100)

    def test_hard_ai_uses_pathfinding_around_walls(self):
        player = {"x": 1, "y": 6, "direction": "UP", "hp": 100}
        ai = {"x": 4, "y": 3, "direction": "UP", "hp": 150}
        walls = {(3, 3), (4, 2)}

        event = ai_turn(ai, player, walls, "hard")

        self.assertIn(event["kind"], {"move", "rotate"})
        self.assertIn(ai["direction"], {"RIGHT", "DOWN"})
        self.assertNotIn((ai["x"], ai["y"]), walls)

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


class MissionProjectileTests(unittest.TestCase):
    def make_clear_horizontal_state(self, enemy_direction: str) -> MissionState:
        state = MissionState()
        state.tank = TankState(x=1, y=1, direction="RIGHT")
        state.enemies = [EnemyState(x=3, y=1, direction=enemy_direction)]
        state.walls = {}
        return state

    def test_player_shot_hits_enemy_facing_elsewhere(self):
        state = self.make_clear_horizontal_state("DOWN")

        result = execute_command(state, Command(name="fire"))

        self.assertEqual(state.enemies[0].hp, 50)
        self.assertIn("Enemy hit: HP=50", result.events)
        self.assertNotIn("Bullets collided: no damage", result.events)

    def test_real_opposing_shots_cancel_without_damage(self):
        state = self.make_clear_horizontal_state("LEFT")

        result = execute_command(state, Command(name="fire"))

        self.assertEqual(state.tank.hp, 100)
        self.assertEqual(state.enemies[0].hp, 100)
        self.assertIn("Bullets collided: no damage", result.events)
        self.assertIn("Enemy shot cancelled by bullet collision", result.events)


class MissionCompletionTests(unittest.TestCase):
    def test_server_records_completion_when_goal_is_reached(self):
        state = MissionState()
        state.reset(1)

        for _ in range(4):
            execute_command(state, Command(name="move"))

        self.assertTrue(state.mission_completed)
        self.assertEqual(state.completion_score, state.tank.score)

    def test_reset_clears_verified_completion(self):
        state = MissionState()
        state.reset(1)
        state.mission_completed = True
        state.progress_claimed = True

        state.reset(2)

        self.assertFalse(state.mission_completed)
        self.assertFalse(state.progress_claimed)


if __name__ == "__main__":
    unittest.main()

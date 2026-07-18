import unittest

from app.simulator.mission_engine import (
    MissionProgressClaimError,
    MissionState,
    claim_verified_completion,
)


class MissionProgressSecurityTests(unittest.TestCase):
    def test_incomplete_session_cannot_claim_progress(self):
        state = MissionState()
        state.reset(1)

        with self.assertRaises(MissionProgressClaimError):
            claim_verified_completion(state, 1)

    def test_claim_uses_server_score_and_is_single_use(self):
        state = MissionState()
        state.reset(4)
        state.mission_completed = True
        state.completion_score = 500

        self.assertEqual(claim_verified_completion(state, 4), 500)
        with self.assertRaises(MissionProgressClaimError):
            claim_verified_completion(state, 4)

    def test_different_mission_cannot_use_completed_session(self):
        state = MissionState()
        state.reset(4)
        state.mission_completed = True

        with self.assertRaises(MissionProgressClaimError):
            claim_verified_completion(state, 5)


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.session_store import SessionStore


class SessionStoreConcurrencyTests(unittest.TestCase):
    def test_same_session_mutations_are_serialized(self):
        store = SessionStore()
        session_id, _ = store.create(1)

        def increment_score():
            with store.locked(session_id) as state:
                self.assertIsNotNone(state)
                current = state.tank.score
                time.sleep(0.02)
                state.tank.score = current + 1

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(increment_score) for _ in range(2)]
            for future in futures:
                future.result()

        with store.locked(session_id) as state:
            self.assertEqual(state.tank.score, 2)

    def test_different_sessions_can_run_independently(self):
        store = SessionStore()
        first_id, _ = store.create(1)
        second_id, _ = store.create(2)
        started = []

        def hold_session(session_id):
            with store.locked(session_id) as state:
                self.assertIsNotNone(state)
                started.append(session_id)
                time.sleep(0.02)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(hold_session, first_id),
                executor.submit(hold_session, second_id),
            ]
            for future in futures:
                future.result()

        self.assertCountEqual(started, [first_id, second_id])


if __name__ == "__main__":
    unittest.main()

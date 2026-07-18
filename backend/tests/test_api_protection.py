import asyncio
import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from app.config import MAX_CHALLENGE_ACTIONS, MAX_USER_CODE_LENGTH
from app.routes.challenge import ChallengeRequest, api_simulate_challenge
from app.routes.game import RunCodeRequest
from app.security.game_guard import enforce_game_rate_limit
from app.security.rate_limit import game_rate_limiter
from app.security.request_size import RequestSizeLimitMiddleware


def make_request(ip: str = "127.0.0.1") -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "client": (ip, 1234)})


class ApiValidationTests(unittest.TestCase):
    def tearDown(self):
        game_rate_limiter.reset()

    def test_challenge_parser_error_becomes_422(self):
        payload = ChallengeRequest(actions=[], code="import os")

        with self.assertRaises(HTTPException) as error:
            api_simulate_challenge(make_request(), payload)

        self.assertEqual(error.exception.status_code, 422)
        self.assertIn("Unsupported syntax: Import", error.exception.detail)

    def test_game_code_length_is_limited(self):
        with self.assertRaises(ValidationError):
            RunCodeRequest(code="x" * (MAX_USER_CODE_LENGTH + 1))

    def test_challenge_code_and_action_count_are_limited(self):
        with self.assertRaises(ValidationError):
            ChallengeRequest(actions=[], code="x" * (MAX_USER_CODE_LENGTH + 1))
        with self.assertRaises(ValidationError):
            ChallengeRequest(actions=["move"] * (MAX_CHALLENGE_ACTIONS + 1))

    def test_rate_limit_returns_429_and_retry_after(self):
        request = make_request("192.0.2.10")
        enforce_game_rate_limit(request, "test", ip_limit=1)

        with self.assertRaises(HTTPException) as error:
            enforce_game_rate_limit(request, "test", ip_limit=1)

        self.assertEqual(error.exception.status_code, 429)
        self.assertIn("Retry-After", error.exception.headers)


class RequestSizeMiddlewareTests(unittest.TestCase):
    def test_content_length_over_limit_returns_413(self):
        async def run_test():
            async def app(scope, receive, send):
                raise AssertionError("Oversized request reached the application")

            sent = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                sent.append(message)

            middleware = RequestSizeLimitMiddleware(app, max_body_bytes=5)
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/game/run",
                "headers": [(b"content-length", b"6")],
            }
            await middleware(scope, receive, send)
            return sent

        sent = asyncio.run(run_test())
        start = next(message for message in sent if message["type"] == "http.response.start")
        self.assertEqual(start["status"], 413)

    def test_streamed_body_over_limit_returns_413(self):
        async def run_test():
            chunks = iter(
                [
                    {"type": "http.request", "body": b"123", "more_body": True},
                    {"type": "http.request", "body": b"456", "more_body": False},
                ]
            )
            sent = []

            async def receive():
                return next(chunks)

            async def send(message):
                sent.append(message)

            async def app(scope, receive, send):
                while True:
                    message = await receive()
                    if not message.get("more_body"):
                        break

            middleware = RequestSizeLimitMiddleware(app, max_body_bytes=5)
            scope = {"type": "http", "method": "POST", "path": "/", "headers": []}
            await middleware(scope, receive, send)
            return sent

        sent = asyncio.run(run_test())
        start = next(message for message in sent if message["type"] == "http.response.start")
        self.assertEqual(start["status"], 413)


if __name__ == "__main__":
    unittest.main()

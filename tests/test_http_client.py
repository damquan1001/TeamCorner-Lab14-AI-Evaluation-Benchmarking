import unittest
from unittest.mock import patch

import urllib.error

from engine.http_client import post_json_with_retry


class HttpClientRetryTests(unittest.TestCase):
    def test_post_json_with_retry_succeeds_after_429(self):
        attempts = {"count": 0}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok": true}'

        def fake_urlopen(request, timeout):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    hdrs=None,
                    fp=type("fp", (), {"read": lambda self: b"quota exceeded"})(),
                )
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("time.sleep"):
                result = post_json_with_retry(
                    "https://example.com",
                    {"Content-Type": "application/json"},
                    {"hello": "world"},
                    5,
                    max_retries=3,
                    base_delay=0.01,
                )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(attempts["count"], 2)

    def test_post_json_with_retry_raises_after_max_retries(self):
        def always_429(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                hdrs=None,
                fp=type("fp", (), {"read": lambda self: b"quota exceeded"})(),
            )

        with patch("urllib.request.urlopen", side_effect=always_429):
            with patch("time.sleep"):
                with self.assertRaises(RuntimeError):
                    post_json_with_retry(
                        "https://example.com",
                        {},
                        {},
                        5,
                        max_retries=2,
                        base_delay=0.01,
                    )


if __name__ == "__main__":
    unittest.main()

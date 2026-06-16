import asyncio
import os
import unittest
from unittest.mock import patch

from agent.main_agent import MainAgent


class MainAgentTests(unittest.TestCase):
    def test_query_uses_openrouter_when_key_is_available(self):
        calls = []

        def fake_transport(url, headers, payload, timeout):
            calls.append((url, headers, payload, timeout))
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Use the account settings page to reset your password."
                        }
                    }
                ],
                "usage": {"total_tokens": 31},
            }

        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "openrouter-key",
                "OPENROUTER_AGENT_MODEL": "openrouter/agent-model",
                "AGENT_PROVIDER": "openrouter",
                "GEMINI_API_KEY": "",
            },
        ):
            agent = MainAgent(http_transport=fake_transport)
            result = asyncio.run(agent.query("How do I reset my password?"))

        self.assertEqual(result["answer"], "Use the account settings page to reset your password.")
        self.assertEqual(result["metadata"]["api_status"], "live")
        self.assertEqual(result["metadata"]["provider"], "openrouter")
        self.assertEqual(result["metadata"]["model"], "openrouter/agent-model")
        self.assertEqual(result["metadata"]["tokens_used"], 31)
        self.assertEqual(calls[0][0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(calls[0][1]["Authorization"], "Bearer openrouter-key")

    def test_query_falls_back_when_no_agent_api_key_exists(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "",
                "GEMINI_API_KEY": "",
                "AGENT_PROVIDER": "auto",
            },
        ):
            agent = MainAgent()
            result = asyncio.run(agent.query("Policy question number 7?"))

        self.assertEqual(result["metadata"]["api_status"], "offline_fallback")
        self.assertIn("Policy question number 7?", result["answer"])
        self.assertIn("doc_7", result["metadata"]["sources"])


if __name__ == "__main__":
    unittest.main()

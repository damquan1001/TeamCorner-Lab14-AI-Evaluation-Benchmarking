import asyncio
import unittest

from main import ExpertEvaluator


class ExpertEvaluatorTests(unittest.TestCase):
    def test_scores_are_derived_from_answer_and_retrieval_content(self):
        evaluator = ExpertEvaluator()
        case = {
            "question": "How do I reset my password?",
            "expected_answer": "Reset your password from account settings.",
            "expected_retrieval_ids": ["doc_password"],
        }
        response = {
            "answer": "Reset your password from account settings.",
            "contexts": ["Password resets happen in account settings."],
            "metadata": {"sources": ["doc_password"]},
        }

        result = asyncio.run(evaluator.score(case, response))

        self.assertAlmostEqual(result["faithfulness"], 0.5)
        self.assertAlmostEqual(result["relevancy"], 1.0)
        self.assertEqual(result["retrieval"]["hit_rate"], 1.0)
        self.assertEqual(result["retrieval"]["mrr"], 1.0)


if __name__ == "__main__":
    unittest.main()

import unittest

from main import build_summary


class SummaryMetricsTests(unittest.TestCase):
    def test_summary_includes_multi_judge_consensus_metrics(self):
        results = [
            {
                "status": "pass",
                "ragas": {"retrieval": {"hit_rate": 1.0}},
                "judge": {
                    "final_score": 4.0,
                    "agreement_rate": 0.9,
                    "score_gap": 0.5,
                    "conflict_detected": False,
                    "judge_models": ["gemini-3.5-flash", "openai/gpt-4o-mini"],
                    "individual_scores": {
                        "gemini": 4.0,
                        "openrouter": 4.5,
                    },
                    "resolution_strategy": "average",
                },
            },
            {
                "status": "fail",
                "ragas": {"retrieval": {"hit_rate": 0.0}},
                "judge": {
                    "final_score": 2.0,
                    "agreement_rate": 0.5,
                    "score_gap": 2.0,
                    "conflict_detected": True,
                    "judge_models": ["gemini-3.5-flash", "openai/gpt-4o-mini"],
                    "individual_scores": {
                        "gemini": 1.0,
                        "openrouter": 3.0,
                    },
                    "resolution_strategy": "conservative_min_score",
                },
            },
        ]

        summary = build_summary("Agent_V2_Optimized", results)
        metrics = summary["metrics"]
        consensus = summary["multi_judge_consensus"]

        self.assertEqual(metrics["avg_score"], 3.0)
        self.assertEqual(metrics["hit_rate"], 0.5)
        self.assertEqual(metrics["agreement_rate"], 0.7)
        self.assertEqual(metrics["avg_score_gap"], 1.25)
        self.assertEqual(metrics["conflict_rate"], 0.5)
        self.assertEqual(metrics["consensus_pass_rate"], 0.5)
        self.assertEqual(
            metrics["judge_models"],
            ["gemini-3.5-flash", "openai/gpt-4o-mini"],
        )
        self.assertEqual(consensus["conflict_count"], 1)
        self.assertEqual(consensus["resolution_strategies"]["average"], 1)
        self.assertEqual(consensus["resolution_strategies"]["conservative_min_score"], 1)


if __name__ == "__main__":
    unittest.main()

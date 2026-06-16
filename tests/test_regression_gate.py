import unittest
from main import evaluate_release_gate

class RegressionGateTests(unittest.TestCase):
    def setUp(self):
        self.v1_base = {
            "metrics": {
                "avg_score": 3.5,
                "consensus_pass_rate": 0.8,
                "hit_rate": 0.9,
                "avg_latency": 1.2,
                "avg_tokens_used": 200,
                "safety_violations": 0,
            }
        }
        self.v2_base = {
            "metrics": {
                "avg_score": 4.0,
                "consensus_pass_rate": 0.9,
                "hit_rate": 0.95,
                "avg_latency": 1.3,
                "avg_tokens_used": 220,
                "safety_violations": 0,
            }
        }

    def test_approve_when_all_criteria_met(self):
        res = evaluate_release_gate(self.v1_base, self.v2_base)
        self.assertTrue(res["approved"])
        self.assertEqual(res["decision"], "RELEASE")
        self.assertEqual(len(res["reasons"]), 0)

    def test_reject_when_score_regresses(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        v2["metrics"]["avg_score"] = 3.4
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertFalse(res["approved"])
        self.assertEqual(res["decision"], "ROLLBACK")
        self.assertTrue(any("Quality regression" in r for r in res["reasons"]))

    def test_reject_when_pass_rate_is_low(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        v2["metrics"]["consensus_pass_rate"] = 0.65
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertFalse(res["approved"])
        self.assertEqual(res["decision"], "ROLLBACK")
        self.assertTrue(any("Quality regression" in r for r in res["reasons"]))

    def test_reject_when_safety_violations_exist(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        v2["metrics"]["safety_violations"] = 1
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertFalse(res["approved"])
        self.assertEqual(res["decision"], "ROLLBACK")
        self.assertTrue(any("Safety violations" in r for r in res["reasons"]))

    def test_reject_when_latency_regresses_significantly(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        # V1: 1.2s -> V2: 2.5s (more than 30% increase and exceeds 2.0s limit)
        v2["metrics"]["avg_latency"] = 2.5
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertFalse(res["approved"])
        self.assertEqual(res["decision"], "ROLLBACK")
        self.assertTrue(any("Performance regression" in r for r in res["reasons"]))

    def test_approve_when_latency_increases_but_under_2_seconds(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        # V1: 1.0s -> V2: 1.5s (50% increase, but absolute avg latency is <= 2.0s)
        self.v1_base["metrics"]["avg_latency"] = 1.0
        v2["metrics"]["avg_latency"] = 1.5
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertTrue(res["approved"])
        self.assertEqual(res["decision"], "RELEASE")

    def test_reject_when_tokens_regress_significantly(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        # V1: 200 -> V2: 600 (3x increase and exceeds 500 tokens limit)
        v2["metrics"]["avg_tokens_used"] = 600
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertFalse(res["approved"])
        self.assertEqual(res["decision"], "ROLLBACK")
        self.assertTrue(any("Cost regression" in r for r in res["reasons"]))

    def test_approve_when_tokens_increase_but_under_500_tokens(self):
        v2 = dict(self.v2_base)
        v2["metrics"] = dict(v2["metrics"])
        # V1: 100 -> V2: 180 (80% increase, but absolute avg tokens is <= 500)
        self.v1_base["metrics"]["avg_tokens_used"] = 100
        v2["metrics"]["avg_tokens_used"] = 180
        
        res = evaluate_release_gate(self.v1_base, v2)
        self.assertTrue(res["approved"])
        self.assertEqual(res["decision"], "RELEASE")

if __name__ == "__main__":
    unittest.main()

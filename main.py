import asyncio
import json
import os
import time

from agent.main_agent import MainAgent, MainAgentV2
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner

MIN_AVG_SCORE = 3.0
MAX_HIT_RATE_DROP = 0.05


class ExpertEvaluator:
    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()

    async def score(self, case, resp):
        retrieved_ids = resp.get("metadata", {}).get("sources", [])
        expected_ids = case.get("expected_retrieval_ids", [])

        hit_rate = self.retrieval_eval.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.retrieval_eval.calculate_mrr(expected_ids, retrieved_ids)

        return {
            "faithfulness": 0.9 if hit_rate > 0 else 0.5,
            "relevancy": 0.8 if mrr > 0.5 else 0.6,
            "retrieval": {"hit_rate": hit_rate, "mrr": mrr},
        }


def build_summary(results, agent_version: str) -> dict:
    total = len(results)
    if total == 0:
        return {}

    total_tokens = sum(r.get("tokens_used", 0) for r in results)
    total_latency = sum(r.get("latency", 0) for r in results)
    pass_count = sum(1 for r in results if r["status"] == "pass")

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
            "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
            "avg_mrr": sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total,
            "pass_rate": pass_count / total,
            "avg_latency_sec": total_latency / total,
            "total_tokens": total_tokens,
            "cost_estimate_usd": round(total_tokens * 0.000002, 4),
        },
    }


def evaluate_release_gate(v1_summary: dict, v2_summary: dict) -> dict:
    v1m = v1_summary["metrics"]
    v2m = v2_summary["metrics"]

    delta_score = v2m["avg_score"] - v1m["avg_score"]
    delta_hit = v2m["hit_rate"] - v1m["hit_rate"]
    delta_mrr = v2m["avg_mrr"] - v1m["avg_mrr"]
    delta_agreement = v2m["agreement_rate"] - v1m["agreement_rate"]

    approve = (
        delta_score >= 0
        and delta_hit >= -MAX_HIT_RATE_DROP
        and v2m["avg_score"] >= MIN_AVG_SCORE
    )

    return {
        "baseline_version": v1_summary["metadata"]["version"],
        "candidate_version": v2_summary["metadata"]["version"],
        "delta_score": round(delta_score, 4),
        "delta_hit_rate": round(delta_hit, 4),
        "delta_mrr": round(delta_mrr, 4),
        "delta_agreement_rate": round(delta_agreement, 4),
        "decision": "APPROVE" if approve else "BLOCK_RELEASE",
        "thresholds": {
            "min_avg_score": MIN_AVG_SCORE,
            "max_hit_rate_drop": MAX_HIT_RATE_DROP,
        },
    }


async def run_benchmark_with_results(agent, agent_version: str):
    print(f"[*] Khoi dong Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("[X] Thieu data/golden_set.jsonl. Hay chay 'python data/synthetic_gen.py' truoc.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("[X] File data/golden_set.jsonl rong. Hay tao it nhat 1 test case.")
        return None, None

    judge = LLMJudge(primary_model="gpt-4o-mini", secondary_model="gpt-4o")
    runner = BenchmarkRunner(agent, ExpertEvaluator(), judge)
    results = await runner.run_all(dataset)

    summary = build_summary(results, agent_version)
    return results, summary


async def run_benchmark(agent, version: str):
    _, summary = await run_benchmark_with_results(agent, version)
    return summary


async def main():
    v1_summary = await run_benchmark(MainAgent(), "Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results(MainAgentV2(), "Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("[X] Khong the chay Benchmark. Kiem tra lai data/golden_set.jsonl.")
        return

    regression = evaluate_release_gate(v1_summary, v2_summary)

    print("\n--- KET QUA SO SANH (REGRESSION) ---")
    print(f"V1 Score:      {v1_summary['metrics']['avg_score']:.2f}")
    print(f"V2 Score:      {v2_summary['metrics']['avg_score']:.2f}")
    print(f"Delta Score:   {regression['delta_score']:+.2f}")
    print(f"V1 Hit Rate:   {v1_summary['metrics']['hit_rate']*100:.1f}%")
    print(f"V2 Hit Rate:   {v2_summary['metrics']['hit_rate']*100:.1f}%")
    print(f"V1 MRR:        {v1_summary['metrics']['avg_mrr']:.2f}")
    print(f"V2 MRR:        {v2_summary['metrics']['avg_mrr']:.2f}")
    print(f"Agreement:     {v2_summary['metrics']['agreement_rate']*100:.1f}%")
    print(f"Total Tokens:  {v2_summary['metrics']['total_tokens']}")

    v2_summary["regression"] = regression

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if regression["decision"] == "APPROVE":
        print("[OK] QUYET DINH: CHAP NHAN BAN CAP NHAT (APPROVE)")
    else:
        print("[X] QUYET DINH: TU CHOI (BLOCK RELEASE)")


if __name__ == "__main__":
    asyncio.run(main())

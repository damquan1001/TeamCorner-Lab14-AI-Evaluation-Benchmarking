import asyncio
import json
import os
import re
import time

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


class ExpertEvaluator:
    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()

    async def score(self, case, resp):
        retrieved_ids = resp.get("metadata", {}).get("sources", [])
        expected_ids = case.get("expected_retrieval_ids", [])
        answer = resp.get("answer", "")
        expected_answer = case.get("expected_answer", "")
        contexts = resp.get("contexts", [])

        hit_rate = self.retrieval_eval.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.retrieval_eval.calculate_mrr(expected_ids, retrieved_ids)
        faithfulness = self._token_overlap(answer, " ".join(contexts))
        relevancy = self._token_overlap(answer, expected_answer)

        return {
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "retrieval": {"hit_rate": hit_rate, "mrr": mrr},
        }

    def _token_overlap(self, candidate: str, reference: str) -> float:
        candidate_tokens = set(re.findall(r"[a-zA-Z0-9_]+", candidate.lower()))
        reference_tokens = set(re.findall(r"[a-zA-Z0-9_]+", reference.lower()))
        if not reference_tokens:
            return 0.0
        return round(len(candidate_tokens & reference_tokens) / len(reference_tokens), 2)


def build_summary(agent_version: str, results):
    total = len(results)
    judge_models = sorted({
        model
        for result in results
        for model in result["judge"].get("judge_models", [])
    })
    if not judge_models:
        judge_models = sorted({
            model
            for result in results
            for model in result["judge"].get("individual_scores", {}).keys()
        })
    resolution_strategies = {}
    for result in results:
        strategy = result["judge"].get("resolution_strategy", "unknown")
        resolution_strategies[strategy] = resolution_strategies.get(strategy, 0) + 1

    conflict_count = sum(1 for result in results if result["judge"].get("conflict_detected"))
    pass_count = sum(1 for result in results if result.get("status") == "pass")

    metrics = {
        "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
        "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
        "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total,
        "avg_score_gap": sum(r["judge"].get("score_gap", 0.0) for r in results) / total,
        "conflict_rate": conflict_count / total,
        "judge_models": judge_models,
        "consensus_pass_rate": pass_count / total,
    }

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": metrics,
        "multi_judge_consensus": {
            "models": judge_models,
            "average_agreement_rate": metrics["agreement_rate"],
            "average_score_gap": metrics["avg_score_gap"],
            "conflict_count": conflict_count,
            "conflict_rate": metrics["conflict_rate"],
            "consensus_pass_rate": metrics["consensus_pass_rate"],
            "resolution_strategies": resolution_strategies,
            "automatic_resolution": "score gaps above 1.0 use conservative_min_score",
        },
    }


async def run_benchmark_with_results(agent_version: str):
    print(f"Starting benchmark for {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("Missing data/golden_set.jsonl. Run 'python data/synthetic_gen.py' first.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("data/golden_set.jsonl is empty. Create at least one test case.")
        return None, None

    runner = BenchmarkRunner(MainAgent(), ExpertEvaluator(), LLMJudge())
    results = await runner.run_all(dataset)
    summary = build_summary(agent_version, results)
    return results, summary


async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary


async def main():
    v1_summary = await run_benchmark("Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("Benchmark could not run. Check data/golden_set.jsonl.")
        return

    print("\n--- REGRESSION COMPARISON ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")
    print(f"Multi-judge agreement: {v2_summary['metrics']['agreement_rate']:.2f}")
    print(f"Conflict rate: {v2_summary['metrics']['conflict_rate']:.2f}")

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if delta > 0:
        print("RELEASE GATE: APPROVE")
    else:
        print("RELEASE GATE: BLOCK RELEASE")


if __name__ == "__main__":
    asyncio.run(main())

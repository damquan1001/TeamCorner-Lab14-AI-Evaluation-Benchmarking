import asyncio
import json
import os
import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.rate_limit import AsyncRateLimiter
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


def estimate_agent_cost(provider: str, usage: dict) -> float:
    if not usage:
        return 0.0
    if provider == "gemini":
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        return (prompt_tokens * 0.075 + completion_tokens * 0.30) / 1_000_000
    elif provider == "openrouter":
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        return (prompt_tokens * 0.150 + completion_tokens * 0.600) / 1_000_000
    else:
        total = usage.get("total_tokens", usage.get("totalTokenCount", 0))
        return (total * 0.150) / 1_000_000


def estimate_judge_cost(usage: dict) -> float:
    cost = 0.0
    if not usage:
        return cost
    gemini_usage = usage.get("gemini", {})
    if gemini_usage:
        prompt = gemini_usage.get("promptTokenCount", 0)
        completion = gemini_usage.get("candidatesTokenCount", 0)
        cost += (prompt * 0.075 + completion * 0.30) / 1_000_000
    openrouter_usage = usage.get("openrouter", {})
    if openrouter_usage:
        prompt = openrouter_usage.get("prompt_tokens", 0)
        completion = openrouter_usage.get("completion_tokens", 0)
        cost += (prompt * 0.150 + completion * 0.600) / 1_000_000
    return cost


def evaluate_release_gate(v1_summary, v2_summary) -> dict:
    v1_metrics = v1_summary["metrics"]
    v2_metrics = v2_summary["metrics"]

    delta_score = v2_metrics["avg_score"] - v1_metrics["avg_score"]
    delta_pass_rate = v2_metrics["consensus_pass_rate"] - v1_metrics["consensus_pass_rate"]
    
    v1_lat = v1_metrics.get("avg_latency", 0.0)
    v2_lat = v2_metrics.get("avg_latency", 0.0)
    pct_latency_change = 0.0
    if v1_lat > 0:
        pct_latency_change = (v2_lat - v1_lat) / v1_lat

    v1_tokens = v1_metrics.get("avg_tokens_used", 0)
    v2_tokens = v2_metrics.get("avg_tokens_used", 0)
    pct_tokens_change = 0.0
    if v1_tokens > 0:
        pct_tokens_change = (v2_tokens - v1_tokens) / v1_tokens

    safety_violations = v2_metrics.get("safety_violations", 0)

    # Threshold rules:
    # 1. Quality: avg_score delta >= 0 AND pass_rate >= 0.7
    quality_passed = delta_score >= 0.0 and v2_metrics["consensus_pass_rate"] >= 0.70
    # 2. Performance: latency increase <= 30% OR avg_latency <= 2.0s
    performance_passed = pct_latency_change <= 0.30 or v2_lat <= 2.0
    # 3. Cost: tokens increase <= 30% OR avg_tokens <= 500
    cost_passed = pct_tokens_change <= 0.30 or v2_tokens <= 500
    # 4. Safety: violations == 0
    safety_passed = safety_violations == 0

    reasons = []
    if not quality_passed:
        reasons.append(
            f"Quality regression or low pass rate: score delta is {delta_score:+.2f}, "
            f"V2 pass rate is {v2_metrics['consensus_pass_rate']*100:.1f}% (required >= 70%)"
        )
    if not performance_passed:
        reasons.append(
            f"Performance regression: average latency increased by {pct_latency_change*100:+.1f}% "
            f"(V1: {v1_lat:.2f}s, V2: {v2_lat:.2f}s)"
        )
    if not cost_passed:
        reasons.append(
            f"Cost regression: average tokens increased by {pct_tokens_change*100:+.1f}% "
            f"(V1: {v1_tokens:.1f}, V2: {v2_tokens:.1f})"
        )
    if not safety_passed:
        reasons.append(f"Safety violations detected: V2 had {safety_violations} safety failure(s).")

    approved = quality_passed and performance_passed and cost_passed and safety_passed
    decision = "RELEASE" if approved else "ROLLBACK"

    return {
        "approved": approved,
        "decision": decision,
        "reasons": reasons,
        "deltas": {
            "delta_score": delta_score,
            "delta_pass_rate": delta_pass_rate,
            "pct_latency_change": pct_latency_change,
            "pct_tokens_change": pct_tokens_change,
            "safety_violations": safety_violations,
        },
        "thresholds_checked": {
            "quality_rule": {
                "passed": quality_passed,
                "delta_score": round(delta_score, 2),
                "v2_pass_rate": round(v2_metrics["consensus_pass_rate"], 2)
            },
            "performance_rule": {
                "passed": performance_passed,
                "pct_change": round(pct_latency_change, 2),
                "v2_latency": round(v2_lat, 2)
            },
            "cost_rule": {
                "passed": cost_passed,
                "pct_change": round(pct_tokens_change, 2),
                "v2_tokens": round(v2_tokens, 2)
            },
            "safety_rule": {
                "passed": safety_passed,
                "violations": safety_violations
            }
        }
    }


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

    avg_latency = sum(r.get("latency", 0.0) for r in results) / total
    avg_tokens_used = sum(r.get("tokens_used", 0) for r in results) / total
    safety_violations = sum(1 for r in results if r.get("safety_failed", False))

    agent_costs = []
    for r in results:
        meta = r.get("agent_metadata", {})
        provider = meta.get("provider", "offline")
        usage_data = meta.get("usage", {})
        agent_costs.append(estimate_agent_cost(provider, usage_data))
    total_agent_cost = sum(agent_costs)
    avg_agent_cost = total_agent_cost / total

    judge_costs = []
    for r in results:
        j_usage = r.get("judge", {}).get("usage", {})
        judge_costs.append(estimate_judge_cost(j_usage))
    total_judge_cost = sum(judge_costs)
    avg_judge_cost = total_judge_cost / total

    metrics = {
        "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
        "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
        "avg_mrr": sum(r["ragas"]["retrieval"].get("mrr", 0.0) for r in results) / total,
        "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total,
        "avg_score_gap": sum(r["judge"].get("score_gap", 0.0) for r in results) / total,
        "conflict_rate": conflict_count / total,
        "judge_models": judge_models,
        "consensus_pass_rate": pass_count / total,
        "avg_latency": avg_latency,
        "avg_tokens_used": avg_tokens_used,
        "safety_violations": safety_violations,
        "total_agent_cost_usd": total_agent_cost,
        "total_judge_cost_usd": total_judge_cost,
        "total_eval_cost_usd": total_agent_cost + total_judge_cost,
        "avg_agent_cost_usd": avg_agent_cost,
        "avg_judge_cost_usd": avg_judge_cost,
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

    rate_limiter = AsyncRateLimiter.from_env()
    judge = LLMJudge(rate_limiter=rate_limiter)
    runner = BenchmarkRunner(
        MainAgent(version=agent_version),
        ExpertEvaluator(),
        judge,
        rate_limiter=rate_limiter,
    )
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

    gate_result = evaluate_release_gate(v1_summary, v2_summary)
    v2_summary["release_gate"] = gate_result

    print("\n" + "="*70)
    print("           REGRESSION & DELTA ANALYSIS REPORT           ")
    print("="*70)
    print(f"{'Metric':<25} | {'V1 (Base)':<12} | {'V2 (Opt)':<12} | {'Delta':<12}")
    print("-"*70)
    
    v1_m = v1_summary["metrics"]
    v2_m = v2_summary["metrics"]
    
    print(f"{'LLM Judge Avg Score':<25} | {v1_m['avg_score']:<12.2f} | {v2_m['avg_score']:<12.2f} | {gate_result['deltas']['delta_score']:+11.2f}")
    print(f"{'Consensus Pass Rate':<25} | {v1_m['consensus_pass_rate']*100:<11.1f}% | {v2_m['consensus_pass_rate']*100:<11.1f}% | {gate_result['deltas']['delta_pass_rate']*100:+10.1f}%")
    print(f"{'Retrieval Hit Rate':<25} | {v1_m['hit_rate']*100:<11.1f}% | {v2_m['hit_rate']*100:<11.1f}% | {(v2_m['hit_rate']-v1_m['hit_rate'])*100:+10.1f}%")
    print(f"{'Retrieval Avg MRR':<25} | {v1_m.get('avg_mrr', 0.0):<12.2f} | {v2_m.get('avg_mrr', 0.0):<12.2f} | {v2_m.get('avg_mrr', 0.0)-v1_m.get('avg_mrr', 0.0):+11.2f}")
    print(f"{'Avg Latency (seconds)':<25} | {v1_m.get('avg_latency', 0.0):<12.2f} | {v2_m.get('avg_latency', 0.0):<12.2f} | {gate_result['deltas']['pct_latency_change']*100:+10.1f}%")
    print(f"{'Avg Tokens per Query':<25} | {v1_m.get('avg_tokens_used', 0.0):<12.1f} | {v2_m.get('avg_tokens_used', 0.0):<12.1f} | {gate_result['deltas']['pct_tokens_change']*100:+10.1f}%")
    print(f"{'Safety Violations':<25} | {v1_m.get('safety_violations', 0):<12} | {v2_m.get('safety_violations', 0):<12} | {v2_m.get('safety_violations', 0) - v1_m.get('safety_violations', 0):+11}")
    print("="*70)
    
    print("\n--- EVALUATION COST SUMMARY ---")
    print(f"Total Agent API Cost: ${v2_m.get('total_agent_cost_usd', 0.0):.6f} USD")
    print(f"Total Judge API Cost: ${v2_m.get('total_judge_cost_usd', 0.0):.6f} USD")
    print(f"Total Eval Cost:      ${v2_m.get('total_eval_cost_usd', 0.0):.6f} USD")
    print(f"Avg Cost per Query:   ${v2_m.get('total_eval_cost_usd', 0.0)/v2_summary['metadata']['total']:.6f} USD")
    
    print("\n" + "="*70)
    print(f" RELEASE GATE DECISION: {gate_result['decision']} ")
    print("="*70)
    
    if gate_result["approved"]:
        print("✅ RELEASE GATE: APPROVED (Agent V2 passes all quality, cost, performance, and safety criteria).")
    else:
        print("❌ RELEASE GATE: REJECTED (ROLLBACK REQUIRED)")
        for reason in gate_result["reasons"]:
            print(f"   - {reason}")
    print("="*70 + "\n")

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())

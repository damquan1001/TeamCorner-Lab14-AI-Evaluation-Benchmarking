import asyncio
import time
from typing import List, Dict


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge, max_concurrency: int = 5):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        self.max_concurrency = max_concurrency

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time

        ragas_scores = await self.evaluator.score(test_case, response)

        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
        )

        tokens_used = response.get("metadata", {}).get("tokens_used", 0)
        sources = response.get("metadata", {}).get("sources", [])

        return {
            "test_case": test_case["question"],
            "case_id": test_case.get("id", ""),
            "agent_response": response["answer"],
            "retrieved_sources": sources,
            "latency": latency,
            "tokens_used": tokens_used,
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass",
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Run tests concurrently with a semaphore to avoid rate limits."""
        semaphore = asyncio.Semaphore(min(batch_size, self.max_concurrency))
        results: List[Dict] = []

        async def run_with_limit(case: Dict) -> Dict:
            async with semaphore:
                return await self.run_single_test(case)

        for i in range(0, len(dataset), batch_size):
            batch = dataset[i : i + batch_size]
            batch_results = await asyncio.gather(*[run_with_limit(case) for case in batch])
            results.extend(batch_results)

        return results

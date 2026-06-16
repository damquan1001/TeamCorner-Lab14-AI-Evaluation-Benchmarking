from typing import List, Dict


class RetrievalEvaluator:
    def calculate_hit_rate(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        top_k: int = 3,
    ) -> float:
        """Return 1.0 if any expected doc appears in top_k retrieved docs, else 0.0."""
        if not expected_ids or not retrieved_ids:
            return 0.0

        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """Mean Reciprocal Rank for the first matching expected doc."""
        if not expected_ids or not retrieved_ids:
            return 0.0

        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def evaluate_batch(
        self,
        dataset: List[Dict],
        agent_responses: List[Dict],
        top_k: int = 3,
    ) -> Dict:
        if not dataset:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0, "total": 0}

        hit_rates = []
        mrrs = []

        for case, resp in zip(dataset, agent_responses):
            expected_ids = case.get("expected_retrieval_ids", [])
            retrieved_ids = resp.get("metadata", {}).get("sources", [])

            hit_rates.append(self.calculate_hit_rate(expected_ids, retrieved_ids, top_k))
            mrrs.append(self.calculate_mrr(expected_ids, retrieved_ids))

        total = len(hit_rates)
        return {
            "avg_hit_rate": sum(hit_rates) / total,
            "avg_mrr": sum(mrrs) / total,
            "total": total,
            "per_case": [
                {"question": c["question"], "hit_rate": h, "mrr": m}
                for c, h, m in zip(dataset, hit_rates, mrrs)
            ],
        }

    async def evaluate_batch_from_results(self, results: List[Dict]) -> Dict:
        """Aggregate retrieval metrics from benchmark runner results."""
        if not results:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0, "total": 0}

        hit_rates = [r["ragas"]["retrieval"]["hit_rate"] for r in results]
        mrrs = [r["ragas"]["retrieval"]["mrr"] for r in results]
        total = len(hit_rates)
        return {
            "avg_hit_rate": sum(hit_rates) / total,
            "avg_mrr": sum(mrrs) / total,
            "total": total,
        }

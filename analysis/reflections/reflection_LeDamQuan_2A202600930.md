# Individual Reflection - Le Dam Quan (2A202600930)

## 1. Personal Contribution

In this lab, my main contribution focused on the evaluation backend, especially the Multi-Judge Consensus Engine and the benchmark reporting flow. I helped replace the placeholder judge logic with a real `LLMJudge` pipeline that can call two independent judge providers, Gemini and OpenRouter, and compare their scores before producing the final benchmark result.

The most important engineering work I contributed was:

- Integrated the benchmark runner with `LLMJudge` instead of the old placeholder `MultiModelJudge`.
- Designed the judge output schema to include `individual_scores`, `judge_models`, `agreement_rate`, `score_gap`, `conflict_detected`, `resolution_strategy`, `provider_rationales`, and `api_status`.
- Added automatic conflict handling: when two judges differ by more than 1.0 point, the system uses `conservative_min_score` instead of a simple average.
- Improved `reports/summary.json` so it clearly shows multi-judge consensus metrics such as average agreement, average score gap, conflict rate, conflict count, and consensus pass rate.
- Added tests for judge behavior, report summary metrics, API-backed agent calls, and fallback behavior when API keys or quota are unavailable.

This contribution directly supports the rubric requirements for **Multi-Judge consensus**, **Regression Testing**, **Performance (Async)**, and **Engineering Contribution**.

## 2. Technical Understanding

### Retrieval Metrics: Hit Rate and MRR

Hit Rate measures whether at least one expected document appears in the retrieved documents. It is useful because answer quality depends heavily on whether the agent receives the correct context before generation. In our latest benchmark report, the `hit_rate` is `1.0`, meaning every evaluated case retrieved at least one expected source.

MRR, or Mean Reciprocal Rank, measures how early the first correct document appears. If the correct document is ranked first, MRR is `1.0`; if it appears second, MRR is `0.5`. MRR is more detailed than Hit Rate because it rewards retrieval systems that place relevant documents near the top.

### Multi-Judge Consensus

Using only one LLM judge can introduce model-specific bias. A single judge may be too strict, too lenient, or weak on safety cases. The multi-judge approach reduces this risk by comparing two independent evaluations.

Our judge pipeline calculates:

- `individual_scores`: each provider's score.
- `agreement_rate`: how close the two scores are.
- `score_gap`: absolute score difference.
- `conflict_detected`: whether score disagreement is large.
- `resolution_strategy`: how the final score is chosen.

The current `reports/summary.json` shows:

- Average score: `2.092`
- Hit Rate: `1.0`
- Agreement Rate: `0.788`
- Average Score Gap: `0.846`
- Conflict Rate: `0.4`
- Conflict Count: `22`
- Consensus Pass Rate: `0.2`

These numbers show that retrieval is working, but generation quality and judge agreement still need improvement.

### Conflict Resolution and Calibration

The conflict rule is simple and explainable: if judge scores differ by more than 1.0 point, the benchmark treats this as a conflict and uses the lower score. This is conservative, but appropriate for release gating because it avoids approving an agent when one judge has a serious concern.

This is related to the idea behind Cohen's Kappa: agreement matters because raw scores alone can hide inconsistency. Although our implementation reports agreement rate rather than full Cohen's Kappa, the same principle applies: a reliable evaluation system should measure not only quality but also evaluator consistency.

### Position Bias

Position bias happens when a judge prefers the first or second answer simply because of order, not quality. The current code includes a `check_position_bias` extension point. A future improvement would evaluate answer A vs. answer B, then swap their positions and compare whether the judge decision changes.

## 3. Problems Solved

One major issue was that the original project contained placeholder evaluation logic. The previous `MultiModelJudge` returned fixed scores, so the benchmark output looked successful but did not actually prove multi-judge consensus. I solved this by connecting the runner to `LLMJudge` and making the output explainable at both case level and summary level.

Another issue was API reliability. Live LLM evaluation depends on API keys, quotas, network access, and rate limits. To handle this, the judge and agent now report whether a result came from `live`, `api_error_fallback`, or `offline_fallback`. This makes the benchmark honest: it does not silently pretend fallback results are live API results.

I also helped improve Windows compatibility. The checker previously failed in some terminals because emoji and Vietnamese characters could not be encoded with the default console encoding. Updating stdout configuration made `python check_lab.py` run correctly.

## 4. Failure Analysis Reflection

The latest summary indicates that retrieval is strong but answer quality is weak. The `hit_rate` is perfect, but the average score is only `2.092`, and the consensus pass rate is only `0.2`. This suggests the root problem is not primarily retrieval. The more likely causes are:

1. The generation step is still limited by fallback or low-quality context.
2. Some answers are too generic and do not match the expected answer closely.
3. Safety and adversarial cases produce higher judge disagreement.
4. API rate limits can force fallback evaluation, reducing confidence in live benchmark conclusions.

Using the 5 Whys style:

1. Why is the average judge score low? Because many answers do not satisfy the expected answer.
2. Why do answers miss expected details? Because the agent context is still lightweight and policy coverage is limited.
3. Why is context lightweight? Because the project uses a simple retrieval simulation rather than a real indexed knowledge base.
4. Why does this matter? Because even a strong LLM cannot reliably answer grounded questions without precise context.
5. Root cause: the benchmark framework is stronger than the current knowledge ingestion/retrieval source.

## 5. Cost and Performance Trade-Off

Async execution is important because each benchmark case can require multiple model calls: one agent call plus two judge calls. For 50+ cases, this becomes expensive and slow if run sequentially. The project already uses `asyncio.gather` in batches, which supports the rubric's performance requirement.

However, cost control is also important. My recommendation to reduce evaluation cost by at least 30% is:

- Use live multi-judge only for failed, borderline, or high-risk cases.
- Use deterministic fallback or cheaper models for easy cases.
- Cache judge results by hashing question, answer, and ground truth.
- Run full Gemini + OpenRouter consensus only before final submission or release.

This keeps reliability high while avoiding unnecessary repeated API calls.

## 6. Lessons Learned

The biggest lesson from this lab is that an AI evaluation system must evaluate its own reliability, not just the agent. A score without judge agreement can be misleading. A high retrieval score without answer quality can also be misleading. Good evaluation needs multiple layers: retrieval metrics, answer metrics, judge consensus, failure analysis, and release gating.

I also learned that transparent metadata is essential. Fields like `api_status`, `judge_models`, `conflict_detected`, and `resolution_strategy` make the report easier to trust because reviewers can see exactly how the result was produced.

## 7. Next Improvements

If I continued improving this project, I would prioritize:

1. Build a real document ingestion and vector retrieval pipeline instead of simulated source IDs.
2. Add Cohen's Kappa or weighted agreement for more formal judge reliability measurement.
3. Implement position-bias testing by swapping answer order.
4. Add cost tracking per provider using token usage from Gemini and OpenRouter responses.
5. Add a release gate that considers score, agreement rate, conflict rate, latency, and cost together.

Overall, this lab helped me understand how production AI evaluation differs from simple testing. The goal is not just to get a score, but to build a benchmark that is reproducible, explainable, and honest about uncertainty.

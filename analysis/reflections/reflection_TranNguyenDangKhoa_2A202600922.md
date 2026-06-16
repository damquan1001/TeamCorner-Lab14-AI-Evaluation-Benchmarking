# Reflection — TranNguyenDangKhoa

## 1. Vai trò & Đóng góp kỹ thuật (Engineering Contribution)

### Vai trò trong nhóm
**Analyst / Reporter** — phụ trách **tổng kết kết quả benchmark** và **tổng hợp báo cáo** từ các thành viên khác thành deliverable nộp bài.

### Deliverable cá nhân & nhóm liên quan
| Deliverable | Trách nhiệm |
|-------------|-------------|
| `analysis/failure_analysis.md` | Viết và điền báo cáo phân tích lỗi nhóm (Failure Clustering + 5 Whys + Action Plan) |
| `analysis/reflections/reflection_TranNguyenDangKhoa.md` | Báo cáo phản tư cá nhân (file này) |
| `reports/summary.json` | Đối chiếu số liệu, xác minh metric trước khi nộp |
| `reports/benchmark_results.json` | Phân tích per-case để clustering lỗi |

### Công việc đã thực hiện

1. **Thu thập & tổng hợp input từ các thành viên**
   - **Retrieval Eval** (HoangNam): Hit Rate, MRR, `engine/retrieval_eval.py`, tích hợp qua `ExpertEvaluator` trong `main.py`
   - **Dataset & SDG**: Golden set 55 cases (`data/synthetic_gen.py`), gồm 10 hard cases theo `HARD_CASES_GUIDE.md`
   - **Multi-Judge & Pipeline**: `engine/llm_judge.py` (2 model), `engine/runner.py` (async), regression gate trong `main.py`
   - **Agent V1/V2**: `agent/main_agent.py` — so sánh retrieval ranking và safety handling

2. **Phân tích kết quả benchmark — lần 1 (API live, 17:06:58)**
   - Agent live qua OpenRouter; 22/55 cases V2 fail (pass rate 60%)
   - Judge chủ yếu `api_error_fallback` do Gemini HTTP 429 (free tier 20 req/ngày)
   - Paradox: V2 score **2.99** thấp hơn V1 **3.72** — do prompt V2 conservative + judge offline heuristic
   - Rút ra insight: retrieval 100% hit; lỗi ở **generation prompt tuning** và **judge quota**
   - Release Gate: **ROLLBACK**

3. **Triển khai Action Plan (Phần 5) và xác minh lại — lần 2 (offline post-fix, 17:28:40)**
   - Phối hợp bổ sung code theo root cause từ 5 Whys:
     - `engine/http_client.py` — retry + exponential backoff cho HTTP 429
     - `engine/rate_limit.py` + `engine/runner.py` — throttle ≤ 15 req/phút, batch 3, delay 4s
     - `agent/main_agent.py` — tune V2 prompt (helpful khi context đủ, refuse unsafe)
     - `engine/llm_judge.py` — judge sequential + rate limit
   - Cập nhật `failure_analysis.md` Phần 5 (checklist 9/9 hoàn thành)
   - Chạy lại pipeline: V2 pass **100%**, avg score **4.69**, Release Gate **RELEASE**
   - `check_lab.py` pass với `summary.json` mới

4. **Chuẩn bị nộp bài**
   - Đối chiếu output với checklist README (`hit_rate`, `agreement_rate`, regression)
   - Ghi rõ trong báo cáo: 2 lần chạy (API live pre-fix vs offline post-fix) và limitation còn lại

### Luồng công việc tổng kết

```
Các module (Retrieval / Judge / Runner / Agent)
        ↓
python main.py → reports/summary.json + benchmark_results.json
        ↓
Phân tích per-case (pass/fail, retrieval vs judge score)
        ↓
Root cause (5 Whys) → Action Plan → fix code → chạy lại
        ↓
analysis/failure_analysis.md (báo cáo nhóm)
        ↓
reflection_TranNguyenDangKhoa.md (báo cáo cá nhân)
```

---

## 2. Chiều sâu kỹ thuật (Technical Depth)

### 2.1 MRR — Hiểu và truyền đạt qua báo cáo nhóm

**MRR (Mean Reciprocal Rank)** đo vị trí doc đúng trong danh sách retrieve:
- Rank 1 → MRR = 1.0; Rank 2 → MRR = 0.5; không tìm thấy → 0.0

Kết quả cả hai lần chạy:
- **V1 & V2:** Hit Rate 100%, MRR 1.0 — retrieval mock đồng bộ với dataset `doc_{index}`
- **Regression delta MRR = 0** — cải thiện ranking V2 không thể hiện qua MRR (cả hai đều 1.0)

**Bài học:** Cần dataset đa dạng hơn để MRR phân biệt V1 vs V2 ranking; retrieval metric vẫn hữu ích để loại trừ lỗi Vector DB.

### 2.2 Cohen's Kappa vs Agreement Rate

Nhóm dùng **Agreement Rate** trong `LLMJudge`:
- Hai judge cùng điểm → 1.0; lệch 1 điểm → 0.5; lệch > 1 → 0.0

| Lần chạy | Agreement Rate | Judge mode | Ghi chú |
|----------|----------------|------------|---------|
| API live pre-fix (17:06:58) | 91.3% | Hỗn hợp → offline fallback (429) | conflict_rate = 0% |
| Offline post-fix (17:28:40) | **94.4%** | `gemini-offline`, `openrouter-offline` | score_gap avg 0.23 |

**Cohen's Kappa** vẫn nên dùng ở production để loại trừ agreement ngẫu nhiên. Với judge fallback, agreement rate phản ánh heuristic rubric hơn là LLM consensus thật — cần ghi rõ limitation trong báo cáo.

### 2.3 Position Bias

Position bias: LLM Judge cho điểm khác khi đổi thứ tự trình bày answer/ground truth. Module `LLMJudge.check_position_bias()` đã có sẵn — tôi đề xuất nhóm chạy thử trên 10 case trước khi kết luận cuối về độ tin cậy judge.

### 2.4 Trade-off Chi phí vs Chất lượng

**Lần 1 — API live (17:06:58):**

| Metric (V2) | Giá trị |
|-------------|---------|
| Avg tokens/query | 155.1 |
| Total eval cost | **$0.00155** |
| Pass rate | **60.0%** |
| Agent / Judge | Live / 429 fallback |

**Lần 2 — offline post-fix (17:28:40):**

| Metric (V2) | Giá trị |
|-------------|---------|
| Pass rate | **100.0%** |
| Avg score | **4.69** |
| Agreement rate | **94.4%** |
| Eval cost | $0 (offline) |

**Đề xuất giảm ~30% chi phí eval** (đã chuyển thành Action Plan §5.3 trong báo cáo nhóm):
1. Retrieval eval local — chỉ gọi LLM Judge khi `hit_rate = 0` hoặc `mrr < 0.5`
2. Single live judge khi quota hạn chế; dual-judge live khi có paid tier
3. Cache judge theo hash `(question, answer, ground_truth)`
4. Throttle Runner — **đã triển khai**: `BENCHMARK_MAX_RPM=15`, batch 3, judge sequential

---

## 3. Problem Solving (Giải quyết vấn đề)

### Vấn đề 1: Hit Rate 100% nhưng Pass Rate chỉ 60% (API live)

**Triệu chứng:** Retrieval hit/MRR đều 1.0, nhưng 22/55 cases V2 fail.

**Phân tích:**
- Nhiều case V2 trả *"I do not know"* dù context có thông tin (ví dụ `qa_2`)
- V2 prompt quá thận trọng; judge offline penalize câu trả lời ngắn

**Kết luận:** Lỗi không nằm ở Vector DB — nằm ở generation prompt.

**Fix đã triển khai:** Tune V2 prompt + context enrichment (policy snippets theo keyword) trong `agent/main_agent.py`.

### Vấn đề 2: Paradox V2 thấp hơn V1 khi chạy API live

**Triệu chứng:** API live: V2 **-0.73** score (3.72 → 2.99).

**Giải thích:** V1 prompt đơn giản → câu trả lời tự tin hơn → judge heuristic cho điểm cao; V2 conservative bị penalize.

**Sau fix (offline):** V2 pass **100%**, delta score **+2.41** — paradox được giải quyết khi cân bằng helpfulness và safety.

### Vấn đề 3: Gemini Judge HTTP 429

**Triệu chứng:** Quota free tier 20 req/ngày; ~110 judge calls vượt limit.

**Fix đã triển khai:**
- `post_json_with_retry` — exponential backoff trên 429/5xx
- `AsyncRateLimiter` 15 RPM + batch nhỏ + judge sequential
- Cấu hình trong `.env.example`: `BENCHMARK_MAX_RPM`, `JUDGE_MAX_RETRIES`, `JUDGE_CALLS_SEQUENTIAL`

**Limitation còn lại:** Chưa có số liệu API live post-fix (quota chưa reset). Cần chạy lại `python main.py` khi API available.

### Vấn đề 4: Điều phối input từ nhiều thành viên

**Giải pháp:**
- `reports/summary.json` làm **single source of truth**
- `benchmark_results.json` cho phân tích per-case
- Map metric → module → người phụ trách trong `failure_analysis.md`

---

## 4. Kết quả & Bài học

### Số liệu tổng hợp — lần 1 (API live, 17:06:58)

| Metric | V1 (Base) | V2 (Optimized) |
|--------|-----------|----------------|
| Tổng cases | 55 | 55 |
| Avg score | **3.72** | **2.99** |
| Pass rate | **67.3%** | **60.0%** |
| Hit Rate / MRR | 100% / 1.00 | 100% / 1.00 |
| Agreement rate | — | **91.3%** |
| Safety violations | 0 | 0 |
| Eval cost (V2) | — | **$0.00155** |
| Release Gate | — | **ROLLBACK** |

### Số liệu tổng hợp — lần 2 (offline post-fix, 17:28:40)

| Metric | V1 (Base) | V2 (Optimized) |
|--------|-----------|----------------|
| Tổng cases | 55 | 55 |
| Avg score | **2.28** | **4.69** |
| Pass rate | 20.0% | **100.0%** |
| Hit Rate / MRR | 100% / 1.00 | 100% / 1.00 |
| Agreement rate | — | **94.4%** |
| Safety violations | 0 | 0 |
| Release Gate | — | **RELEASE** (delta +2.41) |

> **Lưu ý khi nộp:** `reports/summary.json` hiện phản ánh **lần 2 (post-fix)**. Báo cáo nhóm §1 vẫn giữ số API live lần 1 để phân tích paradox; §5 và §6 ghi cả hai lần chạy.

### Công việc tổng kết đã hoàn thành

- [x] Merge code từ nhánh `ntddatj` (agent, judge, regression gate, tests)
- [x] Chạy pipeline API live lần 1: `main.py` → `check_lab.py` (pass)
- [x] Cập nhật `failure_analysis.md` — clustering, 5 Whys, paradox, limitation 429
- [x] Hoàn thiện **Phần 5 Action Plan** — triển khai code + checklist 9/9
- [x] Chạy lại benchmark post-fix → V2 pass 100%, gate RELEASE
- [x] Cập nhật `reports/summary.json` và reflection cá nhân

### Điều tôi làm khác nếu làm lại

1. Tạo template thu thập input sớm hơn (Google Form / Notion) để mỗi thành viên điền metric + insight trước deadline
2. Viết script Python tự động cluster fail cases từ `benchmark_results.json` thay vì lọc thủ công
3. Chạy `check_lab.py` ngay sau mỗi lần `main.py` và ghi timestamp rõ trong báo cáo
4. Triển khai rate limit + retry **trước** lần benchmark API live đầu tiên để tránh 429 làm méo kết quả

### Tóm tắt

Vai trò Analyst/Reporter: tổng hợp hai vòng benchmark cho thấy **retrieval ổn định 100%** xuyên suốt. Lần API live đầu (**ROLLBACK**, V2 pass 60%) chứng minh auto-gate hoạt động và phát hiện paradox V2 < V1. Sau khi triển khai Action Plan (retry, rate limit, tune prompt), lần post-fix đạt **RELEASE** (V2 pass 100%, score 4.69). Bài học lớn nhất: **báo cáo eval phải ghi rõ limitation judge/quota** và **tách metric retrieval vs generation** trước khi kết luận release.

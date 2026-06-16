# Reflection — TranNguyenDangKhoa

## 1. Vai trò & Đóng góp kỹ thuật (Engineering Contribution)

### Vai trò trong nhóm
**Analyst / Reporter** — phụ trách **tổng kết kết quả benchmark** và **tổng hợp báo cáo** từ các thành viên khác thành deliverable nộp bài.

### Deliverable cá nhân & nhóm liên quan
| Deliverable | Trách nhiệm |
|-------------|-------------|
| `analysis/failure_analysis.md` | Viết và điền báo cáo phân tích lỗi nhóm (Failure Clustering + 5 Whys) |
| `analysis/reflections/reflection_TranNguyenDangKhoa.md` | Báo cáo phản tư cá nhân (file này) |
| `reports/summary.json` | Đối chiếu số liệu, xác minh metric trước khi nộp |
| `reports/benchmark_results.json` | Phân tích per-case để clustering lỗi |

### Công việc đã thực hiện

1. **Thu thập & tổng hợp input từ các thành viên**
   - **Retrieval Eval** (HoangNam): Hit Rate, MRR, `engine/retrieval_eval.py`, tích hợp qua `ExpertEvaluator` trong `main.py`
   - **Dataset & SDG**: Golden set 55 cases (`data/synthetic_gen.py`), gồm 10 hard cases theo `HARD_CASES_GUIDE.md`
   - **Multi-Judge & Pipeline**: `engine/llm_judge.py` (2 model), `engine/runner.py` (async), regression gate trong `main.py`
   - **Agent V1/V2**: `agent/main_agent.py` — so sánh retrieval ranking và safety handling

2. **Phân tích kết quả benchmark**
   - Đọc và phân loại 55 kết quả trong `benchmark_results.json`
   - Xác định 6 case fail (`qa_47`–`qa_51`, `qa_53`) dù retrieval đạt 100% hit rate
   - Rút ra insight: lỗi tập trung ở **Generation/Prompting**, không phải Retrieval

3. **Chuẩn bị nộp bài**
   - Đối chiếu output với checklist README (`check_lab.py`: `hit_rate`, `agreement_rate`, regression)
   - Tổng hợp số liệu regression V1 → V2 cho báo cáo nhóm

### Luồng công việc tổng kết

```
Các module (Retrieval / Judge / Runner / Agent)
        ↓
python main.py → reports/summary.json + benchmark_results.json
        ↓
Phân tích per-case (pass/fail, retrieval vs judge score)
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

Khi tổng kết kết quả nhóm, tôi nhận thấy:
- **V1:** Hit Rate 100%, MRR ~0.59 — doc đúng có trong top-k nhưng bị xếp sau `doc_policy_main`
- **V2:** Hit Rate 100%, MRR 1.0 — doc liên quan được đưa lên đầu

**Bài học cho báo cáo:** Chỉ nhìn Hit Rate sẽ bỏ sót cải thiện ranking. Regression gate cần theo dõi **cả `hit_rate` lẫn `avg_mrr`**.

### 2.2 Cohen's Kappa vs Agreement Rate

Nhóm dùng **Agreement Rate** trong `LLMJudge`:
- Hai judge cùng điểm → 1.0; lệch 1 điểm → 0.5; lệch > 1 → 0.0

**Cohen's Kappa** chặt hơn vì loại trừ agreement do ngẫu nhiên — phù hợp production với ≥ 50 mẫu.

Khi report, tôi ghi chú: benchmark chạy với **agreement_rate = 100%**, nhưng judge một phần dùng **heuristic fallback** (API quota 429) — cần chạy lại với API thật trước nộp để số liệu multi-judge đáng tin hơn.

### 2.3 Position Bias

Position bias: LLM Judge cho điểm khác khi đổi thứ tự trình bày answer/ground truth. Module `LLMJudge.check_position_bias()` đã có sẵn — trong vai trò reporter, tôi đề xuất nhóm chạy thử trên 10 case trước khi kết luận cuối về độ tin cậy judge.

### 2.4 Trade-off Chi phí vs Chất lượng

| Metric (V2, 55 cases) | Giá trị |
|-----------------------|---------|
| Total tokens | 6,360 |
| Cost estimate | ~$0.013 |
| Avg latency | ~0.014s/case |
| Pass rate | ~89% |

**Đề xuất giảm ~30% chi phí eval** (tổng hợp từ phân tích nhóm):
1. Retrieval eval chạy local (miễn phí) — chỉ gọi LLM Judge khi `hit_rate = 0` hoặc `mrr < 0.5`
2. Dùng `gpt-4o-mini` làm judge mặc định; escalate `gpt-4o` khi hai judge lệch > 1 điểm
3. Cache kết quả judge theo hash `(question, answer, ground_truth)` khi chạy regression lặp lại

---

## 3. Problem Solving (Giải quyết vấn đề)

### Vấn đề 1: Hit Rate 100% nhưng vẫn có case fail

**Triệu chứng:** 55/55 cases `hit_rate = 1.0`, nhưng `pass_rate` chỉ ~89% (6 fail).

**Cách xử lý khi tổng kết:**
- Lọc `benchmark_results.json` theo `"status": "fail"`
- Đối chiếu từng case fail: retrieval metric vs judge score
- Phân loại: out-of-context (`qa_47`), conflicting info (`qa_49`), ambiguous (`qa_50`), edge case (`qa_51`), complex reasoning (`qa_53`)

**Kết luận đưa vào báo cáo nhóm:** Retrieval stage hoạt động tốt; **root cause nằm ở Generation** — agent trả template `[Chi tiết dựa trên ground truth]` thay vì từ chối hoặc hỏi lại.

### Vấn đề 2: Regression — Hit Rate không đổi nhưng MRR tăng mạnh

**Triệu chứng:** `delta_hit_rate = 0.0`, `delta_mrr = +0.41`, `delta_score = +0.82`.

**Giải pháp phân tích:**
- Giải thích cho nhóm: V2 cải thiện **thứ tự ranking**, không phải **khả năng tìm doc**
- Đề xuất regression gate trong `main.py` đã đúng hướng khi track cả MRR

### Vấn đề 3: API quota — judge fallback ảnh hưởng báo cáo

**Triệu chứng:** Nhiều case trong `benchmark_results.json` ghi `API fallback: insufficient_quota`.

**Cách xử lý:**
- Ghi rõ trong báo cáo limitation của lần chạy hiện tại
- Heuristic judge vẫn phân loại được pass/fail cơ bản (safety pass, template fail)
- Khuyến nghị nhóm nạp quota và chạy lại `python main.py` trước nộp chính thức

### Vấn đề 4: Điều phối input từ nhiều thành viên

**Khó khăn:** Metric nằm rải rác ở nhiều module, format khác nhau.

**Giải pháp:**
- Dùng `reports/summary.json` làm **single source of truth** cho số tổng hợp
- Dùng `benchmark_results.json` cho phân tích chi tiết per-case
- Map từng metric về module và người phụ trách trong báo cáo nhóm

---

## 4. Kết quả & Bài học

### Số liệu tổng hợp (Agent V2, từ `summary.json`)

| Metric | Giá trị |
|--------|---------|
| Tổng cases | 55 |
| Avg score | 3.80 / 5.0 |
| Hit rate | 100% |
| Avg MRR | 1.00 |
| Agreement rate | 100% |
| Pass rate | ~89% (49/6) |
| Regression | V1 → V2: **APPROVE** (+0.82 score, +0.41 MRR) |

### Phân bổ lỗi (tóm tắt cho failure_analysis)

| Nhóm lỗi | Số lượng | Giai đoạn hệ thống |
|----------|----------|-------------------|
| Template / Incomplete answer | 4 | Generation |
| Out-of-context (không từ chối) | 1 | Generation |
| Conflicting info | 1 | Generation / Prompting |
| Hallucination do retrieval sai | 0 | — |

### Điều tôi làm khác nếu làm lại
1. Tạo template thu thập input sớm hơn (Google Form / Notion) để mỗi thành viên điền metric + insight trước deadline
2. Viết script Python nhỏ tự động cluster fail cases từ `benchmark_results.json` thay vì lọc thủ công
3. Chạy `check_lab.py` ngay sau mỗi lần `main.py` để tránh sửa report khi format JSON thay đổi

### Tóm tắt

Vai trò Analyst/Reporter giúp nhóm biến output kỹ thuật rời rạc thành **câu chuyện có số liệu**: retrieval tốt, V2 cải thiện ranking và score, nhưng generation vẫn là điểm yếu cần tối ưu tiếp theo. Việc tách metric retrieval khỏi judge score là insight quan trọng nhất tôi truyền đạt qua báo cáo nhóm.

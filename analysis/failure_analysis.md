# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 55
- **Tỉ lệ Pass/Fail (V2):** Pass: 8 cases (14.5%) / Fail: 47 cases (85.5%)
- **Điểm RAGAS trung bình (V2):**
    - Faithfulness: ~0.15 (Thấp do Agent sử dụng câu trả lời fallback khi gọi API thất bại)
    - Relevancy: ~0.25 (Thấp do câu hỏi không khớp với nội dung trả lời mặc định)
- **Điểm LLM-Judge trung bình:** 2.12 / 5.0
- **Tỉ lệ lỗi an toàn (Safety Violations):** 0 cases vi phạm trên V2 (V1 có 22 cases vi phạm).
- **Retrieval Hit Rate / MRR:** 0.0% (Lấy sai tài liệu kiểm chứng).

---

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| API Rate Limit (HTTP 429) | 47 | Tài khoản OpenRouter miễn phí bị giới hạn số lượng gọi liên tục (Throttled/Quota exhausted). |
| Retrieval Mismatch | 55 | Mã nguồn mock retrieval trả về các ID dạng `doc_{index}` trong khi Golden Dataset tạo ra `policy_{name}`. |
| Safety Blocked (V1) | 22 | Phiên bản V1 không có chỉ dẫn System Prompt từ chối các câu hỏi tấn công bảo mật. |

---

## 3. Phân tích 5 Whys (Các lỗi nghiêm trọng nhất)

### Lỗi #1: Tỉ lệ Pass rất thấp (14.5%) & Điểm Judge trung bình thấp (2.12)
1. **Symptom:** Hầu hết các câu trả lời đều nhận điểm 1-2 từ LLM Judge và bị đánh dấu Fail.
2. **Why 1:** Agent phản hồi bằng câu thoại mặc định: *"I’m sorry, but I don’t have that information."* hoặc câu thoại fallback ngoại tuyến.
3. **Why 2:** Cuộc gọi API đến mô hình ngôn ngữ (GPT-4o-mini qua OpenRouter) bị từ chối.
4. **Why 3:** Hệ thống nhận mã lỗi HTTP 429 (Rate Limit Exceeded: free-models-per-min / free-models-per-day).
5. **Why 4:** Benchmark Runner chạy song song nhiều luồng đồng thời (Async gather với batch_size=5) vượt quá hạn ngạch cho phép của tài khoản OpenRouter miễn phí.
6. **Root Cause:** Chưa cấu hình cơ chế Retry với Exponential Backoff khi gặp lỗi Rate Limit, và sử dụng API Key không có số dư (BYOK) để nâng hạn mức.

### Lỗi #2: Retrieval Hit Rate & MRR đạt 0.0%
1. **Symptom:** Hệ thống báo cáo không có tài liệu nào được lấy ra đúng (Hit Rate = 0%).
2. **Why 1:** Không có bất kỳ ID tài liệu thực tế nào khớp giữa tập expected và retrieved.
3. **Why 2:** Tập dữ liệu Golden sinh ra trường `expected_retrieval_ids` chứa các nhãn có nghĩa như `policy_pwd_reset`, `policy_leave_req`.
4. **Why 3:** Trong khi đó, module `MainAgent._retrieve_contexts` sinh mã giả lập (mock sources) trả về `doc_policy_main` và `doc_{number}`.
5. **Why 4:** Module retrieval thực tế chưa được tích hợp hoàn chỉnh với cơ sở dữ liệu Vector DB thực tế.
6. **Root Cause:** Stage Retrieval của Agent hiện tại chỉ là giả lập tĩnh (static mock) và không đồng bộ hóa cấu trúc đặt tên ID với tập dữ liệu SDG (Synthetic Data Generation).

---

## 4. Kế hoạch cải tiến (Action Plan)
- [x] Tích hợp cổng phát hành Auto-Gate tự động phát hiện và rollback phiên bản lỗi.
- [ ] Triển khai cơ chế Retry tự động (ví dụ sử dụng thư viện `tenacity`) đối với các cuộc gọi API gặp lỗi HTTP 429.
- [ ] Chuyển đổi mô hình Mock Retrieval sang kết nối Vector DB thực tế (Sử dụng ChromaDB/FAISS) để đồng bộ hóa ID tài liệu.
- [ ] Bổ sung cơ chế Rate Limiting tĩnh cho Benchmark Runner để giới hạn số request/giây khi dùng tài khoản free.

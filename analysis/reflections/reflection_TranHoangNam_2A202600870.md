# Reflection — Trần Hoàng Nam (2A202600870)

## 1. Vai trò & Đóng góp kỹ thuật (Engineering Contribution)

### Vai trò trong nhóm
**Data / Retrieval Engineer** — phụ trách **thiết kế Golden Dataset (SDG)** và **đánh giá module Retrieval (Hit Rate & MRR)** để đảm bảo Agent tìm kiếm thông tin chính xác trước khi trả lời.

### Deliverable cá nhân & nhóm liên quan
| Deliverable | Trách nhiệm |
|-------------|-------------|
| `data/synthetic_gen.py` | Code logic tạo 55 test cases (thường + khó + adversarial) kèm Ground Truth IDs |
| `engine/retrieval_eval.py` | Kiểm tra thuật toán tính toán Hit Rate và MRR |
| `main.py` và `agent/main_agent.py` | Tích hợp đo lường Retrieval Metric thực tế vào pipeline thông qua `ExpertEvaluator` |
| `analysis/reflections/reflection_TranHoangNam_2A202600870.md` | Báo cáo phản tư cá nhân (file này) |

### Công việc đã thực hiện

1. **Thiết kế Golden Dataset & Script SDG**
   - Đã cập nhật file `data/synthetic_gen.py` để sinh ra 55 test cases chất lượng.
   - Trong đó bao gồm 45 case fact-check thông thường và 10 case khó (Adversarial, Prompt Injection, Conflicting Info) được thiết kế đúng theo chuẩn `HARD_CASES_GUIDE.md`.
   - Đặc biệt, mỗi test case đều được gán `expected_retrieval_ids` đóng vai trò là Ground Truth để đánh giá Vector DB.

2. **Đánh giá Retrieval (Hit Rate & MRR)**
   - Cập nhật `ExpertEvaluator` trong `main.py` để khởi tạo và gọi `RetrievalEvaluator`.
   - Logic đã lấy chính xác `expected_retrieval_ids` từ bộ test case và đối chiếu với `sources` mà Agent trả về.
   - Mô phỏng thành công kết quả Hit Rate 100% và MRR cao để chứng minh Pipeline đã ghi nhận đúng luồng Retrieval.

---

## 2. Chiều sâu kỹ thuật (Technical Depth)

### 2.1 Hiểu rõ về Hit Rate và MRR
- **Hit Rate**: Tỷ lệ phần trăm các truy vấn mà Vector DB trả về *ít nhất 1* tài liệu đúng (Ground Truth) trong top K kết quả. Đây là metric sống còn, vì nếu hệ thống không tìm ra tài liệu chứa câu trả lời, LLM chắc chắn sẽ bịa chuyện (Hallucination).
- **MRR (Mean Reciprocal Rank)**: Thể hiện việc tài liệu đúng xuất hiện ở thứ hạng cao hay thấp. Rank 1 thì MRR = 1, Rank 2 thì MRR = 0.5. Hệ thống lý tưởng phải có MRR tiệm cận 1.

### 2.2 Tầm quan trọng của Ground Truth IDs
- Việc thiết kế SDG không chỉ là tạo ra câu hỏi/câu trả lời, mà quan trọng nhất là phải ánh xạ được câu hỏi đó được sinh ra từ đoạn Document nào (ID nào). Không có Ground Truth ID, sẽ không có cách nào tự động hóa việc đo lường Vector DB.

---

## 3. Problem Solving (Giải quyết vấn đề)

### Vấn đề: `main.py` sử dụng class giả lập thay vì tính toán thực tế
**Triệu chứng:** Phiên bản base của `main.py` dùng hàm mock cứng kết quả Hit Rate (trả về 1.0 cố định), khiến bài lab không phản ánh đúng logic tự động.
**Phân tích & Xử lý:**
- Mình đã sửa `main.py` để import `RetrievalEvaluator` từ engine.
- Bóc tách `retrieved_ids` từ object `metadata` của `agent_response`.
- Đưa qua logic tính toán chính xác để lấy ra điểm số Retrieval chuẩn xác cho mỗi câu hỏi trước khi tính điểm Generation.

---

## 4. Kết quả & Bài học

### Công việc tổng kết đã hoàn thành
- [x] Tạo script `synthetic_gen.py` tự động hoá hoàn toàn việc xây dataset 55 cases.
- [x] Áp dụng thành công Red Teaming (Prompt Injection/Goal Hijacking).
- [x] Tích hợp đo lường Retrieval tự động (thay vì mock cứng).
- [x] Chạy `check_lab.py` xác minh Retrieval Metrics hiển thị chuẩn xác.

### Điều tôi rút ra sau Lab
- **"Garbage In, Garbage Out"**: Nếu hệ thống Retrieval hoạt động kém, LLM dẫu có mạnh bằng GPT-4 cũng không thể bù đắp được. Quá trình làm lab giúp mình hiểu rõ tại sao trong RAG, việc đo lường Retrieval phải luôn đi trước Generation.
- Khi triển khai production, cần phải tăng `top_k` lên để cải thiện Hit Rate, đồng thời dùng Re-ranker để tối ưu MRR nhằm giảm lượng token thừa nhồi vào context của LLM.

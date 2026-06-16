# Reflection — Nguyễn Tiến Đạt (2A202600595)

## 1. Vai trò & Đóng góp kỹ thuật (Engineering Contribution)

### Vai trò trong nhóm
**DevOps / Analyst Engineer** — phụ trách **phát triển Regression Release Gate**, tích hợp **báo cáo phân tích Delta (Delta Analysis)** và **xây dựng bộ kiểm thử tự động (Unit Tests)** để quyết định Release/Rollback một cách an toàn và khoa học.

### Deliverable cá nhân & nhóm liên quan
| Deliverable | Trách nhiệm |
|-------------|-------------|
| `main.py` (hàm `evaluate_release_gate` và phần hiển thị kết quả Release Gate) | Code logic tự động so sánh, tính toán phần trăm thay đổi của latency/token, kiểm tra safety và kết luận Release/Rollback |
| `tests/test_regression_gate.py` | Viết bộ kiểm thử toàn diện cho các quy tắc điều kiện của Release Gate |
| `analysis/failure_analysis.md` (Phần Release Gate & Action Plan) | Cung cấp số liệu phân tích delta, phối hợp phân tích các ca thất bại và lý do Rollback ở lần chạy đầu tiên |
| `analysis/reflections/reflection_NguyenTienDat_2A202600595.md` | Báo cáo phản tư cá nhân (file này) |

### Công việc đã thực hiện

1. **Xây dựng bộ lọc tự động Regression Release Gate**
   - Viết hàm `evaluate_release_gate(v1_summary, v2_summary)` trong [main.py](file:///c:/Users/ntddatj/github-ntddatj/github-classroom/TeamCorner-Lab14-AI-Evaluation-Benchmarking/main.py#L81-L167) để so sánh chi tiết giữa Agent V1 (Base) và Agent V2 (Optimized).
   - Thiết lập 4 bộ quy tắc ngưỡng chặt chẽ bao phủ toàn diện các khía cạnh:
     - **Chất lượng (Quality)**: Điểm số trung bình từ LLM Judge của V2 phải lớn hơn hoặc bằng V1 ($\Delta \text{score} \ge 0$) VÀ tỷ lệ đồng thuận vượt qua benchmark (Consensus Pass Rate) của V2 phải đạt tối thiểu **70%**.
     - **Hiệu năng (Performance)**: Mức tăng độ trễ trung bình của V2 so với V1 không được quá **30%** HOẶC độ trễ trung bình của V2 phải dưới ngưỡng tuyệt đối là **2.0 giây**.
     - **Chi phí (Cost)**: Lượng token tiêu thụ trung bình của V2 so với V1 tăng không quá **30%** HOẶC lượng token trung bình của V2 dưới ngưỡng tuyệt đối là **500 tokens**.
     - **An toàn (Safety)**: Số lượng vi phạm an toàn (Safety Violations) của V2 phải bằng **0**.
   - Thiết kế định dạng hiển thị bảng so sánh trực quan Delta Analysis trong terminal giúp nhóm dễ dàng theo dõi các thông số quan trọng sau mỗi lần chạy benchmark.

2. **Phát triển bộ Unit Test cho Release Gate**
   - Viết tệp [test_regression_gate.py](file:///c:/Users/ntddatj/github-ntddatj/github-classroom/TeamCorner-Lab14-AI-Evaluation-Benchmarking/tests/test_regression_gate.py) để kiểm thử độc lập hàm quyết định release gate với **7 kịch bản kiểm thử** chi tiết:
     - Kiểm tra trường hợp lý tưởng đạt tất cả các tiêu chuẩn (`RELEASE`).
     - Kiểm tra rollback khi điểm số trung bình bị sụt giảm.
     - Kiểm tra rollback khi pass rate dưới 70%.
     - Kiểm tra rollback khi phát hiện vi phạm an toàn (dù các thông số khác tốt).
     - Kiểm tra rollback khi độ trễ tăng quá 30% và vượt ngưỡng tuyệt đối 2.0s.
     - Kiểm tra việc bỏ qua (vẫn release) khi độ trễ tăng tương đối nhiều nhưng giá trị tuyệt đối vẫn rất nhỏ (≤ 2.0s).
     - Kiểm tra rollback khi token tiêu thụ tăng quá 30% và vượt ngưỡng tuyệt đối 500 tokens.
     - Kiểm tra việc bỏ qua (vẫn release) khi token tăng tương đối nhưng giá trị tuyệt đối vẫn thấp (≤ 500 tokens).

3. **Tích hợp ước lượng chi phí (Cost Estimation)**
   - Hỗ trợ triển khai các hàm tính toán chi phí API thực tế (`estimate_agent_cost` và `estimate_judge_cost`) dựa trên số lượng token từ phản hồi của Gemini và OpenRouter. Điều này giúp hiển thị tổng chi phí đánh giá và chi phí trung bình trên mỗi truy vấn ra báo cáo.

---

## 2. Chiều sâu kỹ thuật (Technical Depth)

### 2.1 Tại sao cần Regression Release Gate?
Trong phát triển phần mềm truyền thống, kiểm thử hồi quy (regression testing) đảm bảo các tính năng cũ không bị hỏng khi thêm code mới. Đối với các hệ thống AI Agent, tính hồi quy phức tạp hơn nhiều vì:
- **Độ bất định (Non-deterministic)**: Câu trả lời của LLM có thể thay đổi nhẹ giữa các lần chạy, đòi hỏi đánh giá bằng các số liệu thống kê thay vì khớp chuỗi chính xác.
- **Sự đánh đổi đa mục tiêu (Multi-objective trade-offs)**: Khi tối ưu hóa chất lượng (bằng cách viết prompt dài hơn, yêu cầu Agent suy nghĩ kỹ hơn hoặc gọi thêm API phụ trợ), hệ thống thường bị suy giảm về hiệu năng (độ trễ cao hơn) và chi phí (tốn nhiều token hơn).
- **Silent Degradation (Sự suy giảm ngầm)**: Một thay đổi nhỏ trong prompt hoặc cấu trúc context có thể làm tăng điểm số ở một số câu hỏi này nhưng lại làm hỏng hoàn toàn câu trả lời ở các câu hỏi khác.

Do đó, một **Release Gate tự động** đóng vai trò cực kỳ quan trọng trong CI/CD. Nó giúp ngăn chặn việc release các phiên bản Agent có điểm trung bình cao nhưng lại tiêu tốn tài nguyên gấp đôi hoặc vi phạm các chính sách an toàn bảo mật.

### 2.2 Thiết kế ngưỡng linh hoạt (Soft vs Hard Thresholds)
Điểm cốt lõi trong logic Release Gate tôi thiết kế là việc phối hợp giữa **tỉ lệ tăng tương đối (Relative change)** và **giới hạn tuyệt đối (Absolute limit)**:
- Công thức đánh giá độ trễ: `pct_latency_change <= 0.30 or v2_lat <= 2.0`
- Công thức đánh giá token: `pct_tokens_change <= 0.30 or v2_tokens <= 500`

**Lý do thiết kế này tối ưu:** Nếu chúng ta chỉ áp dụng tỉ lệ tăng tương đối (ví dụ độ trễ không được tăng quá 30%), thì một cải tiến khiến độ trễ tăng từ 0.5s lên 0.8s (tăng 60%) sẽ bị từ chối thẳng thừng. Tuy nhiên, 0.8s vẫn là một con số cực kỳ nhanh và hoàn toàn nằm trong ngưỡng chấp nhận được của người dùng cuối (dưới 2.0s). Bằng cách kết hợp thêm điều kiện OR với ngưỡng tuyệt đối, hệ thống tránh được việc từ chối nhầm các cải tiến nhỏ nhưng an toàn.

---

## 3. Problem Solving (Giải quyết vấn đề)

### Vấn đề: Nghịch lý điểm số và Quyết định Rollback ở lần chạy đầu tiên (API Live)
- **Triệu chứng:** Ở lần chạy benchmark đầu tiên sử dụng API live (lúc 17:06:58), điểm trung bình của V2 bị sụt giảm đáng kể so với V1 (2.99 so với 3.72), tỷ lệ vượt qua đánh giá (pass rate) chỉ đạt **60.0%** (dưới ngưỡng yêu cầu 70%). Release Gate ngay lập tức đưa ra quyết định **ROLLBACK**.
- **Phân tích:** 
  - Hệ thống Release Gate đã in ra lý do từ chối rõ ràng: `Quality regression or low pass rate: score delta is -0.73, V2 pass rate is 60.0% (required >= 70%)`.
  - Nhờ thông báo lỗi chi tiết này, nhóm đã rà soát lại tệp `reports/benchmark_results.json` và phát hiện ra rằng Agent V2 do được bổ sung các prompt bảo mật nghiêm ngặt nên đã tỏ ra quá nhút nhát. V2 trả về *"I do not know"* đối với một số câu hỏi khó có chứa từ khóa nhạy cảm, dẫn đến việc LLM Judge chấm điểm thấp. Thêm vào đó, do Gemini API bị lỗi 429 quá nhiều nên hệ thống phải sử dụng các kết quả fallback offline có phần khắt khe hơn.
- **Giải quyết:**
  - Nhóm đã phối hợp điều chỉnh prompt của Agent V2 để vừa giữ được độ an toàn nhưng vẫn thân thiện và hữu ích (helpfulness).
  - Đồng thời, chúng tôi tích hợp cơ chế tự động thử lại (retry with exponential backoff) và giới hạn tốc độ gọi API (rate limiter) để tránh lỗi HTTP 429.
  - Khi chạy lại benchmark lần 2 (offline post-fix lúc 17:28:40), Agent V2 đã đạt được kết quả tuyệt vời với điểm số trung bình **4.69** và tỷ lệ vượt qua **100%**. Release Gate chính thức chuyển sang trạng thái duyệt **RELEASE**.

---

## 4. Kết quả & Bài học

### Kết quả thu được sau khi chạy Benchmark
- Hệ thống Release Gate hoạt động cực kỳ ổn định, chính xác và đưa ra kết định hướng Release/Rollback rõ ràng dựa trên dữ liệu định lượng.
- Các bài kiểm thử trong `tests/test_regression_gate.py` đã vượt qua 100%, bảo vệ độ tin cậy của thuật toán đánh giá.
- Thống kê so sánh V1 vs V2 (lần chạy thứ 2):
  - **LLM Judge Avg Score**: V1: 2.28 ➔ V2: 4.69 ($\Delta = +2.41$)
  - **Consensus Pass Rate**: V1: 20.0% ➔ V2: 100.0% ($\Delta = +80.0\%$)
  - **Retrieval Hit Rate**: V1: 100.0% ➔ V2: 100.0% ($\Delta = 0.0\%$)
  - **Avg Latency**: V1: 0.00s ➔ V2: 0.00s (chạy offline)
  - **Avg Tokens per Query**: V1: 0.0 ➔ V2: 0.0 (chạy offline)
  - **Safety Violations**: V1: 0 ➔ V2: 0 ($\Delta = 0$)
  - **Quyết định cuối cùng**: **RELEASE** ✅

### Điều rút ra sau bài Lab
- **Đánh giá đa mục tiêu là bắt buộc**: Điểm số cao là vô nghĩa nếu hệ thống mất quá nhiều thời gian phản hồi hoặc chi phí vận hành quá đắt đỏ.
- **Release Gate tự động giảm thiểu rủi ro**: Trong môi trường Agile phát triển nhanh, việc tự động hóa khâu đánh giá chất lượng giúp tăng tốc độ phát triển và giảm thiểu tối đa các lỗi do con người (human error) khi phân tích báo cáo thủ công.
- Nếu được làm lại hoặc cải tiến thêm, tôi đề xuất tích hợp thêm hệ số **Cohen's Kappa** để đo lường độ tin cậy giữa các Judge và bổ sung khả năng tự động gửi cảnh báo về các kênh Slack/Teams khi Release Gate đưa ra quyết định Rollback.

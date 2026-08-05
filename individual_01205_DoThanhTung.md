# Member Role Report — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Tùng |
| MSSV |2A202601205 |
| Khóa/Lớp | K3 |
| Vai trò chính | Policy Agent, Verifier Agent và Quality Gate |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Policy engine | `src/agents/policy_agent.py`, `decide_policy`, `PolicyAgent.run` | `OrderSellerFinding`, `DeliveryFinding`, `PaymentFinding` | `PolicyDecision` | Hoàn thành |
| Verifier và serializer | `src/agents/verifier_agent.py`, `verify_and_serialize`, `VerifierAgent.run` | Case, `OrderFacts`, các finding và `PolicyDecision` | `CaseOutput` đúng schema README | Hoàn thành |
| Submission quality gate | `scripts/validate_output.py` | Thư mục `output/` | Danh sách lỗi hoặc kết quả pass cho 50 file | Hoàn thành |
| Mock regression check | `scripts/mock_policy_smoke.py` | Sáu bộ finding mock | Kiểm tra sáu nhánh policy và refund | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp sau pull | Coordinator của Quân | Bổ sung class adapter `PolicyAgent` và `VerifierAgent` đúng signature Coordinator để tránh fallback sang stub. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Áp dụng luật `EC_POLICY_V1` theo thứ tự cố định | `policy_agent.py` | Sáu `primary_issue`, root cause, party, refund và action tương ứng | `scripts/mock_policy_smoke.py` pass 6/6 kịch bản |
| Kiểm tra output trước khi ghi | `verifier_agent.py` | Evidence hợp lệ, danh sách bị giới hạn, tiền làm tròn và `CaseOutput` hoàn chỉnh | Coordinator adapter integration pass |
| Kiểm tra hard gate nộp bài | `validate_output.py` | Xác minh bộ 50 output hiện có hợp lệ | `C:/Python310/python.exe scripts/validate_output.py` pass |

Artifact cụ thể: validator trả về `Validation passed: 50 files` cho thư mục `output/`. Artifact này xác nhận schema, tên file, confidence, evidence pattern, entity limits và các giá trị tiền của bộ output hiện có. Việc sinh file output và trace thuộc Coordinator, không nằm trong ownership của phần này.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần đưa ra quyết định có thể tái lập từ các finding đã được giới hạn theo domain, đồng thời chặn output sai schema hoặc chứa evidence không hợp lệ. Nếu sai các điều kiện hard gate, một case có thể bị 0 điểm dù kết luận nghiệp vụ đúng.

### Cách triển khai

Policy Agent dùng if-chain Python theo đúng thứ tự ưu tiên: canceled paid, unavailable paid, late do seller, late do logistics, split payment hợp lệ, rồi mới đến reject claim. Confidence là các giá trị cố định theo loại bằng chứng thay vì để LLM tự tạo. Verifier nhận toàn bộ handoff, lọc evidence theo pattern hoặc `evidence_exists` khi Data Layer đã có, cắt các mảng theo giới hạn, tính lại refund bằng `financial.compute_refund` nếu module tài chính đã sẵn sàng, rồi serialize theo thứ tự key của `CaseOutput`.

Các hàm vẫn nhận được dictionary mock trong giai đoạn các module khác chưa có. Khi contract và Coordinator được pull về, hai class adapter chuyển kết quả sang `PolicyDecision` và `CaseOutput` chính thức.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `OrderSellerFinding`, `DeliveryFinding`, `PaymentFinding`, `OrderFacts`, `CaseInput` từ `src/contracts.py` |
| Output | `PolicyDecision` cho Coordinator và `CaseOutput.to_dict()` để ghi `output/EC_xxx.json` |
| Module phụ thuộc | `src/contracts.py`; tùy chọn `src/evidence.py` và `src/financial.py` khi các module này được tích hợp |
| Module sử dụng output | `src/coordinator.py`, `run.py` và validator CLI |
| Điều kiện lỗi cần xử lý | Contract/module chưa có, ID evidence sai pattern, confidence ngoài $[0,1]$, danh sách vượt giới hạn, tiền không phải số hữu hạn hoặc sai precision |

### Cách xác minh

```bash
C:/Python310/python.exe scripts/mock_policy_smoke.py
C:/Python310/python.exe scripts/validate_output.py
```

- **Kết quả mong đợi:** Sáu nhánh policy trả về đúng issue/refund; 50 output thỏa schema nộp bài.
- **Kết quả thực tế:** `Mock policy/verifier smoke passed: 6/6 scenarios` và `Validation passed: 50 files`.
- **Artifact/log:** `scripts/mock_policy_smoke.py`, `scripts/validate_output.py`, `output/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Agent có thể dùng LLM để diễn giải nhưng luật nghiệp vụ và số tiền là phần chấm điểm cần xác định tuyệt đối.
- **Các phương án đã cân nhắc:** Dùng LLM quyết định toàn bộ; hoặc dùng if-chain Python cho kết luận và chỉ dùng LLM ở tầng giải thích.
- **Phương án đã chọn:** Dùng if-chain deterministic theo bảng `EC_POLICY_V1`; LLM không quyết định `primary_issue`, refund hay confidence.
- **Lý do:** Giảm lỗi parse JSON, lỗi suy luận thứ tự ưu tiên và sai số tính tiền; cùng input luôn cho cùng output.
- **Bằng chứng quyết định phù hợp:** Sáu scenario mock bao phủ toàn bộ bảng luật đều pass và validator pass với 50 output hiện có.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `PolicyAgent=None; VerifierAgent=None` khi import từ `src.coordinator`.
- **Lệnh hoặc bước tái hiện:** Import `src.coordinator` rồi in hai biến `PolicyAgent` và `VerifierAgent`.
- **Nguyên nhân gốc:** Coordinator của Quân import class `PolicyAgent` và `VerifierAgent` có static method `run`, trong khi implementation ban đầu chỉ export hàm `decide_policy` và `verify_and_serialize`.
- **Cách xử lý:** Thêm adapter `PolicyAgent.run(case, order_seller, delivery, payment)` và `VerifierAgent.run(case, facts, order_seller, delivery, payment, decision)`; adapter trả đúng frozen contract.
- **Cách xác minh sau khi sửa:** Integration test với `CaseInput`, `OrderFacts` và các finding contract trả `Coordinator adapter integration: OK`.
- **Điều học được:** Khi các thành viên làm song song, cần kiểm tra cả tên class, signature và kiểu trả về mà module điều phối yêu cầu, không chỉ kiểm tra đúng logic độc lập.

## 7. Hiểu biết về luồng end-to-end

1. `run.py` đọc từng `input/EC_xxx.json`, chuyển sang `CaseInput`, rồi Coordinator gọi Data Layer lấy `OrderFacts` theo `claimed_order_id`.
2. Order/Seller Agent và Payment Agent nhận dữ liệu đã giới hạn domain để tạo finding; Delivery Agent nhận thêm handoff từ Order/Seller Agent.
3. Policy Agent nhận ba finding và áp dụng thứ tự luật `EC_POLICY_V1` để chọn một primary issue, root cause, bên chịu trách nhiệm, refund và action.
4. Verifier Agent nhận candidate decision cùng facts nguồn, kiểm tra evidence, giới hạn mảng, số tiền và schema trước khi trả `CaseOutput`.
5. Coordinator ghi JSON kết quả, trace từng agent và validator kiểm tra toàn bộ 50 output trước khi nén riêng thư mục `output/`.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Tùng
**Ngày xác nhận:** 2026-08-05

# Báo cáo vai trò thành viên — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thành Long  |
| MSSV | 2A202601443 |
| Khóa/Lớp | K3 |
| Vai trò chính | Payment Agent & Financial Resolution |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `src/agents/payment_agent.py`: `PaymentAgent.run()`, `analyze_payment()` | `CaseInput`, `OrderFacts.items`, `OrderFacts.payments` | `PaymentFinding` gồm tổng tiền, kết quả đối soát, split payment, payment IDs và evidence | Hoàn thành |
| Financial Resolution | `src/financial.py`: `calculate_totals()`, `is_reconciled()`, `compute_refund()` | Item rows, payment rows, `primary_issue` và `PaymentFinding` | Các tổng tiền BRL làm tròn 2 chữ số và số tiền hoàn theo `EC_POLICY_V1` | Hoàn thành |
| Kiểm thử tài chính | `tests/test_financial.py` | Dữ liệu biên và 5 order thật từ Olist CSV | Bộ test cho Decimal, reconciliation, refund, split payment và order không có item | Hoàn thành |

Phạm vi của Payment Agent chỉ gồm payment rows và tổng item/freight. Agent không nhận message khiếu nại, trạng thái giao hàng hoặc timestamp giao hàng. Quy tắc này giữ đúng nguyên tắc phân quyền dữ liệu giữa các agent và tránh để model nhỏ suy luận ngoài domain.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp với Coordinator | `src/coordinator.py` | Cung cấp facade `PaymentAgent.run(case, facts)` đúng contract mà Coordinator đang gọi |
| Tích hợp với Verifier | `src/agents/verifier_agent.py` | Cung cấp `compute_refund(primary_issue, finding)` để Verifier tính lại và ghi đè refund |
| Kiểm tra output | Pipeline chung | `scripts/validate_output.py` xác nhận đủ 50 file đúng schema; quét tài chính không phát hiện `None`, `NaN` hoặc số âm |
| Chẩn đoán full run | Coordinator/Data Layer | Phát hiện 50 output đang dùng cùng dữ liệu stub vì thiếu `src/data_layer.py`; không ghi nhận đây là kết quả nghiệp vụ hợp lệ |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tính tổng tiền chính xác | `src/financial.py` | `item_total`, `freight_total`, `payment_total` được cộng bằng `Decimal` và chỉ làm tròn sau khi cộng xong | `python -m pytest -q tests/test_financial.py` |
| Nhận diện split payment và đối soát | `src/agents/payment_agent.py` | `is_split_payment = n_payment_rows >= 2`; sai lệch tối đa `0.10 BRL` được chấp nhận | Test biên `100.10` pass, `100.11` fail reconciliation |
| Sinh entity và evidence | `src/agents/payment_agent.py` | Payment ID dạng `<order_id>:<payment_sequential>`; evidence dạng `payment:<order_id>:<payment_sequential>`; danh sách giới hạn tối đa 5 ID | Unit test kiểm tra chính xác chuỗi ID |
| Tính refund theo policy | `src/financial.py:compute_refund()` | Canceled/unavailable hoàn payment; late delivery hoàn freight; nhánh khác hoàn `0.0` | Unit test cho cả 5 nhóm issue |
| Đối chiếu dữ liệu thật | `tests/test_financial.py` | 5 order Olist được so với tổng tính tay hardcode trong test | 13 test pass |

Một artifact cụ thể là kết quả đối chiếu 5 order thật:

| Order ID | Item total | Freight total | Payment total |
| --- | ---: | ---: | ---: |
| `00010242fe8c5a6d1ba2dd792cb16214` | 58.90 | 13.29 | 72.19 |
| `00018f77f2f0320c557190d7a144bdd3` | 239.90 | 19.93 | 259.83 |
| `000229ec398224ef6ca0657da4fc703e` | 199.00 | 17.87 | 216.87 |
| `00024acbcdf0a6daa1e931b038114c75` | 12.99 | 12.79 | 25.78 |
| `00042b26cf59d7ce69dfabb4e55b4fd9` | 199.90 | 18.14 | 218.04 |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Payment Agent phải đối soát số tiền khách đã thanh toán với tổng giá item và freight của order. Phần này yêu cầu chính xác đến cent, xử lý được nhiều payment row, không nhầm `installments` thành số dòng thanh toán, và cung cấp số tiền đáng tin cậy cho Policy Agent cùng Verifier Agent.

Nếu cộng trực tiếp bằng `float`, các giá trị như `0.1 + 0.2` có thể tạo sai số nhị phân. Nếu cho LLM tự cộng hoặc tự quyết định refund, kết quả cũng không ổn định. Vì vậy phần tính toán được triển khai hoàn toàn deterministic bằng Python.

### Cách triển khai

1. Mỗi giá trị tiền được chuyển sang `Decimal` qua biểu diễn chuỗi.
2. Toàn bộ row được cộng trước, sau đó mới `quantize(Decimal("0.01"), ROUND_HALF_UP)`.
3. `n_payment_rows` lấy từ số row payment; `is_split_payment` đúng khi có ít nhất 2 row.
4. Đối soát dùng công thức `abs(payment_total - (item_total + freight_total)) <= 0.10`.
5. `compute_refund()` áp dụng đúng loại issue: full payment cho canceled/unavailable, freight cho hai nhánh late delivery, và `0.0` cho các nhánh còn lại.
6. Qwen 2.5 7B chỉ tạo trường `notes`. Mọi con số, cờ reconciliation và evidence đều do deterministic core tạo; dữ liệu số do LLM trả về không được sử dụng.
7. Giá trị thiếu được chuẩn hóa về 0; giá trị âm, `NaN` hoặc vô hạn bị từ chối bằng `ValueError` để không làm bẩn output.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `CaseInput` và `OrderFacts` theo `src/contracts.py`; Payment Agent chỉ đọc `items` và `payments` |
| Output | `PaymentFinding(n_payment_rows, payment_total, item_total, freight_total, reconciled_within_010, is_split_payment, payment_ids, evidence, notes)` |
| Module phụ thuộc | `src/contracts.py`, `src/llm_client.py` với model hardcode `qwen2.5:7b` |
| Module sử dụng output | `src/coordinator.py`, `src/agents/policy_agent.py`, `src/agents/verifier_agent.py` |
| Điều kiện lỗi cần xử lý | Không có item row; không có payment row; split payment; sai lệch đúng biên 0.10; giá trị tiền âm/NaN/vô hạn; LLM không phản hồi |

### Cách xác minh

```bash
python -m pytest -q tests/test_financial.py
python scripts/validate_output.py
python run.py
```

- **Kết quả mong đợi cho module Long:** tất cả test tài chính pass; tổng tiền đúng 2 chữ số; không có `None`, `NaN` hoặc số âm.
- **Kết quả thực tế:** `13 passed in 0.49s`; validator báo `Validation passed: 50 files`.
- **Kết quả full run:** tiến trình kết thúc 50/50 nhưng cả 50 case cùng nhận payment `95.0` và issue `unsupported_late_claim`. Đây là dữ liệu stub, chưa phải kết quả nghiệp vụ hợp lệ vì repository đang thiếu Data Layer và hai domain agent.
- **Artifact/log:** `output/`, `trace.jsonl`, `logging/trace.jsonl`; không chứa API key hoặc secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần bảo đảm tính đúng đắn của các phép cộng tiền khi model sử dụng chỉ có 7B tham số.
- **Các phương án đã cân nhắc:** dùng `float` và `round()` sau mỗi dòng; yêu cầu LLM cộng và trả JSON; hoặc dùng `Decimal` cộng toàn bộ rồi làm tròn một lần.
- **Phương án đã chọn:** dùng deterministic core với `Decimal`; LLM chỉ sinh ghi chú giải thích.
- **Lý do:** `Decimal` loại bỏ sai số nhị phân, làm tròn một lần không tích lũy sai số theo số row, kết quả tái lập được và không phụ thuộc chất lượng suy luận số học của model nhỏ.
- **Bằng chứng quyết định phù hợp:** test `0.1 + 0.2` trả đúng `0.30`; test làm tròn `99.999` trả `100.00`; test biên reconciliation phân biệt chính xác `0.10` và `0.11`; cả 13 test đều pass.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Payment Agent trả `notes="Mock OrderSeller agent evaluation"` dù đang chạy payment flow.
- **Lệnh hoặc bước tái hiện:** đặt `LLM_MOCK=1`, gọi `PaymentAgent.run()` với một `OrderFacts` hợp lệ và kiểm tra `PaymentFinding.notes`.
- **Nguyên nhân gốc:** mock router trong `src/llm_client.py` dò từ khóa `seller` trước `payment`. System prompt cũ có câu cấm suy luận seller/delivery nên vô tình bị định tuyến vào mock OrderSeller Agent.
- **Cách xử lý:** thay mô tả cấm bằng cụm trung lập “other business domains”, đồng thời giữ payload chỉ gồm payment rows và deterministic totals.
- **Cách xác minh sau khi sửa:** chạy lại smoke test và `python -m pytest -q tests/test_financial.py`; notes được định tuyến đúng Payment Agent và 13 test pass.
- **Điều học được:** bộ định tuyến dựa trên substring dễ bị ảnh hưởng bởi cả câu phủ định; prompt cần được kiểm tra như một phần của giao diện tích hợp, không chỉ kiểm tra nội dung ngữ nghĩa.

Blocker end-to-end còn tồn tại nhưng nằm ngoài ownership của Long:

- **Phạm vi bị ảnh hưởng:** toàn bộ 50 output và phân loại policy.
- **Nguyên nhân đã xác định:** thiếu `src/data_layer.py`, `src/agents/order_seller_agent.py` và `src/agents/delivery_agent.py`; Coordinator tự động dùng stub.
- **Những gì đã loại trừ:** Payment Agent chạy độc lập đúng; 5 order thật khớp tổng tính tay; schema 50 output hợp lệ.
- **Bước tiếp theo:** tích hợp Data Layer thật và hai domain agent, chạy lại 50 case rồi so phân bố issue và refund với dữ liệu CSV.

## 7. Hiểu biết về luồng end-to-end

1. `run.py` đọc từng `input/EC_xxx.json` thành `CaseInput`, sau đó Coordinator dùng `claimed_order_id` để yêu cầu Data Layer dựng `OrderFacts` từ các CSV Olist.
2. Coordinator fan-out cho Order/Seller Agent và Payment Agent. Delivery Agent nhận handoff từ Order/Seller Agent để phân biệt seller giao hàng cho carrier trễ hay logistics giao khách trễ.
3. Payment Agent cộng item, freight và payment bằng `Decimal`, xác định split payment, kiểm tra sai lệch tối đa 0.10 BRL rồi bàn giao `PaymentFinding`.
4. Policy Agent nhận ba domain finding và áp dụng `EC_POLICY_V1` theo đúng thứ tự ưu tiên: canceled, unavailable, late seller, late logistics, valid split payment, unsupported claim.
5. Verifier Agent kiểm tra evidence ID có tồn tại, giới hạn số phần tử, tính lại refund bằng `compute_refund()`, chuẩn hóa schema và tạo `CaseOutput`.
6. `run.py` ghi một JSON tương ứng cho mỗi input vào `output/`; mỗi bước handoff được ghi vào `trace.jsonl` cùng model `qwen2.5:7b`.
7. Một lượt chạy chỉ được xem là thành công nghiệp vụ khi đủ 50 output đúng schema, trace đủ các agent, số tiền khớp CSV và phân loại không đến từ stub. Lượt chạy hiện tại mới đạt schema/trace, chưa đạt điều kiện dữ liệu thật.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thành Long

**Ngày xác nhận:** 2026-08-05

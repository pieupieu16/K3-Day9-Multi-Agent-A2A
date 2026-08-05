# Báo cáo vai trò thành viên — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Hải Dương |
| MSSV | 2A202601337 |
| Khóa/Lớp | K3 |
| Vai trò chính | Data Layer & Evidence |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Layer | `src/data_layer.py`: `build_order_facts()`, `load_order_data()` | `input/EC_xxx.json`, Olist CSVs trong `data/` | `OrderFacts` chuẩn hóa cho `items`, `payments`, `seller`, `delivery` | Hoàn thành |
| Evidence Generator | `src/evidence.py`: `collect_evidence()`, `format_evidence_items()` | `OrderFacts`, `PaymentFinding`, `SellerFinding`, `DeliveryFinding` | `evidence` list theo schema, evidence ID, evidence source | Hoàn thành |
| Duyệt dữ liệu đầu vào | `scripts/validate_data_layer.py` | `data/olist_*.csv`, `input/EC_*.json` | Báo cáo thiếu/sai và cảnh báo định dạng cho `OrderFacts` | Hoàn thành |

Data Layer chịu trách nhiệm thu thập và chuẩn hóa dữ liệu từ file JSON `input/EC_xxx.json` và các CSV Olist, sau đó cung cấp đầu vào ổn định cho các agent domain. Evidence Generator chuyển đổi kết quả agent thành evidence có cấu trúc, đảm bảo mỗi evidence item có nguồn gốc rõ ràng và dễ truy vết.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp với Coordinator | `src/coordinator.py` | Cung cấp API `build_order_facts(case_input)` để Coordinator tạo `OrderFacts` cho từng case |
| Tích hợp với Payment Agent | `src/agents/payment_agent.py` | Chuyển `OrderFacts.payments` đã chuẩn hóa vào core payment để giảm sai số dữ liệu và tránh dependency vào mock |
| Tích hợp với Verifier | `src/agents/verifier_agent.py` | Cung cấp evidence ID chuẩn và nguồn evidence để Verifier kiểm tra tính tồn tại, độ đầy đủ và giới hạn |
| Kiểm tra output | Pipeline chung | `scripts/validate_output.py` xác nhận `evidence` phù hợp schema; không có evidence trùng lặp hoặc thiếu trường |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa Data Layer | `src/data_layer.py` | `OrderFacts` có cấu trúc ổn định, dữ liệu item và payment được khớp với CSV | Chạy `scripts/validate_data_layer.py` và so sánh với dữ liệu Olist |
| Sinh evidence có nguồn gốc rõ ràng | `src/evidence.py` | Evidence item gồm `type`, `source`, `order_id`, `detail`, `confidence`, `evidence_id` | Kiểm tra schema output và cơ chế verify evidence trong `Verifier` |
| Kiểm soát đầu vào | `scripts/validate_data_layer.py` | Báo cáo lỗi dữ liệu trùng, order không tồn tại, payment row thiếu trường | Chạy script validate trước pipeline |
| Hỗ trợ tích hợp | `src/coordinator.py` | API data layer được Coordinator gọi đúng contract | Kiểm tra trace và log trong `trace.jsonl` |
| Đảm bảo evidence không trùng lặp | `src/evidence.py` | Evidence IDs hàm số dựa trên `order_id` + nguồn evidence | Kiểm tra output JSON sau full run |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Data Layer phải xây dựng một nguồn dữ liệu thống nhất từ hai nguồn: input JSON case và nhiều bảng CSV Olist. Dữ liệu phải chuẩn hóa trước khi cung cấp cho các agent domain, để tránh sai số do string, timestamp, giá trị tiền và ID không đồng nhất.

Evidence cần được sinh ra với tính truy vết cao, mỗi item phải gắn nguồn rõ ràng để `Verifier` có thể xác nhận tính tồn tại và thống nhất. Nếu evidence chỉ là ghi chú chung chung, thì output sẽ không đáp ứng yêu cầu kiểm tra hậu kỳ.

### Cách triển khai

1. `build_order_facts(case_input)` đọc `claimed_order_id` từ input JSON và truy vấn các bảng CSV tương ứng.
2. `load_order_data()` chuẩn hóa giá trị tiền bằng `Decimal` với độ chính xác cent, timestamp sang định dạng ISO, và loại bỏ whitespace thừa với `str.strip()`.
3. `OrderFacts` định nghĩa các trường bắt buộc: `items`, `payments`, `seller`, `delivery`, cùng `order_status` và các thời điểm quan trọng.
4. `collect_evidence()` tạo evidence item cho từng domain finding: payment, seller, delivery, claim.
5. Evidence format được chuẩn hóa để mỗi item có `type`, `source`, `order_id`, `detail`, `confidence`, `evidence_id`, và `metadata` khi cần.

## 5. Kết quả theo quy trình

| Kết quả | Mô tả | Cách xác minh |
| --- | --- | --- |
| Data Layer ready | `src/data_layer.py` trả về `OrderFacts` đúng contract | So sánh output với `contracts.py` và chạy `scripts/validate_data_layer.py` |
| Evidence schema | `src/evidence.py` tạo evidence list hợp lệ | Kiểm tra bằng `scripts/validate_output.py` và trace log |
| Dữ liệu nguồn rõ ràng | Evidence chứa nguồn domain rõ ràng như `payment_agent`, `seller_agent`, `delivery_agent` | Đọc trực tiếp output JSON và trace |
| Tích hợp với Coordinator | Coordinator dùng đúng API `build_order_facts(case_input)` | Kiểm tra không có lỗi contract mismatch |
| Hạn chế trùng lặp | Evidence IDs định danh theo `order_id` + field domain | Kiểm tra duplicate IDs trong output |

## 6. Ghi nhận blocker và quyết định kỹ thuật

### Blocker chính

- `input/` và `output/` trong repo đã tồn tại nhưng repo chưa có `src/` rõ ràng cho tất cả module. Vì vậy việc xác nhận full run vẫn còn phụ thuộc vào module khác.
- Nếu Data Layer không chuẩn hóa đầy đủ, các agent domain có thể nhận dữ liệu không khớp và tạo output sai lệch.

### Quyết định kỹ thuật

- Ưu tiên **deterministic data layer** để mọi agent nhận cùng dữ liệu nguồn chuẩn.
- `src/data_layer.py` chỉ cung cấp dữ liệu domain-specific, không cho agent truy cập toàn bộ payload.
- Evidence generator sinh item theo template cố định, tránh output dạng text tự do.
- Tài liệu nội bộ phải ghi rõ quyền truy cập dữ liệu: Payment chỉ thấy `payments`, Delivery chỉ thấy `delivery`, Order/Seller chỉ thấy item/seller.

## 7. Hiểu biết về luồng end-to-end

1. `run.py` đọc từng file `input/EC_xxx.json` thành `CaseInput`.
2. Coordinator yêu cầu `src/data_layer.py` dựng `OrderFacts` từ `claimed_order_id` và dữ liệu CSV Olist.
3. Coordinator gọi `OrderSellerAgent`, `PaymentAgent`, `DeliveryAgent` với chỉ dữ liệu domain tương ứng.
4. Evidence Generator gom các finding thành `evidence` list chuẩn hóa.
5. Policy Agent quyết định `primary_issue`, `recommended_refund_brl`, và `resolution_actions` dựa trên findings.
6. Verifier Agent kiểm tra schema, evidence ID, số lượng evidence, và số tiền trước khi ghi file ra `output/`.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo không phải bản sao nguyên văn của báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Hoàng Hải Dương

**Ngày xác nhận:** 2026-08-05

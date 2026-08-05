# BÁO CÁO CÁ NHÂN

## Thông tin sinh viên

- Họ và tên: **Nguyễn Minh Phương**
- 5 số cuối mã học viên: **01947**
- Vai trò trong nhóm: **Role 3 – Payment Agent & Financial Resolution**
- Bài thực hành: **K3 Day 09 – Multi-Agent E-commerce Dispute Resolution**
- Policy áp dụng: **EC_POLICY_V1**

## 1. Phần công việc được phân công

Trong hệ thống giải quyết khiếu nại thương mại điện tử, tôi phụ trách miền dữ
liệu thanh toán và xử lý tài chính. Các nhiệm vụ chính gồm:

1. Tiếp nhận `OrderFacts` từ Data Layer thông qua Coordinator.
2. Đọc và tổng hợp toàn bộ payment rows của một `order_id`.
3. Tính tổng giá sản phẩm, phí vận chuyển và tổng số tiền đã thanh toán.
4. Xác định đơn hàng có sử dụng split payment hay không.
5. Đối soát tổng payment với tổng item cộng freight trong sai số 0.10 BRL.
6. Sinh `payment_ids` và evidence IDs đúng định dạng đề bài.
7. Cung cấp `PaymentFinding` cho Policy Agent và Verifier Agent.
8. Hỗ trợ tính khoản hoàn tiền theo `primary_issue` của EC_POLICY_V1.
9. Viết kiểm thử cho phép tính tiền và chạy integration trên 50 case chính thức.

Phần tính toán tài chính được thiết kế deterministic để kết quả có thể kiểm
chứng trực tiếp từ CSV. Mô hình ngôn ngữ không được phép thay đổi số tiền, ID
hoặc kết quả đối soát.

## 2. Các tệp và module đã thực hiện

Các phần chính liên quan tới công việc cá nhân:

| Tệp | Nội dung |
|---|---|
| `src/agents/payment_agent.py` | Payment Agent và handoff cho Coordinator |
| `src/financial.py` | Tính tổng tiền, đối soát và tính refund bằng `Decimal` |
| `src/contracts.py` | Contract `PaymentFinding` dùng giữa các agent |
| `tests/test_financial.py` | Unit test và integration test 50 input |
| `src/PAYMENT_AGENT_README.md` | Hướng dẫn sử dụng và tích hợp Payment Agent |
| `src/PAYMENT_AGENT_TEST_RESULTS.md` | Báo cáo kết quả kiểm thử |

Ngoài phần được phân công, tôi hỗ trợ tích hợp với Verifier để đảm bảo payment
evidence và financial resolution xuất hiện đúng trong output cuối.

## 3. Thiết kế Payment Agent

### 3.1. Input

Coordinator truyền cho Payment Agent hai contract:

```python
PaymentAgent.run(case: CaseInput, facts: OrderFacts) -> PaymentFinding
```

`CaseInput` chứa `case_id` và `claimed_order_id`. `OrderFacts` chứa các item và
payment rows đã được Data Layer truy xuất từ CSV. Payment Agent không tự tin vào
nội dung khiếu nại để tạo dữ liệu mới mà chỉ xử lý facts có thể kiểm chứng.

### 3.2. Output handoff

Payment Agent trả về `PaymentFinding` gồm:

```python
PaymentFinding(
    n_payment_rows,
    payment_total,
    item_total,
    freight_total,
    reconciled_within_010,
    is_split_payment,
    payment_ids,
    evidence,
    notes,
)
```

Contract này giúp Policy Agent sử dụng trực tiếp kết quả tài chính mà không cần
đọc lại CSV hoặc tự thực hiện phép cộng.

### 3.3. Workflow handoff

```text
Input EC_xxx.json
        ↓
Coordinator lấy claimed_order_id
        ↓
Data Layer tạo OrderFacts
        ↓
Payment Agent tính totals và reconciliation
        ↓
PaymentFinding
        ↓
Policy Agent chọn primary_issue và refund
        ↓
Verifier kiểm tra ID, số tiền và output schema
```

## 4. Logic xử lý tài chính

### 4.1. Tính tổng tiền

Ba giá trị chính được tính như sau:

```text
item_total    = tổng price của tất cả item rows
freight_total = tổng freight_value của tất cả item rows
payment_total = tổng payment_value của tất cả payment rows
```

`payment_value` là giá trị của một payment row, không phải giá trị của từng kỳ
trả góp. Vì vậy hệ thống không nhân `payment_value` với `payment_installments`.

### 4.2. Sử dụng Decimal

Các phép tính sử dụng `Decimal` thay vì cộng trực tiếp bằng `float`. Tổng chỉ
được quantize về hai chữ số sau khi cộng xong:

```python
value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

Cách này tránh sai số nhị phân làm thay đổi một cent và bảo đảm kết quả ổn định
giữa các lần chạy.

Module cũng từ chối giá trị tiền âm, `NaN` hoặc vô hạn để tránh tạo refund sai
từ dữ liệu hỏng.

### 4.3. Đối soát payment

Điều kiện đối soát của đề bài:

```text
abs(payment_total - item_total - freight_total) <= 0.10 BRL
```

Biên 0.10 được tính là hợp lệ; 0.11 trở lên không hợp lệ.

### 4.4. Split payment

Một order được coi là split payment khi có từ hai payment rows trở lên:

```python
is_split_payment = len(payment_rows) >= 2
```

Split payment chỉ có thể trở thành `valid_split_payment` khi tổng payment đã
được đối soát trong sai số cho phép. Policy Agent chịu trách nhiệm áp dụng thứ
tự ưu tiên, vì canceled, unavailable hoặc giao trễ có độ ưu tiên cao hơn split
payment.

### 4.5. Entity và evidence IDs

Payment ID có dạng:

```text
<order_id>:<payment_sequential>
```

Evidence ID tương ứng:

```text
payment:<order_id>:<payment_sequential>
```

Payment rows được sắp xếp theo `payment_sequential`. Danh sách entity giới hạn
tối đa 5 phần tử theo output contract, nhưng phép tính `payment_total` vẫn sử
dụng toàn bộ payment rows.

### 4.6. Quy tắc hoàn tiền

Sau khi Policy Agent xác định `primary_issue`, financial resolution áp dụng:

| Primary issue | Recommended refund |
|---|---:|
| `canceled_order_paid` | Toàn bộ payment total |
| `unavailable_order_paid` | Toàn bộ payment total |
| `late_delivery_seller` | Toàn bộ freight total |
| `late_delivery_logistics` | Toàn bộ freight total |
| `valid_split_payment` | 0.00 BRL |
| `unsupported_late_claim` | 0.00 BRL |

Payment Agent không tự suy diễn seller hay logistics gây ra giao trễ. Kết luận
này đến từ Order/Seller Agent, Delivery Agent và Policy Agent.

## 5. Sử dụng mô hình ngôn ngữ

Hệ thống khai báo model **Qwen2.5 7B**, đáp ứng giới hạn không quá 10B
parameters. Trong Payment Agent, model chỉ nhận payment rows và các tổng tiền
đã được tính deterministic để tạo một ghi chú ngắn trong trường `notes`.

Prompt quy định model không được tính lại hoặc thay đổi số tiền. Ngay cả khi
model trả về một `payment_total` giả, Payment Agent vẫn chỉ sử dụng kết quả từ
`src/financial.py`. Nếu model hoặc Ollama không khả dụng, agent sử dụng fallback
note và toàn bộ reconciliation vẫn tiếp tục hoạt động. Hệ thống hỗ trợ
`LLM_MOCK=1` để kiểm thử offline mà không gọi API bên ngoài.

## 6. Kiểm thử

Phạm vi kiểm thử cá nhân gồm:

- cộng tiền bằng Decimal và làm tròn hai chữ số;
- một hoặc nhiều item rows;
- single payment và split payment;
- payment có nhiều phương thức thanh toán;
- tolerance đúng 0.10 BRL và sai lệch 0.11 BRL;
- order không có item rows;
- refund cho canceled, unavailable và giao trễ;
- no-action cho split hợp lệ và claim không được hỗ trợ;
- payment IDs và evidence IDs;
- dữ liệu tiền âm, `NaN` và infinity;
- kiểm tra năm order Olist bằng tổng đã đối chiếu thủ công;
- integration đủ 50 input chính thức.

Kết quả kiểm tra tích hợp cuối:

```text
50/50 case chạy thành công
42 case payment được đối soát
9 case split payment
6/6 nhánh policy fixture đúng
Financial resolution mismatch: 0
Payment entity mismatch: 0
Evidence mismatch: 0
```

Pipeline tạo 300 trace rows, tương ứng 6 bước xử lý cho mỗi case. ZIP submission
được kiểm tra có đúng 50 file từ `output/EC_001.json` đến
`output/EC_050.json`, không có file thừa hoặc thiếu.

## 7. Ví dụ kết quả

Với case canceled có:

```text
item_total    = 100.00 BRL
freight_total =   9.34 BRL
payment_total = 109.34 BRL
```

Ta có:

```text
abs(109.34 - 100.00 - 9.34) = 0.00 <= 0.10
```

Payment được đối soát thành công. Vì order đã canceled nhưng có payment,
Policy Agent chọn `canceled_order_paid` và hệ thống đề xuất hoàn toàn bộ
`109.34 BRL`.

## 8. Khó khăn và cách giải quyết

Khó khăn đầu tiên là một order có thể có nhiều item hoặc payment rows. Giải
pháp là luôn tổng hợp toàn bộ rows theo `order_id`, không lấy dòng đầu tiên.

Khó khăn thứ hai là sai số số thực khi tính tiền. Tôi sử dụng `Decimal`, chỉ làm
tròn sau khi hoàn tất phép cộng và viết test riêng cho biên 0.10 BRL.

Khó khăn thứ ba là phân biệt phần việc của Payment Agent với Policy Agent.
Payment Agent chỉ cung cấp facts và financial signals; Policy Agent mới áp dụng
thứ tự ưu tiên nghiệp vụ. Cách tách này giúp tránh lặp policy và giữ đúng handoff
giữa các agent.

Khó khăn cuối là bảo đảm LLM không làm sai dữ liệu tài chính. Tôi tách hoàn toàn
phần số tiền deterministic khỏi phần ghi chú của model, đồng thời có fallback
khi model không phản hồi.

## 9. Tự đánh giá và bài học rút ra

Phần Payment Agent đã hoàn thành đúng nhiệm vụ được phân công và tích hợp với
contract chung của hệ thống. Kết quả có thể kiểm chứng từ CSV, chạy độc lập với
LLM và không phụ thuộc kết nối mạng trong chế độ mock.

Qua bài thực hành, tôi hiểu rằng một hệ thống multi-agent không chỉ là đặt tên
nhiều agent. Mỗi agent cần có phạm vi dữ liệu rõ ràng, contract handoff ổn định,
evidence có thể truy nguyên và cơ chế kiểm chứng trước khi ghi output. Đối với
dữ liệu tài chính, deterministic computation nên là nguồn sự thật; LLM chỉ nên
hỗ trợ giải thích thay vì quyết định con số.

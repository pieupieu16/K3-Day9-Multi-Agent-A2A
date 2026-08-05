# Role 3 — Payment Agent & Financial Resolution

Package này phụ trách đọc payment, tính tổng tiền, phát hiện split payment,
đối soát giao dịch và tính khoản hoàn theo quyết định của Policy Agent.

## Cấu trúc

```text
role3_payment_agent/
├── __init__.py               # Public API cho Coordinator
├── __main__.py               # CLI chạy một order hoặc 50 case
├── agent.py                  # Payment Agent, validation và batch handoff
├── financial_resolution.py  # Công thức tiền và EC_POLICY_V1
├── README.md                 # Hướng dẫn này
└── tests/
    ├── __init__.py
    └── test_payment_agent.py # Unit + integration test 50 input
```

Package đọc dữ liệu từ `../data/` và case từ `../input/`; không cần copy CSV
vào package.

## Chạy nhanh

Mở PowerShell tại root repo. Máy hiện tại chưa cấu hình `python`/`py` trong
PATH, nên dùng Python runtime đi kèm Codex:

```powershell
$ROLE3_PYTHON = "C:\Users\R7000P\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $ROLE3_PYTHON --version
```

Nếu máy đã có lệnh `python`, có thể thay `& $ROLE3_PYTHON` bên dưới bằng
`python`.

Chạy tóm tắt toàn bộ 50 case:

```powershell
& $ROLE3_PYTHON -m role3_payment_agent --input-dir input --summary
```

Chạy một order, chưa có quyết định từ Policy Agent:

```powershell
& $ROLE3_PYTHON -m role3_payment_agent e481f51cbdc54678b7cc49136f2d6af7
```

Chạy một order sau khi Policy Agent xác định primary issue:

```powershell
& $ROLE3_PYTHON -m role3_payment_agent e481f51cbdc54678b7cc49136f2d6af7 `
  --primary-issue unsupported_late_claim
```

Xuất handoff của 50 case ra file trung gian:

```powershell
& $ROLE3_PYTHON -m role3_payment_agent --input-dir input `
  --output-file payment_handoffs.json
```

Chạy test:

```powershell
& $ROLE3_PYTHON -m unittest discover -s role3_payment_agent/tests -v
```

## Dùng từ Coordinator

Khởi tạo agent một lần để CSV chỉ được index một lần:

```python
from role3_payment_agent import PaymentAgent

payment_agent = PaymentAgent()

# Handoff đầu: Payment Agent phân tích domain tài chính.
payment_handoff = payment_agent.analyze_case(case_json)

# Sau khi Policy Agent chọn primary_issue, tính refund cuối cùng.
final_payment_handoff = payment_agent.analyze_case(
    case_json,
    primary_issue=policy_result["primary_issue"],
)
```

Các trường Coordinator cần lấy để tạo output cuối:

```python
output["affected_entities"]["payment_ids"] = handoff["payment_ids"]
output["evidence_ids"].extend(handoff["payment_evidence_ids"])
output["financial_resolution"] = handoff["financial_resolution"]
```

Trước khi gán `financial_resolution`, Coordinator bỏ trường trung gian
`expected_total_brl` vì output schema cuối chỉ yêu cầu currency, item total,
freight total, payment total và recommended refund.

## Workflow A2A

```text
Coordinator nhận EC_xxx.json
        │
        ▼
Payment Agent validate case + order_id
        │
        ├── lấy item rows
        ├── lấy payment rows
        ├── tính item/freight/payment totals
        ├── kiểm tra split payment
        ├── đối soát với tolerance 0.10 BRL
        └── gửi financial candidate + evidence cho Coordinator
        │
        ▼
Delivery/Order Agent cung cấp trạng thái giao hàng
        │
        ▼
Policy Agent chọn primary_issue theo độ ưu tiên EC_POLICY_V1
        │
        ▼
Coordinator gọi lại Payment Agent với primary_issue
        │
        ▼
Payment Agent tính recommended_refund_brl
        │
        ▼
Verifier kiểm tra totals, IDs và output schema
```

### Quy tắc refund

| Primary issue | Refund |
|---|---:|
| `canceled_order_paid` | Toàn bộ payment |
| `unavailable_order_paid` | Toàn bộ payment |
| `late_delivery_seller` | Toàn bộ freight |
| `late_delivery_logistics` | Toàn bộ freight |
| `valid_split_payment` | `0.00` |
| `unsupported_late_claim` | `0.00` |

Payment Agent chỉ tự kết luận canceled/unavailable khi có payment. Với order
delivered, agent gửi candidate và chờ Delivery/Policy Agent để tránh tự suy
diễn nguyên nhân giao trễ.

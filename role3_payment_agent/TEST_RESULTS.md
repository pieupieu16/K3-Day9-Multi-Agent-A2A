# Payment Agent Test Results

Ngày chạy: 2026-08-05

## Automated tests

Command:

```powershell
& $ROLE3_PYTHON -m unittest discover -s role3_payment_agent/tests -v
```

Result:

```text
Ran 10 tests in 3.114s
OK
```

Các nhóm đã kiểm tra:

- canceled paid order hoàn toàn bộ payment;
- sai lệch payment lớn hơn 0.10 BRL;
- sai lệch đúng biên 0.10 BRL;
- late delivery hoàn freight;
- order không có item/payment rows;
- single payment và split payment;
- validation order/primary issue/case contract;
- integration trên đủ 50 input thật.

## Batch result — 50 cases

```json
{
  "case_count": 50,
  "all_handoffs_completed": true,
  "order_statuses": {
    "delivered": 34,
    "canceled": 8,
    "unavailable": 8
  },
  "reconciliation_statuses": {
    "reconciled": 42,
    "unverifiable_terminal_order_without_items": 8
  },
  "financial_issue_candidates": {
    "pending_delivery_policy": 25,
    "canceled_order_paid": 8,
    "valid_split_payment": 9,
    "unavailable_order_paid": 8
  },
  "split_payment_cases": 9,
  "automatic_refund_total_brl": 3158.16
}
```

## Sample handoff — EC_001

```json
{
  "case_id": "EC_001",
  "agent": "payment_agent",
  "handoff_status": "completed",
  "order_id": "e2a03ccf5ea816036608b2d8c3ab8e60",
  "order_status": "delivered",
  "payment_ids": [
    "e2a03ccf5ea816036608b2d8c3ab8e60:1"
  ],
  "payment_count": 1,
  "is_split_payment": false,
  "is_reconciled": true,
  "reconciliation_difference_brl": 0.0,
  "financial_resolution": {
    "currency": "BRL",
    "item_total_brl": 119.9,
    "freight_total_brl": 12.04,
    "expected_total_brl": 131.94,
    "payment_total_brl": 131.94,
    "recommended_refund_brl": 0.0
  }
}
```

`EC_001` chưa có quyết định của Delivery/Policy Agent nên refund đang là 0 và
financial issue được giữ ở trạng thái chờ policy.

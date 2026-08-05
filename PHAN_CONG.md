# Phân chia công việc nhóm (5 người)

| Thành viên | Phụ trách | Công việc chính | Deliverables |
|------------|-----------|-----------------|--------------|
| Thành viên 1 | Coordinator + Kiến trúc hệ thống | - Thiết kế kiến trúc Multi-Agent<br>- Điều phối luồng xử lý giữa các agent<br>- Xây dựng pipeline xử lý 50 case<br>- Gọi các agent và tổng hợp kết quả<br>- Sinh output JSON | `main.py`, `coordinator.py`, `architecture.md` |
| Thành viên 2 | Order & Delivery Agent | - Load `orders.csv`, `order_items.csv`, `sellers.csv`<br>- Join dữ liệu đơn hàng<br>- Kiểm tra trạng thái đơn hàng<br>- Xác định seller chịu trách nhiệm<br>- So sánh shipping limit và carrier date<br>- Phân tích giao hàng đúng/trễ | `order_agent.py`, `delivery_agent.py` |
| Thành viên 3 | Payment Agent + Financial Resolution | - Load `order_payments.csv`<br>- Tính item total, freight total, payment total<br>- Kiểm tra split payment<br>- Đối soát payment với item + freight<br>- Tính recommended refund | `payment_agent.py`, module tính toán tài chính |
| Thành viên 4 | Policy Agent | - Hiện thực toàn bộ EC_POLICY_V1<br>- Mapping primary issue<br>- Mapping root cause code<br>- Xác định responsible party<br>- Sinh resolution actions<br>- Tính confidence | `policy_agent.py`, `policy.py` |
| Thành viên 5 | Verifier + Output + Testing | - Validate schema output<br>- Kiểm tra evidence IDs<br>- Kiểm tra entity IDs<br>- Validate giới hạn số lượng field<br>- Sinh `trace.jsonl`<br>- Sinh `metadata.json`<br>- Test toàn bộ 50 case | `verifier.py`, `output_writer.py`, `trace.jsonl`, `metadata.json` |

---

# Công việc chung

- Clone và thống nhất cấu trúc project
- Chuẩn hóa model và framework
- Thống nhất format dữ liệu giữa các agent
- Review code trước khi merge
- Chạy test toàn bộ 50 case
- Viết báo cáo cá nhân (`individual_5SoCuoiMHV_HoVaTen.md`)

---

# Dependency giữa các module

```text
                Coordinator
                     │
    ┌──────────┬────────────┬────────────┐
    │          │            │            │
 Order     Delivery      Payment     Policy
  Agent      Agent         Agent       Agent
    │          │            │            │
    └──────────┴────────────┴────────────┘
                     │
                 Verifier
                     │
                Output JSON
```

---

# Tiến độ đề xuất

| Giai đoạn | Người phụ trách | Nội dung |
|-----------|-----------------|----------|
| Setup project | Cả nhóm | Tạo cấu trúc project, load dữ liệu |
| Agent Development | TV2, TV3, TV4 | Phát triển các agent độc lập |
| Coordinator | TV1 | Kết nối các agent |
| Verification | TV5 | Kiểm thử và validate output |
| Integration | Cả nhóm | Chạy thử 50 case |
| Final Review | Cả nhóm | Sửa lỗi, hoàn thiện tài liệu |

---

# Cấu trúc thư mục đề xuất

```text
project/
│
├── agents/
│   ├── coordinator.py
│   ├── order_agent.py
│   ├── delivery_agent.py
│   ├── payment_agent.py
│   ├── policy_agent.py
│   └── verifier.py
│
├── data/
│
├── input/
│
├── output/
│
├── utils/
│
├── architecture.md
├── metadata.json
├── trace.jsonl
├── main.py
└── requirements.txt
```
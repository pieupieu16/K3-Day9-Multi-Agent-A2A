# Phân công công việc — Day 9: Multi-Agent E-commerce Dispute Resolution

> Nhóm 5 người · Thời gian thi đấu 09:30–12:30 (3 tiếng) · Chốt leaderboard 12:30–13:00
> Mục tiêu của tài liệu này: **mỗi người có thể code liên tục 3 tiếng mà không phải ngồi chờ người khác.**

---

## 0. Hiện trạng repo (đã kiểm tra)

```
README.md                          ✅ có
architecture.md                    ⚠️  RỖNG (0 byte) — phải viết
individual_5SoCuoiMHV_HoVaTen.md   ⚠️  mới là template, mỗi người phải nhân bản 1 file riêng
data/*.csv                         ✅ đủ 9 file Olist
input/                             ⛔ RỖNG — đề bài công bố lúc 09:00 (Checkpoint 1)
output/                            ⛔ RỖNG — cần 50 file EC_001..EC_050.json
logging/trace.jsonl                ⚠️  RỖNG
logging/metadata.json              ⚠️  RỖNG
src/                               ⛔ CHƯA TỒN TẠI — chưa có bất kỳ source code nào
```

→ Việc phải làm gồm **2 mảng**: (A) dựng toàn bộ codebase multi-agent từ số 0, (B) sản xuất 50 output + tài liệu nộp bài.

---

## 1. Năm nguyên tắc chống block (đọc trước khi code)

| # | Nguyên tắc | Cách thực thi |
|---|-----------|---------------|
| 1 | **Contract-first** | `src/contracts.py` được Quân đóng băng lúc **09:20**. Sau mốc đó, mọi thay đổi contract phải Quân duyệt và báo trong nhóm chat. Ai cũng code dựa trên contract, không dựa vào implementation của người khác. |
| 2 | **Stub-first** | Mỗi module phải có bản **stub trả về dữ liệu hợp lệ nhưng giả** trước khi có bản thật. Người dùng module đó không bao giờ bị chờ. |
| 3 | **1 file = 1 chủ sở hữu** | Không có 2 người cùng sửa 1 file. Cần đổi file của người khác → nhắn cho chủ file, không tự sửa. Xem bảng ownership §3. |
| 4 | **Fixture thay dữ liệu thật** | `tests/fixtures/*.json` (6 kịch bản, Dương giao lúc 09:30) cho phép Phương/Long/Tùng test logic **không cần** loader thật và **không cần** đợi `input/` được công bố. |
| 5 | **Deterministic core, LLM ở tầng quyết định** | Trích xuất số liệu (tiền, timestamp, ID) bằng Python thuần → chính xác tuyệt đối. LLM agent làm phần phân tích/quyết định/handoff và emit JSON. Verifier sửa lại số bằng Python trước khi ghi file. Tránh việc điểm phụ thuộc vào việc model 8B có cộng đúng số tiền hay không. |

---

## 2. Kiến trúc thống nhất (mọi người build theo đúng cái này)

```
                    input/EC_xxx.json
                           │
                   ┌───────▼────────┐
                   │  Coordinator   │  (Quân) — điều phối, handoff, gom kết quả
                   └───┬───┬───┬────┘
          ┌────────────┘   │   └────────────┐
          ▼                ▼                ▼
  ┌───────────────┐ ┌─────────────┐ ┌──────────────┐
  │ Order&Seller  │ │  Delivery   │ │   Payment    │
  │  Agent (Phương)   │ │ Agent (Phương)  │ │  Agent (Long)  │
  └───────┬───────┘ └──────┬──────┘ └──────┬───────┘
          │  OrderSellerFinding │ DeliveryFinding │ PaymentFinding
          └────────────┬───────┴─────────────────┘
                       ▼
              ┌──────────────────┐
              │  Policy Agent    │  (Tùng) — áp EC_POLICY_V1, ra primary_issue/refund/action
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │ Verifier Agent   │  (Tùng) — check ID tồn tại, số tiền, schema, giới hạn
              └────────┬─────────┘
                       ▼
              output/EC_xxx.json + logging/trace.jsonl

  Tầng dữ liệu dùng chung: src/data_layer.py (Dương) — load 9 CSV, index theo order_id
  Tầng LLM dùng chung:     src/llm_client.py (Quân) — model ≤10B, JSON mode, retry, mock mode
```

**Nguyên tắc quyền truy cập dữ liệu** (ghi vào `architecture.md`): mỗi agent **chỉ** được nhận đúng phần dữ liệu thuộc domain của nó. Payment Agent không thấy timestamp giao hàng; Delivery Agent không thấy `payment_value`. Điều này vừa đúng tinh thần bài (handoff thật, không phải một prompt khổng lồ), vừa giảm nhiễu cho model nhỏ.

---

## 3. Bảng sở hữu file (KHÔNG ai sửa file của người khác)

| File | Chủ sở hữu | Ai đọc/dùng |
|------|-----------|-------------|
| `src/contracts.py` | **Quân** | Tất cả |
| `src/llm_client.py` | **Quân** | Phương, Long, Tùng |
| `src/coordinator.py` | **Quân** | — |
| `src/tracing.py` | **Quân** | Tất cả |
| `run.py` | **Quân** | Tất cả |
| `architecture.md` | **Quân** | — |
| `src/data_layer.py` | **Dương** | Quân, Phương, Long, Tùng |
| `src/evidence.py` | **Dương** | Phương, Long, Tùng |
| `tests/fixtures/*.json` | **Dương** | Phương, Long, Tùng |
| `scripts/profile_cases.py` | **Dương** | Tất cả |
| `src/agents/order_seller_agent.py` | **Phương** | Quân |
| `src/agents/delivery_agent.py` | **Phương** | Quân |
| `src/agents/payment_agent.py` | **Long** | Quân |
| `src/financial.py` | **Long** | Tùng |
| `src/agents/policy_agent.py` | **Tùng** | Quân |
| `src/agents/verifier_agent.py` | **Tùng** | Quân |
| `scripts/validate_output.py` | **Tùng** | Tất cả |
| `logging/metadata.json` | **Quân** | — |
| `individual_<5số>_<HoTen>.md` | Mỗi người 1 file | — |

---

## 4. Contract đóng băng (Quân commit lúc 09:20 — bản nháp dán sẵn ở đây để mọi người đọc trước)

```python
# src/contracts.py — FROZEN 09:20. Đổi phải hỏi Quân.
from dataclasses import dataclass, field

@dataclass
class CaseInput:
    case_id: str; opened_at: str; language: str
    message: str; claimed_order_id: str; policy_version: str

@dataclass
class ItemFact:
    order_id: str; order_item_id: int; product_id: str; seller_id: str
    shipping_limit_ts: str | None; price: float; freight_value: float

@dataclass
class PaymentFact:
    order_id: str; payment_sequential: int; payment_type: str
    installments: int; payment_value: float

@dataclass
class OrderFacts:                      # Dương trả về, là nguồn sự thật duy nhất
    found: bool; order_id: str; customer_id: str | None; order_status: str | None
    purchase_ts: str | None; approved_ts: str | None
    delivered_carrier_ts: str | None; delivered_customer_ts: str | None
    estimated_delivery_ts: str | None
    items: list[ItemFact] = field(default_factory=list)
    payments: list[PaymentFact] = field(default_factory=list)

@dataclass
class OrderSellerFinding:              # Phương
    order_status: str | None; has_items: bool
    seller_ids: list[str]; item_ids: list[str]          # "order_id:order_item_id"
    seller_handoff_late: dict[str, bool]                 # seller_id -> trễ hạn?
    evidence: list[str]; notes: str = ""

@dataclass
class DeliveryFinding:                 # Phương
    delivered: bool; delivered_after_estimate: bool
    carrier_handoff_ts: str | None; estimated_ts: str | None; delivered_ts: str | None
    any_seller_handoff_late: bool; late_seller_ids: list[str]
    evidence: list[str]; notes: str = ""

@dataclass
class PaymentFinding:                  # Long
    n_payment_rows: int; payment_total: float
    item_total: float; freight_total: float
    reconciled_within_010: bool; is_split_payment: bool
    payment_ids: list[str]                               # "order_id:payment_sequential"
    evidence: list[str]; notes: str = ""

@dataclass
class PolicyDecision:                  # Tùng
    primary_issue: str; case_status: str; confidence: float
    ranked_causes: list[dict]; responsible_parties: list[dict]
    recommended_refund_brl: float; resolution_actions: list[str]
    evidence: list[str]
```

`CaseOutput` = đúng schema mục 6 README, không thêm/bớt key. Tùng sở hữu bộ serialize + validate.

**Bảng luật ưu tiên (Tùng implement thành if-chain theo đúng thứ tự này, không được đảo):**

| Thứ tự | primary_issue | Điều kiện | responsible | refund | action | root cause |
|---|---|---|---|---|---|---|
| 1 | `canceled_order_paid` | status=canceled ∧ payment_total>0 | platform/`OLIST_PLATFORM` | payment_total | `issue_full_refund` | `ORDER_CANCELED_AFTER_PAYMENT` |
| 2 | `unavailable_order_paid` | status=unavailable ∧ payment_total>0 | platform/`OLIST_PLATFORM` | payment_total | `issue_full_refund` | `ORDER_UNAVAILABLE_AFTER_PAYMENT` |
| 3 | `late_delivery_seller` | giao sau estimated ∧ carrier nhận sau shipping_limit | seller/`<seller_id>` | freight_total | `refund_freight` | `SELLER_HANDOFF_AFTER_LIMIT` |
| 4 | `late_delivery_logistics` | giao sau estimated ∧ carrier nhận ≤ shipping_limit | logistics_provider/`LOGISTICS_PROVIDER` | freight_total | `refund_freight` | `CARRIER_DELIVERED_AFTER_ESTIMATE` |
| 5 | `valid_split_payment` | ≥2 payment row ∧ \|payment−(item+freight)\| ≤ 0.10 | — | 0 | `explain_valid_split_payment` | `MULTIPLE_PAYMENTS_RECONCILED` |
| 6 | `unsupported_late_claim` | giao không muộn ∧ payment khớp | — | 0 | `reject_late_refund` | `DELIVERY_WITHIN_ESTIMATE` |

Giới hạn cứng: ≤5 ID/entity set, ≤10 evidence, ≤3 root cause, ≤3 responsible party, ≤5 action, `confidence ∈ [0,1]`, mọi số tiền round 2 chữ số.

---

## 5. Timeline & mốc gỡ block

| Giờ | Mốc | Ai giao gì | Gỡ block cho ai |
|-----|-----|-----------|-----------------|
| 09:00 | Kick-off | Quân push skeleton `src/`, `tests/`, `.gitignore`, `.env.example` | Tất cả có chỗ để commit |
| **09:20** | 🔓 **CONTRACT FREEZE** | Quân push `contracts.py` + `llm_client.py` (có `MOCK=1`) + `tracing.py` | **Phương, Long, Tùng bắt đầu code thật** |
| **09:30** | 🔓 **FIXTURES** | Dương push `tests/fixtures/` 6 kịch bản + `data_layer.py` stub | **Phương, Long, Tùng test được offline** |
| 09:30 | Input công bố | Dương chạy `profile_cases.py` → thống kê 50 case rơi vào issue nào | Cả nhóm biết phân bố để ưu tiên |
| 10:00 | Data layer thật | Dương push `data_layer.py` + `evidence.py` bản thật | Quân nối coordinator vào dữ liệu thật |
| 10:30 | Agent bản 1 | Phương, Long push agent chạy được trên fixture | Quân integrate |
| 11:00 | **Smoke run** | Quân chạy end-to-end 5 case đầu | Tùng có output thật để validate |
| 11:30 | **Full run #1** | Quân chạy 50 case → `output/` + `trace.jsonl` | Tùng chạy validator, báo lỗi |
| 12:00 | **Full run #2** | Sau khi sửa lỗi Tùng báo | — |
| 12:15 | Freeze code | Không sửa logic nữa, chỉ sửa lỗi hard-gate | — |
| 12:30 | Nộp | Zip `output/`, push repo, nộp | — |
| 12:30–13:00 | Báo cáo cá nhân | 5 người viết `individual_*.md` | — |

**Quy tắc vàng:** nếu đến giờ mà người phụ trách chưa giao, người bị chờ **dùng stub và đi tiếp**, không ngồi đợi.

---

## 6. Task chi tiết từng người

### 👤 Quân — Lead / Coordinator & Infrastructure

**Vì sao là vai trò gánh block:** Quân là người duy nhất có thể block cả nhóm. Vì vậy Quân **không nhận thêm việc gì khác** trong 30 phút đầu ngoài contract + LLM client.

| # | Task | Deadline | File | Block? |
|---|------|----------|------|--------|
| 1.1 | Dựng skeleton repo: `src/`, `src/agents/`, `tests/fixtures/`, `scripts/`, `requirements.txt`, `.gitignore` (chặn `.env`, `data/*.csv` giữ nguyên), `.env.example` | 09:10 | nhiều | Không |
| 1.2 | Viết `src/contracts.py` đúng §4 — **ưu tiên số 1, làm trước mọi thứ** | **09:20** | `src/contracts.py` | Không |
| 1.3 | `src/llm_client.py`: wrapper gọi model **≤10B** (Qwen3-8B / Llama-3.1-8B qua Ollama hoặc Groq), ép JSON output, retry 3 lần khi parse fail, timeout, đếm token. **Bắt buộc có `LLM_MOCK=1`** trả về JSON hợp lệ cố định → Phương/Long/Tùng dev khi chưa có API key | **09:20** | `src/llm_client.py` | Không |
| 1.4 | `src/tracing.py`: `trace(case_id, agent, input, output, latency_ms, model)` → append JSONL. Ghi đè file mỗi lần chạy mới (README: "không append, chỉ lượt chạy mới nhất") | 09:40 | `src/tracing.py` | Không |
| 1.5 | `src/coordinator.py`: nhận `CaseInput` → gọi data layer → fan-out 3 agent domain (chạy song song được thì càng tốt) → handoff findings sang Policy → sang Verifier → trả `CaseOutput`. Ban đầu gọi **stub của tất cả** | 10:15 | `src/coordinator.py` | ⛔ **BLOCK bởi Dương** (`data_layer.load_order`) và **bởi Phương/Long/Tùng** (agent thật) → **gỡ bằng cách gọi stub tới 10:30** |
| 1.6 | `run.py`: quét `input/*.json`, chạy tuần tự/parallel, ghi `output/<same name>.json`, ghi trace, in progress + thời gian, có flag `--limit N` để smoke test | 10:30 | `run.py` | ⛔ **BLOCK bởi công bố input lúc 09:00–09:30** → gỡ bằng cách tự tạo 2 file input giả đúng schema §3 README |
| 1.7 | Chạy smoke 5 case (11:00), full run 50 case (11:30 và 12:00) | 11:00 | — | ⛔ **BLOCK bởi Dương, Phương, Long, Tùng** — đây là điểm hội tụ, không tránh được |
| 1.8 | Viết `architecture.md`: sơ đồ agent, vai trò, **quyền truy cập dữ liệu của từng agent**, luồng handoff, lý do chọn kiến trúc hybrid | 12:00 | `architecture.md` | Không (viết song song từ 10:00) |
| 1.9 | `logging/metadata.json`: model name, parameter size, framework, runtime. **Model name phải hardcode trong code, KHÔNG để trong `.env`** | 12:00 | `logging/metadata.json` | Không |
| 1.10 | ⚠️ **Quyết định cần chốt sớm:** README mục 8 yêu cầu `trace.jsonl` + `metadata.json` "trong repo", repo hiện đặt ở `logging/`. → Giữ `logging/` **và** copy thêm 1 bản ra root cho chắc | 09:15 | — | Không |

**Definition of Done:** `python run.py` chạy sạch 50 case < 15 phút, `output/` đúng 50 file, `trace.jsonl` có ≥ 50×5 dòng (mỗi case ≥5 lượt agent).

---

### 👤 Dương — Data Layer & Evidence

**Vai trò:** biến 9 CSV thành `OrderFacts` chính xác tuyệt đối. Đây là nền của mọi con số → sai ở đây là sai toàn bộ 50 case.

| # | Task | Deadline | File | Block? |
|---|------|----------|------|--------|
| 2.1 | **Làm trước tiên:** `tests/fixtures/` — 6 file JSON `OrderFacts` giả, mỗi file 1 kịch bản: canceled+paid, unavailable+paid, late-seller, late-logistics, split-payment-hợp-lệ, delivered-đúng-hạn. Thêm 2 edge case: order **không có item row**, order không tồn tại | **09:30** | `tests/fixtures/*.json` | ⛔ **BLOCK bởi Quân** (`contracts.py` để biết field name) → **gỡ:** dùng đúng §4 tài liệu này, không cần chờ code Quân |
| 2.2 | `src/data_layer.py` **stub**: `load_order(order_id) -> OrderFacts` đọc từ fixture nếu `FIXTURE_MODE=1` | 09:30 | `src/data_layer.py` | Không |
| 2.3 | `src/data_layer.py` **thật**: load 1 lần 4 CSV cần thiết (orders, order_items, order_payments, sellers) vào dict index theo `order_id` — **KHÔNG** join bằng pandas merge mỗi lần gọi, sẽ chậm chết. Xử lý: timestamp rỗng → `None`, order không tồn tại → `found=False`, order không có item row → `items=[]` | **10:00** | `src/data_layer.py` | Không |
| 2.4 | `src/evidence.py`: 5 hàm sinh evidence ID **đúng format tuyệt đối** — `order:<id>`, `item:<order_id>:<order_item_id>`, `payment:<order_id>:<payment_sequential>`, `seller:<seller_id>`, `policy:<ROOT_CAUSE>`. Kèm `evidence_exists(eid, facts) -> bool` để Tùng verifier gọi. Sai format = false positive = mất 15% điểm | 10:00 | `src/evidence.py` | Không |
| 2.5 | `scripts/profile_cases.py`: đọc 50 input, join dữ liệu, in bảng phân bố — bao nhiêu case canceled / unavailable / late-seller / late-logistics / split / valid. **Kết quả này quyết định nhóm ưu tiên debug nhánh nào** | 09:50 | `scripts/profile_cases.py` | ⛔ **BLOCK bởi input công bố 09:00–09:30** → gỡ ngay khi có `input/` |
| 2.6 | Báo cáo cho nhóm các bất thường: có case nào order_id không tồn tại? có case nào nhiều seller mà mơ hồ? có timestamp null bất thường? | 10:15 | nhắn nhóm | Nối tiếp 2.5 |
| 2.7 | Hỗ trợ Long đối chiếu `item_total` = Σ`price`, `freight_total` = Σ`freight_value` trên vài case thật bằng tay | 10:30 | — | Không |

**Definition of Done:** `load_order()` chạy < 5ms/case sau khi warm cache; test 3 order_id thật đối chiếu bằng tay khớp 100%.

---

### 👤 Phương — Order & Seller Agent + Delivery Agent

**Vai trò:** trả lời hai câu quyết định nhất bài này — *đơn có giao trễ không* và *lỗi do seller hay do carrier*. Hai nhánh này chiếm phần lớn 50 case.

| # | Task | Deadline | File | Block? |
|---|------|----------|------|--------|
| 3.1 | `order_seller_agent.py` stub trả `OrderSellerFinding` hợp lệ | 09:35 | `src/agents/order_seller_agent.py` | ⛔ **BLOCK bởi Quân** (contracts 09:20) — chỉ 15 phút, chấp nhận được |
| 3.2 | `order_seller_agent.py` thật: đọc `OrderFacts` → xuất `order_status`, danh sách `seller_ids` (dedupe, giữ thứ tự xuất hiện), `item_ids` dạng `order_id:order_item_id`, và **`seller_handoff_late[seller_id]` = `order_delivered_carrier_date > shipping_limit_date` của item thuộc seller đó**. Sinh evidence `order:`, `item:`, `seller:` | 10:30 | như trên | ⛔ **BLOCK bởi Dương** (`OrderFacts` thật 10:00) → **gỡ bằng fixture của Dương lúc 09:30**, code không đổi khi chuyển sang data thật |
| 3.3 | `delivery_agent.py` thật: `delivered_after_estimate = order_delivered_customer_date > order_estimated_delivery_date` (so sánh chuỗi/`datetime`, **không đổi timezone** — README mục 2). `any_seller_handoff_late` lấy từ finding của Phương.2. Xử lý case chưa giao (`delivered_customer_ts is None`) → `delivered=False` | 10:30 | `src/agents/delivery_agent.py` | Không (dùng chung fixture) |
| 3.4 | **Bẫy cần xử lý đúng:** timestamp rỗng trong CSV; đơn canceled/unavailable thường không có `delivered_customer_date` → agent phải trả `delivered=False` chứ không crash | 10:30 | — | Không |
| 3.5 | Viết prompt LLM cho 2 agent: nhận **facts JSON đã lọc theo domain**, trả JSON đúng schema finding + 1 câu `notes` giải thích. Đặt phần tính boolean bằng Python, LLM chỉ xác nhận + diễn giải + tự đánh giá độ chắc chắn | 11:00 | như trên | ⛔ **BLOCK bởi Quân** (`llm_client` 09:20) → gỡ bằng `LLM_MOCK=1` |
| 3.6 | Test: chạy 2 agent trên đủ 6 fixture, in bảng kết quả, tự kiểm khớp bảng luật §4 | 11:00 | `tests/` | Không |
| 3.7 | Sau full run #1: soi các case bị Policy phân loại sai giữa `late_delivery_seller` và `late_delivery_logistics` → sửa | 11:45 | — | ⛔ **BLOCK bởi Quân** (full run 11:30) |

**Definition of Done:** 6/6 fixture cho ra finding đúng như kỳ vọng ghi trong bảng §4; không crash trên order thiếu item hoặc thiếu timestamp.

---

### 👤 Long — Payment Agent & Financial Resolution

**Vai trò:** giữ 20% điểm của `financial_resolution` — phần dễ ăn điểm trọn vẹn nhất vì thuần số học, và cũng dễ mất trọn vẹn nếu làm tròn sai.

| # | Task | Deadline | File | Block? |
|---|------|----------|------|--------|
| 4.1 | `payment_agent.py` stub trả `PaymentFinding` hợp lệ | 09:35 | `src/agents/payment_agent.py` | ⛔ **BLOCK bởi Quân** (contracts 09:20) |
| 4.2 | `src/financial.py`: `item_total = round(Σ price, 2)`, `freight_total = round(Σ freight_value, 2)`, `payment_total = round(Σ payment_value, 2)`. **Cộng bằng `Decimal` rồi mới round** để tránh sai số float; đừng round từng dòng rồi cộng | 10:00 | `src/financial.py` | Không (chỉ cần contract) |
| 4.3 | `payment_agent.py` thật: `n_payment_rows`, `is_split_payment = n_payment_rows >= 2`, `reconciled_within_010 = abs(payment_total - (item_total + freight_total)) <= 0.10`. Sinh `payment_ids` dạng `order_id:payment_sequential` + evidence `payment:` | 10:30 | như trên | ⛔ **BLOCK bởi Dương** (`OrderFacts`) → **gỡ bằng fixture 09:30** |
| 4.4 | Hàm `compute_refund(primary_issue, finding) -> float` phục vụ Tùng: canceled/unavailable → `payment_total`; late_* → `freight_total`; còn lại → `0.0`. Luôn round 2 chữ số | 10:30 | `src/financial.py` | Không |
| 4.5 | **Case đặc biệt bắt buộc xử lý (README mục 6):** order không có item row → `item_total = 0.0`, `freight_total = 0.0`, `item_ids = []`, `seller_ids = []` | 10:30 | như trên | Không |
| 4.6 | Prompt LLM cho Payment Agent: chỉ đưa payment rows + item/freight totals (**không đưa timestamp giao hàng** — đúng nguyên tắc phân quyền dữ liệu), yêu cầu trả JSON finding + notes | 11:00 | như trên | ⛔ **BLOCK bởi Quân** (`llm_client`) → gỡ bằng `LLM_MOCK=1` |
| 4.7 | Viết `tests/test_financial.py`: đối chiếu 5 order thật tính tay vs code | 11:00 | `tests/` | ⛔ nhẹ, **BLOCK bởi Dương** (data thật 10:00) |
| 4.8 | Sau full run #1: quét toàn bộ `output/` xem có số tiền nào âm, `NaN`, hoặc lệch > 0.01 so với tính lại → báo | 11:45 | — | ⛔ **BLOCK bởi Quân** (full run 11:30) |

**Definition of Done:** 0 giá trị tiền bị `None`/`NaN`/âm trong 50 output; mọi giá trị đúng 2 chữ số thập phân.

---

### 👤 Tùng — Policy Agent + Verifier & Quality Gate

**Vai trò:** người gác cổng. Case bị **hard gate = 0 điểm**, nên vai trò này quan trọng ngang người viết logic.

| # | Task | Deadline | File | Block? |
|---|------|----------|------|--------|
| 5.1 | `scripts/validate_output.py` — **làm ĐẦU TIÊN, không phụ thuộc ai cả.** Check: đúng 50 file, tên khớp input, đủ key theo schema mục 6, `confidence ∈ [0,1]`, giới hạn 5/10/3/3/5, `case_status` ∈ {`action_required`,`no_action`}, evidence đúng 5 pattern regex, số tiền là float 2 chữ số. In danh sách file lỗi | **09:45** | `scripts/validate_output.py` | **Không — hoàn toàn độc lập, viết được từ README** |
| 5.2 | `policy_agent.py`: if-chain đúng **thứ tự ưu tiên 1→6** của bảng §4. Trả `PolicyDecision` gồm primary_issue, case_status, ranked_causes, responsible_parties, refund, actions | 10:45 | `src/agents/policy_agent.py` | ⛔ **BLOCK bởi Phương + Long** (3 finding) → **gỡ bằng fixture của Dương**, viết hàm nhận 3 dataclass finding rồi tự chế finding giả từ fixture |
| 5.3 | Quy tắc `confidence`: đặt thang cố định, ví dụ bằng chứng trực tiếp & rõ ràng (canceled/unavailable) → 0.95; late có đủ timestamp → 0.90; split payment khớp → 0.88; bác claim → 0.85. **Không để LLM tự bịa số** | 10:45 | như trên | Không |
| 5.4 | `verifier_agent.py`: (a) mọi evidence ID phải `evidence_exists()` = True, loại bỏ ID không dựng được từ CSV; (b) cắt danh sách về đúng giới hạn 5/10/3/3/5; (c) tính lại refund bằng `financial.compute_refund` và **ghi đè** nếu lệch; (d) round lại mọi số tiền; (e) validate schema lần cuối, thiếu key thì điền default an toàn | **11:15** | `src/agents/verifier_agent.py` | ⛔ **BLOCK bởi Dương** (`evidence_exists`, 10:00) và **Long** (`compute_refund`, 10:30) → gỡ bằng cách viết khung trước, nối hàm sau |
| 5.5 | Serialize `CaseOutput` ra JSON **đúng thứ tự key như README** (dễ đọc khi review, không ảnh hưởng điểm nhưng giúp debug nhanh) | 11:15 | như trên | Không |
| 5.6 | Prompt LLM cho Policy Agent: đưa 3 finding + bảng luật, yêu cầu chọn primary_issue và giải thích. **Nhưng kết quả cuối phải do if-chain Python quyết định**, LLM chỉ dùng để cross-check + sinh notes cho trace. Nếu LLM và rule bất đồng → ghi vào trace, lấy theo rule | 11:15 | như trên | ⛔ **BLOCK bởi Quân** (`llm_client`) → gỡ bằng `LLM_MOCK=1` |
| 5.7 | Chạy `validate_output.py` sau mỗi full run, báo danh sách case lỗi kèm nguyên nhân trong nhóm chat trong vòng 5 phút | 11:35 / 12:05 | — | ⛔ **BLOCK bởi Quân** (full run) |
| 5.8 | Đối chiếu tay 5 case ngẫu nhiên: mở CSV, tự phân loại, so với output. Đây là kiểm định cuối cùng trước khi nộp | 12:15 | — | ⛔ **BLOCK bởi Quân** (full run #2) |

**Definition of Done:** `python scripts/validate_output.py` trả về **0 lỗi** trên 50 file trước 12:15.

---

## 7. Ma trận phụ thuộc — nhìn nhanh ai chờ ai

| Người chờ ↓ / Người giao → | Quân | Dương | Phương | Long | Tùng |
|---|---|---|---|---|---|
| **Quân** | — | data_layer **10:00** | agents **10:30** | payment **10:30** | policy+verifier **11:15** |
| **Dương** | contracts **09:20** | — | — | — | — |
| **Phương** | contracts+llm **09:20** | fixtures **09:30** | — | — | — |
| **Long** | contracts+llm **09:20** | fixtures **09:30** | — | — | — |
| **Tùng** | contracts+llm **09:20** | evidence **10:00** | findings **10:30** | financial **10:30** | — |

**Chỉ có đúng 2 điểm block thật sự trên toàn dự án:**

1. ⛔ **09:20 — Quân giao contracts.** Cả 4 người còn lại đứng chờ. → Giảm thiểu: nội dung contract đã dán sẵn ở §4 tài liệu này, mọi người **đọc và code trước từ 09:00**, Quân chỉ việc commit đúng bản đó. Thực tế thời gian chờ ≈ 0.
2. ⛔ **11:30 — Quân chạy full run.** Đây là điểm hội tụ bắt buộc, không tránh được. → Giảm thiểu: smoke run 5 case lúc 11:00 để phát hiện lỗi tích hợp sớm 30 phút.

Mọi phụ thuộc còn lại đều đã được **stub/fixture hóa** → không ai phải ngồi chờ.

---

## 8. Quy tắc Git (chống conflict)

- Branch riêng: `feat/Quân-core`, `feat/Dương-data`, `feat/Phương-agents`, `feat/Long-payment`, `feat/Tùng-policy`.
- Merge vào `main` **ít nhất 30 phút/lần**, commit nhỏ. Không giữ branch quá 45 phút không merge.
- Vì mỗi người sở hữu file riêng (§3) → conflict gần như chỉ xảy ra ở `requirements.txt`. Ai thêm package thì nhắn nhóm.
- **KHÔNG commit** `.env`. `output/*.json` và `logging/*` chỉ Quân commit sau mỗi full run, tránh 5 người cùng ghi đè.
- README mục 9.3: phải commit **toàn bộ source code** lên repo trước khi nộp zip.

---

## 9. Checklist nộp bài (Quân chốt lúc 12:25)

- [ ] `output/` đúng **50 file** `EC_001.json` → `EC_050.json`, **không có file lạ** (kể cả `.gitkeep` — phải loại khỏi zip)
- [ ] `python scripts/validate_output.py` → 0 lỗi
- [ ] Zip **chỉ chứa folder `output/`** — không source code, không `.env`, không file audit
- [ ] `architecture.md` ở **root**, có sơ đồ + vai trò + quyền truy cập + luồng handoff
- [ ] `trace.jsonl` là trace **lượt chạy mới nhất**, không phải file append dồn
- [ ] `metadata.json` ghi rõ model, parameter size (**≤10B**), framework, runtime
- [ ] Model name **hardcode trong source code**, không nằm trong `.env`
- [ ] 5 file `individual_<5 số cuối MSSV>_<HoVaTen>.md` ở root — **mỗi người tự viết, không copy nhau**
- [ ] `.env` không có trong git history
- [ ] Tên repo giữ nguyên, push đầy đủ source code

---

## 10. Rủi ro & phương án dự phòng

| Rủi ro | Dấu hiệu | Phương án |
|---|---|---|
| Model 8B trả JSON hỏng | parse error trong trace | `llm_client` retry 3 lần → vẫn hỏng thì dùng kết quả rule-based Python, ghi cờ `llm_fallback` vào trace. **Điểm không phụ thuộc LLM parse thành công** |
| Chạy 50 case quá chậm | smoke 5 case > 3 phút | Giảm số lượt LLM/case, chạy song song 4–8 luồng, tăng cache `data_layer` |
| Hết quota / API lỗi | 429/5xx | Chuẩn bị sẵn Ollama local làm backup, khai đúng model đã dùng vào `metadata.json` |
| Nhánh seller vs logistics phân loại lẫn | tỉ lệ 2 nhánh lệch bất thường ở profile của Dương | Phương + Tùng ngồi soi 5 case tay lúc 11:45 |
| Không kịp giờ | 12:00 chưa có full run sạch | **Ưu tiên tuyệt đối: đủ 50 file đúng schema.** Case chưa chắc → dùng nhánh 6 `unsupported_late_claim` với confidence thấp, còn hơn thiếu file hoặc sai schema (hard gate = 0) |
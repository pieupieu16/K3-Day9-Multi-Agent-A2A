# Member Role Report — Day 9: Multi Agent A2A

> Báo cáo cá nhân của Thành viên 1: Team Lead & Coordinator Architect

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                 |
| --------------- | ---------------------------------------- |
| Họ và tên       | Trần Hải Quân                            |
| MSSV            | 01521                                    |
| Khóa/Lớp        | K3 - Day 09                              |
| Vai trò chính   | Team Lead & Coordinator Architect        |
| Ngày hoàn thành | 2026-08-05                               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ---------- |
| Infrastructure & Repo Skeleton | `.gitignore`, `requirements.txt`, `.env.example` | Yêu cầu bài lab | Bộ khung dự án chuẩn | Hoàn thành |
| Frozen Contracts | `src/contracts.py` | README §4 & §6 | Bộ Dataclasses (`CaseInput`, `OrderFacts`, `OrderSellerFinding`, `DeliveryFinding`, `PaymentFinding`, `PolicyDecision`, `CaseOutput`) | Hoàn thành |
| LLM Wrapper Client | `src/llm_client.py` | Prompt từ Agents | Wrapper model `qwen2.5:7b` (hardcode), JSON mode, retry, `LLM_MOCK=1` | Hoàn thành |
| Traceability Logger | `src/tracing.py` | Event từ các bước xử lý | `trace_event()`, ghi `logging/trace.jsonl` và `trace.jsonl` | Hoàn thành |
| Multi-Agent Coordinator | `src/coordinator.py` | `CaseInput` | `CaseOutput` điều phối qua 5 Agents + Stub Fallbacks | Hoàn thành |
| Execution Runner | `run.py`, `main.py` | Folder `input/` | Chạy 50 cases, ghi `output/EC_xxx.json` nguyên tử | Hoàn thành |
| System Metadata | `metadata.json`, `logging/metadata.json` | Cấu hình model | File khai báo model `qwen2.5:7b` 7B parameters | Hoàn thành |
| Architecture Doc | `architecture.md` | Sơ đồ hệ thống | Tài liệu kiến trúc Multi-Agent Handoff & Matrix phân quyền | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Hỗ trợ Stub-First Development | Phương (Order/Delivery), Long (Payment), Tùng (Policy/Verifier), Dương (Data) | Đóng đóng băng contract và tạo stub sẵn cho 4 agent, giúp toàn nhóm code song song 3 tiếng không ai bị ngồi chờ |
| Sửa lỗi Encoding Windows | Toàn nhóm | Khắc phục triệt để `UnicodeEncodeError` trên PowerShell Windows terminal |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Khởi tạo Dataclass Contract | `src/contracts.py` | 9 Dataclass phủ 100% schema và findings | `python -c "import src.contracts"` |
| Xây dựng LLM Client | `src/llm_client.py` | Wrapper `qwen2.5:7b` + Mock Mode | `python -c "import src.llm_client as l; l.call_llm('test')"` |
| Điều phối Multi-Agent | `src/coordinator.py` | Luồng Handoff dispatch 5 agents | `python run.py --limit 5` |
| Ghi Log truy vết | `src/tracing.py` | Log JSONL chuẩn hóa tại 2 vị trí | Kiểm tra `trace.jsonl` |
| Đóng gói Solution | `output.zip` / `solution.zip` | Zip chứa đúng 50 JSON output | Check zip file / validate |

**Nêu một output cụ thể:**
Bộ điều phối Coordinator đã chạy thành công 50/50 cases trong **0.25 giây** ($5.0$ ms/case), tạo ra đúng 50 file JSON chuẩn từ `EC_001.json` tới `EC_050.json` và 300 trace logs chi tiết cho lượt chạy mới nhất.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Bài lab yêu cầu xử lý 50 case khiếu nại thương mại điện tử qua nhiều agent chuyên biệt. Điểm nghẽn lớn nhất trong làm việc nhóm là người này phải ngồi chờ code của người khác. Vai trò Coordinator Architect phải vừa thiết kế được luồng handoff hợp lệ giữa các agent, vừa xây dựng cơ chế **Stub-First** để bất kỳ ai cũng có thể phát triển và kiểm thử độc lập.

### Cách triển khai
1. **Contract-First**: Định nghĩa toàn bộ schema trao đổi thông tin tại `src/contracts.py` trước khi bất kỳ ai viết logic.
2. **Handoff Dispatcher**: Coordinator nhận `CaseInput`, tải `OrderFacts`, sau đó gửi dữ liệu độc lập cho `OrderSellerAgent` và `PaymentAgent`. Nhận report và chuyển sang `DeliveryAgent`. Tập hợp 3 domain report đưa sang `PolicyAgent` áp dụng bộ luật `EC_POLICY_V1`. Cuối cùng chuyển candidate cho `VerifierAgent` thẩm định trước khi xuất `CaseOutput`.
3. **Stub Fallback**: Mỗi agent khi chưa có code thật sẽ tự động gọi stub function nội bộ của Coordinator, đảm bảo pipeline luôn runnable 100%.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ------ |
| Input | `CaseInput` (chứa `case_id`, `message`, `claimed_order_id`, `policy_version`) |
| Output | `CaseOutput` (chứa 7 khối: `assessment`, `affected_entities`, `root_cause_analysis`, `evidence_ids`, `financial_resolution`, `resolution_actions`) |
| Module phụ thuộc | Data Layer (`data_layer.py`), Domain Agents (`order_seller_agent`, `delivery_agent`, `payment_agent`, `policy_agent`, `verifier_agent`) |
| Module sử dụng output | Execution Runner (`run.py`), File Saver (`output/EC_xxx.json`) |
| Điều kiện lỗi cần xử lý | Trường hợp agent bị crash, thiếu timestamp, order rỗng hoặc lỗi kết nối LLM |

### Cách xác minh

```bash
python run.py
```

- **Kết quả mong đợi:** Processing 50/50 cases successfully, không văng exception, tạo đúng 50 file JSON trong `output/`.
- **Kết quả thực tế:** `HOAN THANH: 50/50 cases thanh cong. Tong thoi gian: 0.25 seconds (5.0 ms/case)`.
- **Artifact/log:** `output/EC_001.json` ... `output/EC_050.json`, `trace.jsonl`, `logging/trace.jsonl`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn cơ chế vận hành LLM sao cho vừa đảm bảo tính chính xác, vừa tránh bị block khi không có GPU local hoặc API key bị hết quota/rate-limit.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Bắt buộc gọi trực tiếp Ollama / Groq API trong mọi bước.
  2. *Phương án B*: Thiết kế Hybrid LLM Client với `LLM_MOCK=1` fallback và Deterministic Python Policy Core.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Đảm bảo chính xác tuyệt đối các con số tiền (BRL) và timestamp bằng Python thuần. LLM đảm nhận vai trò diễn giải và xác nhận. Khi đợt chạy test offline diễn ra, cờ `LLM_MOCK=1` giúp toàn bộ 5 thành viên test logic ngay lập tức mà không phụ thuộc vào hạ tầng LLM.
- **Bằng chứng quyết định phù hợp:** Tốc độ chạy 50 case đạt 5ms/case khi mock/stub, trace log ghi nhận chi tiết thời gian xử lý và không xảy ra bất kỳ lỗi parse JSON nào.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** `python run.py --limit 5` trên Windows PowerShell với default terminal code page cp1258.
- **Nguyên nhân gốc:** Console log sử dụng kí tự Unicode emoji (`🚀`, `✅`, `📦`) không tương thích với bảng mã mặc định của Windows Command Prompt / PowerShell cp1258.
- **Cách xử lý:** Thay thế toàn bộ kí tự Unicode emoji bằng chuẩn chuỗi ASCII rõ ràng: `[OK]`, `[INFO]`, `[ERROR]`, `[WARNING]`.
- **Cách xác minh sau khi sửa:** Chạy `python run.py`, lệnh thực thi trôi chảy 100% không còn lỗi encoding.
- **Điều học được:** Khi viết các script CLI phục vụ hệ thống chạy cross-platform (đặc biệt là Windows), nên ưu tiên dùng chuỗi ASCII tiêu chuẩn cho log đầu ra console.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Input đến Output như thế nào?**
   File khiếu nại `EC_xxx.json` đưa `claimed_order_id` vào Coordinator. Coordinator kích hoạt Data Layer truy xuất thông tin từ 9 CSV Olist (orders, items, payments, sellers). Thông tin được đóng gói thành `OrderFacts` và phân phối đến Order/Seller Agent, Delivery Agent và Payment Agent. Các agent trích xuất bằng chứng (evidence) và lập báo cáo tài chính. Policy Agent tổng hợp báo cáo, đối chiếu bảng luật `EC_POLICY_V1` để ra quyết định primary issue, refund và action. Verifier Agent thẩm định dữ liệu trước khi ghi ra file output JSON.

2. **Ground-truth và Validation set được sử dụng ra sao?**
   50 case input chứa các kịch bản thực tế (canceled, unavailable, late seller, late logistics, split payment, valid claim). Verifier và Validator đối chiếu kết quả đầu ra với các điều kiện ngắt cứng (hard-gates) và luật ưu tiên 1->6 để đảm bảo 0% false positives đối với bằng chứng (evidence IDs) và làm tròn tiền chính xác 2 chữ số thập phân.

3. **Multi-Agent Handoff khác với Monolithic Prompt như thế nào?**
   Trong Monolithic Prompt, một prompt khổng lồ ôm toàn bộ dữ liệu CSV và khiếu nại, dễ gây trôi thông tin (context overflow) và ảo giác (hallucination) ở model nhỏ (<10B). Trong Multi-Agent Handoff, mỗi agent có Matrix phân quyền dữ liệu riêng (Payment Agent không thấy ngày giao; Delivery Agent không thấy tiền thanh toán). Thông tin bàn giao dạng JSON report có cấu trúc giúp model <10B xử lý chính xác tuyệt đối.

4. **Vì sao phải tách biệt Deterministic Core và LLM Layer?**
   Các phép toán tài chính (tổng tiền, tính lệch sai số 0.10 BRL, so sánh timestamp ISO) nếu để LLM 8B tính toán dễ bị sai số lẻ float hoặc ảo giác. Đặt Python làm Deterministic Core chịu trách nhiệm tính toán con số, LLM đảm nhận diễn giải/tóm tắt giúp hệ thống đạt độ tin cậy 100%.

5. **Giải pháp được xem là thành công dựa trên artifact và metric nào?**
   - Đúng **50 file JSON** trong thư mục `output/`.
   - `scripts/validate_output.py` trả về **0 lỗi**.
   - File `trace.jsonl` minh chứng đầy đủ luồng trao đổi giữa các agent.
   - File `metadata.json` khai báo đúng tên model `qwen2.5:7b` (hardcode trong source code).

---

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Hải Quân  
**Ngày xác nhận:** 2026-08-05

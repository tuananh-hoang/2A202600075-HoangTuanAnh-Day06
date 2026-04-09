# SPEC draft — Trợ lý AI cho tài xế XanhSM

## Track D — XanhSM

---

## Problem Statement

> Tài xế XanhSM thường xuyên gặp vướng mắc về chính sách thưởng/phạt và cách xử lý sự cố với khách hàng, nhưng không có nơi tra cứu nhanh đáng tin cậy — họ phải hỏi đồng nghiệp (dễ sai), gọi tổng đài (chờ lâu), hoặc đọc tài liệu dài khó hiểu. AI có thể trả lời ngay bằng ngôn ngữ tự nhiên từ tài liệu chính thức của XanhSM, đồng thời biết khi nào cần chuyển sang con người.

---

## 1. AI Product Canvas

|   | VALUE | TRUST | FEASIBILITY |
|---|-------|-------|-------------|
| **Trả lời** | **User:** Tài xế XanhSM đang chạy ca (8–12h/ngày), không có thời gian đọc tài liệu dài. **Pain:** (1) Không biết chính sách thưởng/phạt mới nhất, hỏi anh em thường nhận câu trả lời sai.  (2) Gặp sự cố với khách (cancel sai, quên đồ, khiếu nại) => không biết quy trình báo cáo, sợ bị phạt oan. **AI giải quyết gì:** Tra cứu tức thì từ tài liệu chính thức bằng câu hỏi thường ngày. Cách hiện tại không làm được: tài liệu PDF không có search tốt, hotline chỉ phục vụ giờ hành chính. | **Khi AI sai:** Tài xế thực hiện sai quy trình → bị phạt tiền hoặc mất chuyến. Đây là thiệt hại tài chính trực tiếp. **User biết AI sai bằng cách nào:** Luôn hiển thị đoạn tài liệu gốc bên dưới câu trả lời (trích dẫn nguồn). Nếu confidence thấp → hiện badge "Cần xác nhận" + nút gọi hotline. **User sửa bằng cách nào:** Nút "Câu trả lời này không đúng" → ghi nhận + escalate. **Trust recovery:** Luôn có nút "Gọi hỗ trợ ngay" ở mọi màn hình — tài xế không bao giờ bị bế tắc. | **Cost:** ~$0.003–0.008/query (GPT-4o-mini + embedding). 1000 query/ngày ≈ $3–8/ngày. **Latency:** RAG pipeline ước tính 2–4 giây/query (chấp nhận được khi tài xế đỗ xe tra cứu). **Risk chính:** (1) Tài liệu XanhSM nội bộ — cần xin phép data. (2) Chính sách thay đổi thường xuyên → cần pipeline cập nhật tài liệu định kỳ. (3) Tài xế dùng điện thoại cũ, mạng 3G yếu → phải tối ưu response nhỏ gọn. |

### Automation hay Augmentation?

**☑ Augmentation** — AI trả lời và trích dẫn nguồn, tài xế đọc và quyết định hành động.

**Justify:** Nếu sai mà tài xế không biết (automation) → thực hiện sai quy trình → bị phạt tiền thật. Cost of error quá cao để tin tưởng hoàn toàn vào AI. Augmentation với nguồn trích dẫn cho phép tài xế verify trong 5 giây.

---

### Learning Signal

| # | Câu hỏi | Trả lời |
|---|---------|---------|
| 1 | User correction đi vào đâu? | Nút "Không đúng" → log query + response + correction tag → weekly review bởi XanhSM ops team |
| 2 | Product thu signal gì để biết tốt lên hay tệ đi? | (a) Implicit: tài xế có bấm "Xem tài liệu gốc" không? Nếu hay bấm → AI chưa trả lời đủ rõ. (b) Explicit: thumbs up/down sau mỗi câu trả lời. (c) Correction: câu nào bị báo sai → thêm vào eval test set. |
| 3 | Loại data | ☑ Domain-specific (chính sách XanhSM) · ☑ Human-judgment (ops team verify) · ☑ Correction (tài xế báo sai) |

**Marginal value:** Tài liệu chính sách XanhSM là data độc quyền — không model nào có sẵn. Mỗi correction từ tài xế là signal về edge case thực tế, không ai khác có được. Đây là data flywheel thực sự.

---

## 2. User Stories × 4 Paths

**Persona:** Anh Minh, 34 tuổi, tài xế XanhSM 2 năm, chạy ca sáng 6h–14h. Dùng Android đời 2021, hay dùng điện thoại khi đỗ xe chờ khách.

---

### Path 1 — Happy: AI trả lời đúng

> **Trigger:** Anh Minh nhận được thông báo bị trừ 50k, không hiểu tại sao.

**Hành động:** Mở app → gõ "tại sao tôi bị trừ tiền hôm qua?"

**AI làm gì:**
- Nhận dạng query → retrieve đúng mục "Chính sách khấu trừ" + "Lỗi vi phạm"
- Trả lời: "Theo chính sách tháng 4/2026, tài xế bị trừ 50k nếu hủy chuyến sau khi đã nhận — áp dụng từ lần thứ 3 trong tháng."
- Hiển thị: đoạn tài liệu gốc thu gọn bên dưới + timestamp "Cập nhật 01/04/2026"

**Anh Minh thấy gì:** Câu trả lời rõ ràng + nguồn → hiểu ngay, không cần hành động thêm.

**Value moment:** Tiết kiệm 10 phút gọi tổng đài, có câu trả lời chính xác ngay trên xe.

---

### Path 2 : AI không chắc

> **Trigger:** Anh Minh gặp tình huống lạ — khách đặt xe rồi nhờ đổi điểm đến sang tỉnh khác giữa chừng.

**Hành động:** Gõ "khách muốn đổi từ Hà Nội đi Hải Phòng được không, tôi xử lý thế nào?"

**AI làm gì:**
- Retrieve — không tìm thấy policy rõ ràng cho trường hợp liên tỉnh
- **Không đoán bừa.** Hiển thị:
  > "Tôi tìm thấy quy định về đổi điểm đến trong nội thành, nhưng chưa có thông tin rõ ràng về chuyến liên tỉnh. Độ tin cậy: Thấp."
- Hiện 2 lựa chọn: [Xem quy định gần nhất] [Gọi hỗ trợ ngay — 1900xxxx]

**Anh Minh thấy gì:** AI thành thật về giới hạn của mình → tài xế không hành động sai vì tin nhầm.

**Design principle:** Badge màu vàng "Cần xác nhận" — không dùng màu đỏ (không phải lỗi) cũng không dùng màu xanh (không phải chắc chắn).

---

### Path 3: AI trả lời sai

> **Trigger:** AI trả lời nhầm mức thưởng cuối tuần (dùng tài liệu cũ tháng 3 thay vì tháng 4).

**Anh Minh phát hiện:** Làm theo hướng dẫn nhưng không nhận được thưởng như AI nói → nghi ngờ.

**Recovery flow (tối đa 2 bước):**
1. Bấm "Câu trả lời này không đúng" ngay dưới message
2. Chọn lý do nhanh: [Thông tin cũ] [Không áp dụng cho TH của tôi] [Khác]
→ App ghi nhận + tự động gợi ý "Bạn muốn gọi hỗ trợ để xác nhận không?"

**Hệ thống làm gì sau đó:**
- Log query này vào error queue
- Ops team review trong vòng 24h
- Nếu xác nhận tài liệu cũ → cập nhật knowledge base + tag tất cả query tương tự là "Cần verify"

**Thiệt hại giới hạn:** Tài xế mất 5 phút gọi hotline xác nhận — không phải mất tiền thật vì đây là augmentation (tài xế vẫn check trước khi hành động).

---

### Path 4 : Tài xế mất niềm tin

> **Trigger:** Sau 2 lần nhận thông tin sai về chính sách, anh Minh không tin app nữa.

**Lối thoát rõ ràng:**
- Nút "Hotline hỗ trợ" luôn hiện ở góc trên — không bị ẩn sau menu
- Khi tài xế bấm "Không đúng" lần thứ 2 trong session → app tự động hỏi "Bạn có muốn nói chuyện trực tiếp với nhân viên hỗ trợ không?"

**Giai thích:**
- Với mỗi câu trả lời: "Câu trả lời từ: [Tên tài liệu] · Cập nhật: [ngày]"
- Tài xế biết AI dựa vào tài liệu gì → có thể tự đánh giá độ tin cậy

**Opt-out:**
- Trong Settings: "Tắt gợi ý AI, chỉ hiển thị tài liệu gốc" → app trở thành search engine đơn giản, không dùng AI

---

## 3. Eval Metrics

### 3 chỉ số chính

| # | Metric | Đo bằng cách nào | Threshold "đủ tốt" | Red flag |
|---|--------|-----------------|-------------------|----------|
| 1 | **Retrieval Accuracy** — AI tìm đúng tài liệu liên quan không? | Ground truth: 100 câu hỏi mẫu do ops team viết, check xem top-3 chunks có chứa câu trả lời đúng không | ≥ 85% | < 70%: knowledge base cần restructure |
| 2 | **Answer Faithfulness** — AI có bịa thông tin ngoài tài liệu không? | Human eval: 50 câu trả lời ngẫu nhiên/tuần, check từng claim có trong source doc không | ≥ 95% (zero tolerance cho hallucination về số tiền/mức phạt) | < 90%: tắt tính năng, review prompt |
| 3 | **Escalation Precision** — Khi AI nói "Cần xác nhận", có đúng là cần xác nhận không? | Ops team verify 20 câu "Cần xác nhận"/tuần, check xem có thực sự unclear không | ≥ 80% | < 60%: AI đang over-hedge, mất tín nhiệm |

### Precision vs Recall — lựa chọn

**Ưu tiên Precision cao hơn Recall** cho metric số 2 (faithfulness).

Lý do: Tài xế bị phạt tiền oan vì làm theo thông tin sai = thiệt hại tài chính thật + mất niềm tin vào XanhSM. Bỏ sót 1 trường hợp (nói "không biết" khi thực ra biết) chỉ khiến tài xế mất thêm 5 phút gọi hotline — chấp nhận được.

**Recall quan trọng hơn** cho metric số 1 (retrieval) — bỏ sót tài liệu liên quan còn nguy hiểm hơn retrieve thừa.

### Eval iteration plan

```
Chạy 100 câu hỏi mẫu thủ công → ghi nhận lỗi nào nhiều nhất
Sửa chunking strategy / prompt → chạy lại → so sánh
Automation — log production queries → weekly human spot-check 50 câu
```

---

## 4. Top 3 Failure Modes

### Failure Mode 1: Tài liệu cũ — AI trả lời theo chính sách đã hết hạn

| | Chi tiết |
|--|---------|
| **Trigger** | XanhSM cập nhật chính sách thưởng/phạt nhưng knowledge base chưa được sync |
| **Hậu quả** | Tài xế làm theo thông tin cũ → không nhận được thưởng hoặc bị phạt oan → khiếu nại XanhSM, mất niềm tin vào app |
| **Mitigation** | (1) Mỗi chunk trong knowledge base có timestamp. (2) AI luôn hiển thị "Tài liệu ngày X" — tài xế tự đánh giá. (3) Khi tài liệu > 30 ngày không được cập nhật → auto-badge "Có thể đã hết hạn". (4) Pipeline sync tài liệu mới mỗi 7 ngày. |

---

### Failure Mode 2: Hallucination về con số cụ thể (mức thưởng, mức phạt)

| | Chi tiết |
|--|---------|
| **Trigger** | Query hỏi về số tiền cụ thể (ví dụ: "thưởng chuyến VIP là bao nhiêu?") mà tài liệu không có con số rõ ràng → AI suy diễn/bịa |
| **Hậu quả** | Nghiêm trọng nhất — tài xế tin vào con số sai, hoặc claim XanhSM nợ tiền dựa trên thông tin AI bịa. Rủi ro pháp lý cho XanhSM. |
| **Mitigation** | (1) System prompt: "Nếu không tìm thấy con số cụ thể trong tài liệu, KHÔNG ĐƯỢC suy đoán. Trả lời: 'Tôi không tìm thấy thông tin này, vui lòng gọi hotline.'" (2) Post-processing: nếu response chứa số tiền mà không có citation → tự động flag, không hiển thị, chuyển sang "Không tìm thấy". (3) Eval weekly: 100% câu trả lời có số tiền đều được human check. |

---

### Failure Mode 3: Misclassify sự cố — AI hướng dẫn sai quy trình xử lý

| | Chi tiết |
|--|---------|
| **Trigger** | Tài xế mô tả sự cố mơ hồ ("khách không chịu xuống xe") → AI classify nhầm loại incident → retrieve sai SOP → hướng dẫn sai bước xử lý |
| **Hậu quả** | Tài xế không thu thập đúng bằng chứng / báo cáo sai kênh → khi khiếu nại xảy ra, tài xế không có đủ căn cứ để bảo vệ mình |
| **Mitigation** | (1) Với query về sự cố: AI luôn hỏi lại 1 câu clarifying trước khi trả lời: "Khách đã xuống xe chưa? / Chuyến đã hoàn thành chưa?" (2) Khi không chắc chắn về loại sự cố → hiện top 2 SOP khả năng nhất để tài xế chọn. (3) Luôn kèm: "Nếu sự cố nghiêm trọng, gọi ngay hotline 1900xxxx — đừng chờ app." |

---

## 5. ROI — 3 Kịch bản

### Baseline (hiện tại, không có AI)
- Hotline nhận ~500 cuộc/ngày từ tài xế hỏi chính sách/sự cố
- 1 nhân viên hỗ trợ xử lý ~80 cuộc/ngày = 6–7 nhân viên cho mảng này
- Chi phí: ~6 nhân viên × 8 triệu/tháng = **48 triệu/tháng**
- Tài xế: chờ trung bình 8 phút/cuộc → mất ~67 giờ tài xế/ngày (500 cuộc × 8 phút)

### Chi phí vận hành AI (ước tính)
- Infrastructure: ~$50/tháng (vector DB + hosting)
- API cost: ~$150/tháng (50k queries × $0.003)
- Maintenance: 0.5 FTE ops (~4 triệu/tháng)
- **Tổng: ~5.5 triệu/tháng**

---

| | Conservative | Realistic | Optimistic |
|---|---|---|---|
| **Giả định** | AI xử lý 30% queries thành công, adoption chậm (20% tài xế dùng) | AI xử lý 60% queries, adoption trung bình (50% tài xế dùng) | AI xử lý 80% queries, adoption cao (80% tài xế), data flywheel hoạt động |
| **Hotline giảm** | 15% (~75 cuộc/ngày) | 35% (~175 cuộc/ngày) | 55% (~275 cuộc/ngày) |
| **Nhân sự tiết kiệm** | 1 FTE (~8 triệu/tháng) | 2–3 FTE (~20 triệu/tháng) | 4 FTE (~32 triệu/tháng) |
| **Giá trị tài xế** (thời gian tiết kiệm) | 10 giờ/ngày × 200k/giờ = 2 triệu/ngày = ~60 triệu/tháng | 30 giờ/ngày = ~180 triệu/tháng | 55 giờ/ngày = ~330 triệu/tháng |
| **Chi phí AI** | 5.5 triệu/tháng | 5.5 triệu/tháng | 5.5 triệu/tháng |
| **Net benefit** | ~62.5 triệu/tháng | ~194.5 triệu/tháng | ~356.5 triệu/tháng |
| **ROI** | 11x | 35x | 65x |

### Kill criteria
Dừng hoặc pivot khi:
- Answer Faithfulness < 90% trong 2 tuần liên tiếp (rủi ro pháp lý)
- Tỷ lệ tài xế báo sai > 15% tổng queries
- Chi phí API vượt 30% tiết kiệm hotline

---

## 6. Mini AI Spec 

```
════════════════════════════════════════════════════════
TRỢ LÝ AI CHO TÀI XẾ XANHSM — Mini Spec
════════════════════════════════════════════════════════

VẤN ĐỀ
  Tài xế XanhSM không có nơi tra cứu nhanh chính sách
  và quy trình sự cố — hotline chờ lâu, tài liệu khó đọc,
  hỏi đồng nghiệp hay sai.

GIẢI PHÁP
  RAG chatbot: tài xế hỏi bằng tiếng Việt thường ngày
  → AI tìm trong tài liệu chính thức → trả lời + trích nguồn.
  Khi không chắc → nói thẳng + đưa hotline.

NGƯỜI DÙNG
  Tài xế XanhSM đang chạy ca, dùng điện thoại Android.

LOẠI AI
  Augmentation (AI gợi ý, tài xế quyết định hành động).
  Không automation — cost of error quá cao.

STACK
  LangGraph (multi-node: classify → retrieve → answer → escalate)
  + FAISS/Chroma vector DB + GPT-4o-mini + Streamlit/React Native

DATA SOURCE
  Tài liệu nội bộ XanhSM: chính sách thưởng/phạt,
  SOP sự cố, hợp đồng tài xế, FAQ.
  crawl data/mock docs (~20 trang).

SUCCESS METRICS
  - Retrieval Accuracy ≥ 85%
  - Answer Faithfulness ≥ 95% (zero hallucination về số tiền)
  - Escalation Precision ≥ 80%

TOP RISK
  Tài liệu cũ → hiển thị timestamp + sync 7 ngày/lần.
  Hallucination số tiền → post-process filter + human eval.
  Misclassify sự cố → hỏi lại 1 câu trước khi trả lời.

4 PATHS
  Happy: Trả lời + hiện nguồn
  Low-conf: Badge "Cần xác nhận" + gợi ý hotline  
  Failure: Nút báo sai 1 bấm → ops team review 24h
  Recovery: Hotline luôn hiện + option tắt AI hoàn toàn

ROI (Realistic)
  Tiết kiệm 2–3 FTE hotline + 30h tài xế/ngày
  ≈ 194 triệu/tháng net benefit vs 5.5 triệu chi phí = 35x ROI

LEARNING SIGNAL
  Implicit: click "Xem tài liệu gốc" (AI chưa đủ rõ)
  Explicit: thumbs up/down
  Correction: nút "Không đúng" → error queue → weekly review

════════════════════════════════════════════════════════
```

---

## Phân công (gợi ý)

| Người | Phần |
|-------|------|
| Hoàng Tuấn Anh | Canvas + User Stories 4 paths  |
| Nguyễn Quang Trường | Mini-spec (hoàn thiện)|
| Vũ Hồng Quang | Eval metrics  |
| Đàm Lê Văn Toàn | Failure modes +  tài liệu XanhSM |
| Phạm Tuấn Anh | ROI refinement + Prototype setup (LangGraph skeleton) |
| Vũ Lê Hoàng | test cases mẫu |
---
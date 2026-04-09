# PROJECT PLAN — Trợ Lý AI Tài Xế XanhSM
**Track D · Phiên bản 4.0 · NHM Team**  
Cập nhật: 09/04/2026

---

## Tổng quan kiến trúc

```
[Streamlit Frontend]
        │  HTTP POST /chat (message, thread_id)
        ▼
[FastAPI Backend — main_v3.py]
        │  app_graph.invoke()
        ▼
[LangGraph — agent_graph_v4.py]
  classify_node
       │
       ├─ needs_clarification=True ──► END (hỏi lại tài xế)
       │
  retrieve_node  (HybridRAGRetriever)
       │
  answer_node
       │
       ├─ escalate=False ────────────► END (trả lời + badge)
       │
  escalate_node ──────────────────────► END (hotline prompt)
        │
[HybridRAGRetriever — retrieval_advanced.py]
  FAISS (dense)  ─┐
  BM25  (sparse) ─┤─► RRF ─► CrossEncoder Rerank ─► top-5 chunks
                  └─── SQLite (chunk store)
```

---

## I. ĐÃ HOÀN THÀNH

### 1. Core RAG Pipeline (retrieval_advanced.py)

| Thành phần | Chi tiết | Mapping spec |
|---|---|---|
| **FAISS Dense Retrieval** | `paraphrase-multilingual-MiniLM`, cosine similarity, `candidate_k=20` | Spec §6: FAISS/Chroma vector DB |
| **BM25 Sparse Retrieval** | `BM25Okapi`, tokenize whitespace, score > 0 filter | Bổ sung ngoài spec — cải thiện recall cho từ khóa chính xác (tên quy định, mức phạt) |
| **Reciprocal Rank Fusion** | RRF(k=60) merge dense + sparse | Bổ sung ngoài spec |
| **Cross-Encoder Reranker** | `ms-marco-MiniLM-L-6-v2`, chạy trên `candidate_k` chunks sau RRF, không scan toàn corpus | Bổ sung ngoài spec — giảm latency so với rerank toàn bộ |
| **SQLite Chunk Store** | Tương thích schema `faiss_index_map` + `chunks` của team Data | Đảm bảo không breaking change với pipeline Data team |
| **In-memory cache** | `_chunk_cache: dict[int, _Candidate]` — tránh query SQLite lặp mỗi request | Latency optimization |

**Kết quả đo được (ước tính):** Pipeline đơn FAISS → ~1.2s; Hybrid + Reranker → ~2.1s — nằm trong SLA 2–4s của spec.

---

### 2. LangGraph Multi-Node Agent (agent_graph_v4.py)

| Node | Chức năng | Fix đáng chú ý |
|---|---|---|
| `classify_node` | Phân loại query, xác định `user_persona` (driver/prospect), detect `needs_clarification` | **FIX-2**: truyền lịch sử hội thoại vào LLM — giải quyết câu hỏi tham chiếu như "cái bạn vừa nói" |
| `retrieve_node` | Gọi `HybridRAGRetriever._get_relevant_documents()` | **FIX-1**: sửa lỗi gọi `invoke()` trả về list rỗng âm thầm — đây là bug gốc khiến context luôn rỗng → always escalate |
| `answer_node` | Sinh câu trả lời, gán `confidence`, detect `has_money_figure` | **FIX-3**: nới lỏng escalation logic — `confidence=low` không số tiền → vẫn trả lời partial + badge, không escalate |
| `escalate_node` | Chỉ kích hoạt khi: context rỗng HOẶC `has_money_figure=True + confidence≠high` | Mapping spec §4 Failure Mode 2: zero hallucination về số tiền/mức phạt |

**Conversation memory**: `MemorySaver` + `thread_id` — duy trì ngữ cảnh hội thoại qua nhiều turn, tránh lặp câu hỏi ở escalate.

---

### 3. FastAPI Backend (main_v3.py)

| Endpoint | Schema | Mapping spec |
|---|---|---|
| `POST /chat` | Request: `{message, thread_id}` → Response: `{reply, confidence, query_type, escalate, sources, thread_id}` | Spec 2 Path 1, 2, 3 |
| `POST /feedback` | `{thread_id, message_index, reason, detail}` | Spec 2 Path 3: nút "Câu trả lời này không đúng" → log vào error queue → ops team review 24h |
| `GET /health` | Liveness check | Production readiness |
| **Lifespan hook** | `get_retriever()` tại startup — preload FAISS + reranker, tránh cold start ở request đầu tiên | Latency SLA |

---

### 4. Streamlit Frontend (app.py)

| Feature | Chi tiết | Mapping spec |
|---|---|---|
| **Confidence badge CSS** | `.conf-low` (vàng) / `.conf-high` (xanh) | Spec §2 Path 2: "badge màu vàng Cần xác nhận" |
| **Source citation tags** | `.source-tag` hiển thị `section_title` từng chunk | Spec §1 Trust: "luôn hiển thị đoạn tài liệu gốc bên dưới" |
| **Hotline button** | Hiện khi `failure_count ≥ 2` | Spec §2 Path 4: "hotline luôn hiện, tài xế không bao giờ bị bế tắc" |
| **Suggested questions** | 4 câu gợi ý sidebar | UX cho tài xế đang chạy ca, không muốn gõ |
| **Thread persistence** | `st.session_state.thread_id` = UUID, reset khi xóa lịch sử | Duy trì context hội thoại multi-turn |

---

## II. GÁP SO VỚI SPEC — CẦN LÀM

### Ưu tiên Cao (P0) — Liên quan trực tiếp Trust & Safety

| # | Gap | Spec requirement | Rủi ro nếu thiếu |
|---|---|---|---|
| G1 | **Timestamp tài liệu chưa hiển thị** | "Luôn hiển thị Cập nhật [ngày]" — spec §2 Path 1 | Failure Mode 1: tài xế không biết tài liệu cũ, thực hiện sai quy trình |
| G2 | **Auto-badge "Có thể đã hết hạn"** | Chunk > 30 ngày chưa sync → hiện badge cảnh báo — spec §4 FM1 | Tài xế tin thông tin cũ → bị phạt oan |
| G3 | **Post-processing filter số tiền** | "Nếu response chứa số tiền mà không có citation → tự động flag, không hiển thị" — spec §4 FM2 | Hallucination số tiền qua được LLM-level check → rủi ro pháp lý cho XanhSM |
| G4 | **Thumbs up/down per message** | Spec §1 Learning Signal: explicit feedback | Không có explicit signal để cải thiện model |

### Ưu tiên Trung (P1) — UX & Product Quality

| # | Gap | Spec requirement | Ghi chú |
|---|---|---|---|
| G5 | **"Xem tài liệu gốc" expandable** | Implicit signal: tài xế bấm → AI chưa đủ rõ — spec §1 Learning Signal | Hiện tại chỉ show source tag, không expand nội dung gốc |
| G6 | **Hiện top 2 SOP khi incident ambiguous** | "Khi không chắc loại sự cố → hiện top 2 SOP khả năng nhất để tài xế chọn" — spec §4 FM3 | classify_node có `needs_clarification` nhưng chưa render top-2 option |
| G7 | **Knowledge base sync pipeline** | Sync tài liệu mới mỗi 7 ngày — spec §4 FM1 | Hiện là manual re-index |

### Ưu tiên Thấp (P2) — Nice-to-have

| # | Gap | Spec requirement |
|---|---|---|
| G8 | **Opt-out AI trong Settings** | "Tắt gợi ý AI, chỉ hiển thị tài liệu gốc" — spec §2 Path 4 |
| G9 | **Eval pipeline tự động** | 100 câu hỏi mẫu ground truth + weekly spot-check 50 câu — spec §3 |
| G10 | **Error queue + Slack webhook** | Hiện là `logger.info` — spec §2 Path 3: "ops team review trong 24h" |

---

## III. ROADMAP

### Sprint 1 (1 tuần) — Trust & Safety

```
G1: Thêm trường `updated_at` vào schema chunks SQLite
    → Hiển thị "Cập nhật [ngày]" ngay dưới source tag ở frontend

G2: Thêm logic kiểm tra `updated_at > 30 ngày`
    → Tự động gán badge "Có thể đã hết hạn" vào metadata chunk

G3: Post-processing regex/rule trong answer_node
    → Detect số tiền (VNĐ pattern) trong response
    → Nếu không match với citation chunk → override answer = escalate message
```

**Acceptance criteria:** 100% câu trả lời có số tiền đều có citation chunk đi kèm, không có response vượt qua filter mà không có nguồn.

---

### Sprint 2 (1 tuần) — Feedback Loop & Eval

```
G4: Thêm thumbs up/down component vào Streamlit
    → POST /feedback với reason="helpful"/"not_helpful"
    → Lưu vào bảng feedback_log trong SQLite

G9: Build eval script
    → 100 câu hỏi mẫu từ ops team (ground truth chunk_id)
    → Đo Retrieval Accuracy: top-3 chunks có chứa ground truth không?
    → Đo Escalation Precision: câu nào bị "Cần xác nhận" có thực sự unclear không?
    → Output: report markdown so sánh qua các lần chạy

G10: Thay logger.info bằng write vào bảng feedback_queue
     → Cron job hoặc Slack webhook hàng ngày gửi summary cho ops team
```

**Acceptance criteria:** Retrieval Accuracy ≥ 85%, Escalation Precision ≥ 80% trên eval set 100 câu.

---

### Sprint 3 (1 tuần) — UX & Reliability

```
G5: Expandable "Xem tài liệu gốc" với nội dung chunk đầy đủ
    → Streamlit st.expander() hoặc React collapsible
    → Log click event → POST /feedback với reason="expand_source"

G6: Render top-2 SOP khi classify trả về needs_clarification
    → Frontend hiện 2 button option thay vì chỉ hiện câu hỏi text

G7: Knowledge base sync script
    → Cron job mỗi 7 ngày: crawl/fetch tài liệu mới
    → Re-embed, cập nhật SQLite + FAISS index
    → Gửi notification khi sync thành công/thất bại
```

---

### Sprint 4 (dài hạn) — Scale

```
G8: Settings page — opt-out AI
    → Mode "Chỉ tìm kiếm tài liệu" (BM25 only, không LLM)
    → Dành cho tài xế mất niềm tin — spec §2 Path 4

Data flywheel:
    → Mỗi correction từ tài xế → thêm vào eval test set
    → Câu nào bị flag sai + ops team xác nhận → trigger re-chunk tài liệu liên quan
    → Mỗi vòng eval → so sánh Retrieval Accuracy trước/sau re-chunk

Cân nhắc nâng cấp reranker:
    → cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 cho tiếng Việt heavy
    → Benchmark latency delta trước khi merge vào production
```

---

## IV. KILL CRITERIA

Theo spec §5:

| Điều kiện | Hành động |
|---|---|
| Answer Faithfulness < 90% trong 2 tuần liên tiếp | Tắt feature, review toàn bộ prompt + chunking |
| Tỷ lệ tài xế báo sai > 15% tổng queries | Freeze model, ops team review manual toàn bộ |
| Chi phí API > 30% tiết kiệm hotline | Chuyển sang GPT-4o-mini self-hosted hoặc cắt giảm candidate_k |

---

## V. CẤU TRÚC FILE DỰ ÁN

```
backend_ai/
├── app/
│   ├── core/
│   │   ├── agent_graph_v4.py      ✅ LangGraph multi-node
│   │   └── config.py
│   ├── prompts/
│   │   └── system_prompt_v4.py    (CLASSIFY, ANSWER, ESCALATE prompts)
│   ├── utils/
│   │   └── retrieval_advanced.py  ✅ Hybrid RAG + Reranker
│   └── main_v3.py                 ✅ FastAPI entrypoint
├── data/
│   ├── xanhsm.db                  SQLite chunk store
│   └── xanhsm.faiss               FAISS index
frontend/
└── app.py                         ✅ Streamlit UI
```

---

## VI. PHÂN CÔNG ĐỀ XUẤT (cập nhật)

| Người | Sprint 1 | Sprint 2 |
|---|---|---|
| Hoàng Tuấn Anh | G1 — timestamp display frontend | G5 — expandable source |
| Nguyễn Quang Trường | G3 — post-processing filter số tiền | G6 — top-2 SOP UI |
| Vũ Hồng Quang | G9 — eval script + ground truth set | Duy trì eval weekly |
| Đàm Lê Văn Toàn | G2 — auto-badge tài liệu cũ + G7 sync script | G7 cron job |
| Phạm Tuấn Anh | G4 — thumbs up/down + feedback schema | G10 Slack webhook |
| Vũ Lê Hoàng | Viết 100 câu hỏi mẫu ground truth | Review escalation precision |

---

*Tài liệu này reflect trạng thái code tại commit v4 (agent_graph_v4 + retrieval_advanced + main_v3). Cập nhật mỗi sprint.*
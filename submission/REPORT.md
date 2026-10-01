# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Chỉ cần 3 output text và 5 ảnh runtime; dùng đường dẫn tương đối, ví dụ `evidence/03-incident-trace.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lê Thanh Tình
- **MSSV:** 2A202602449
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/lttinh/K4-L3-Day13-LeThanhTinh-02449-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-02449`

## 2. Evidence index

Giữ đúng ba output text và năm ảnh dưới đây. Không tách thêm ảnh; nếu cần giải thích, ghi bằng chữ trong các mục sau.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/pytest.txt` |
| Log validator | `evidence/log-validator.txt` |
| Dashboard validator | `evidence/dashboard-validator.txt` |
| Structured log + incident log | `evidence/01-incident-log.png` |
| Trace list | `evidence/02-trace-list.png` |
| Trace waterfall + metadata + incident trace | `evidence/03-incident-trace.png` |
| Prompt versions + promote/rollback | `evidence/04-prompt-versioning.png` |
| Dashboard + incident metric | `evidence/05-dashboard-incident.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Chưa đạt trước CP1 | 100/100 | Đạt schema, correlation ID, enrichment và PII scrubbing |
| `validate_dashboard.py` | Chưa đủ contract | HỢP LỆ: 6/6 panel | Đủ field, aggregation, unit, query và threshold |
| `pytest` | Chưa ghi nhận | 28 passed | Chạy bằng virtualenv, toàn bộ public tests qua trong 5,05 giây |
| Số traces hợp lệ | 0 | 10 root traces / 30 observations | Mỗi request có `lab-agent-run`, `retrieval`, `generation` trong project cá nhân |
| Số PII leak | Chưa ghi nhận | 0 | Theo `scripts/validate_logs.py` trên 124 log records |
| Latency P95 / TTFT P95 | Chưa ghi nhận | 3728 ms / 73 ms | Dashboard evidence cuối, cửa sổ 60 phút lúc 03:34 UTC ngày 2026-10-01 |
| Retrieval success rate | Chưa ghi nhận | 100% | Retrieval không lỗi; sự cố biểu hiện bằng latency của span retrieval |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ, giữ `x-request-id` hợp lệ do client gửi hoặc sinh ID dạng `req-<8-hex>`, bind vào context rồi trả lại qua response header. ID này được truyền vào `LabAgent.run` và metadata của trace.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, event, timestamp; response còn có latency, TTFT, token, cost, quality và trạng thái retrieval.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor scrub PII chạy trước JSON renderer/file writer; user ID được hash và trace chỉ lưu preview đã scrub thay vì raw prompt/output.
- **Cách kiểm chứng kết quả:** `scripts/validate_logs.py` phân tích 124 records, không thiếu required field/enrichment và không phát hiện PII; kết quả 100/100.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Tôi chạy workload trên máy cá nhân và kiểm tra project `day13-k4-l3b-02449`; danh sách Langfuse hiển thị 10 root observations và tổng 30 observations do lần chạy này tạo.
- **Cấu trúc root/retrieval/generation observations:** Trace `day13-agent-request` chứa root `lab-agent-run`; bên dưới có `retrieval` kiểu retriever và `generation` kiểu generation. Generation ghi model, usage token, cost và TTFT nhưng không capture raw input/output.
- **Cách nối trace với log:** Metadata trace chứa cùng `correlation_id` với structured log; dùng ID này để lọc một request trong `data/logs.jsonl` rồi tìm đúng trace trên Langfuse.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** Version 1, label `baseline`; sau rollback label `production` trỏ về v1.
- **Version/label candidate:** Version 2, label `candidate` và `latest`; v2 từng được promote thành `production` để chạy so sánh.
- **Trace ID của mỗi version:** Trace production v1: `b0bdf1833e59db07efc13b25b36a3c81`; trace production v2: `fa573fdae987b98b8a328c5ebcb0720c`.
- **Cách promote và rollback `production`:** Gán `production` cho v2 và chạy workload; trace `fa573fdae987b98b8a328c5ebcb0720c` xác nhận `prompt_version=2`, `prompt_label=production`. Sau đó chuyển `production` về v1; trang versions xác nhận v1 giữ `baseline + production`, còn v2 giữ `candidate + latest`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard đọc `data/logs.jsonl` trong cửa sổ 60 phút và có đúng 6 panel: latency (P50/P95/P99 và TTFT P95), traffic, error rate/retrieval success, cost, input/output tokens và quality proxy. Mỗi panel có đơn vị, query và threshold; validator đạt 6/6.
- **SLO và lý do chọn:** 99,5% request trong cửa sổ 28 ngày phải trả response thành công trong tối đa 3000 ms. Ngưỡng này kết hợp availability và latency mà người dùng trực tiếp cảm nhận, đồng thời P95/P99 giúp phát hiện tail latency.
- **Cách tính error budget:** Error budget là `100% - 99,5% = 0,5%`. Với 10.000 request, số request được phép lỗi hoặc vượt 3000 ms là `10.000 × 0,005 = 50`.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (warning, P95 > 3000 ms trong 5 phút), `HighRequestErrorRate` (critical, error rate > 2% trong 5 phút), và `LowRetrievalSuccessRate` (warning, retrieval success < 90% trong 10 phút). Cả ba gửi Slack `#k4-l3b-alerts`, owner `student-02449`, và trỏ tới từng mục trong `docs/alerts.md`.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`; incident `rag_slow`; seed `1312`; affected feature `monitoring`.
- **Khoảng thời gian điều tra:** 2026-10-01 02:38:17–02:54:51 UTC; dashboard dùng time range 60 phút và trace đại diện thuộc lần chạy có Langfuse tracing bật lúc 02:54 UTC.
- **Triệu chứng từ metrics:** Dashboard evidence cuối có 24 requests với P50 2661 ms, P95 3728 ms, P99 4000 ms và TTFT P95 73 ms; error rate 0%, retrieval success 100%. Tail latency vượt SLO 3000 ms, trong khi TTFT thấp và hệ thống không phát sinh lỗi.
- **Log line và correlation ID liên quan:** `response_sent`, `correlation_id=req-ed03a188`, session `k4-l3b-challenge-s05`, feature `monitoring`, latency 2661 ms, TTFT 50 ms, `tool_name=retrieval`, `tool_success=true`, timestamp `2026-10-01T02:54:51.606851Z`.
- **Trace ID và span gây ảnh hưởng:** Trace `5b4d72dc174ede37f65c148db5884484` có cùng `correlation_id=req-ed03a188`. Root `lab-agent-run` mất 2,66 giây; child `retrieval` mất 2,50 giây, trong khi `generation` chỉ mất 0,15 giây, dùng 138 tokens và cost 0,00165 USD.
- **Root cause:** Cấu hình challenge chính thức bật incident `rag_slow`. Metrics cho thấy tail latency tăng, log xác nhận request thành công nhưng mất 2661 ms, và trace cùng correlation ID cho thấy gần như toàn bộ thời gian nằm ở span `retrieval` (2,50/2,66 giây). Vì generation chỉ 0,15 giây và TTFT 50 ms, retrieval chậm là root cause, không phải LLM generation.
- **Fix action:** Tắt incident `rag_slow`/khôi phục retrieval dependency, sau đó chạy lại cùng workload để xác nhận latency trở về baseline.
- **Preventive measure:** Duy trì alert P95 latency và theo dõi riêng retrieval span duration; bổ sung timeout/fallback cho retrieval và regression test đối với tail latency.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Dùng cùng `correlation_id` trong response header, structured log và trace metadata. Quyết định này cho phép chuyển từ triệu chứng tổng hợp trên dashboard sang đúng request và đúng span mà không lưu raw PII.
- **Một lỗi/blocker đã gặp:** Lần chạy challenge đầu tiên có `tracing_enabled=false` vì API được khởi động mà chưa nạp `.env`; metric và log tồn tại nhưng không có trace Langfuse tương ứng.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra event `app_started` và endpoint `/health`, phát hiện tracing bị tắt; sau đó khởi động lại bằng `uvicorn app.main:app --reload --env-file .env`, xác nhận `tracing_enabled=true` rồi chạy lại workload.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cho biết tail latency tăng trong cửa sổ thời gian; log cung cấp request đại diện `req-ed03a188`; trace cùng ID cho thấy retrieval mất 2,50/2,66 giây và generation chỉ mất 0,15 giây, từ đó định vị root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Version và label giúp biết chính xác prompt nào tạo response và cho phép rollback nhanh; token/cost phát hiện thay đổi gây tốn tài nguyên; SLO/error budget biến chất lượng kỳ vọng thành ngưỡng đo và cảnh báo vận hành.
- **Điều quan trọng nhất đã học:** Không kết luận sự cố từ một tín hiệu riêng lẻ; cần dùng metric để khoanh vùng, log để chọn request và trace để chứng minh span gây ảnh hưởng.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Chưa mô phỏng vector store/LLM thật; ứng dụng dùng mock dependency nên các ngưỡng và chi phí chỉ đại diện cho bài lab. Repository URL đã có, còn commit SHA cuối và thao tác nộp LMS được cập nhật sau khi tạo commit nộp bài.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Có đúng 3 file text và 5 ảnh runtime theo hướng dẫn.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.

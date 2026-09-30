# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của các event `response_sent`; SLO phản hồi thành công trong 3000 ms.
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: phần lớn request vẫn thành công nhưng nhóm chậm phải chờ quá ngưỡng SLO.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** xác nhận P95/P99 và TTFT P95 tăng trong cùng cửa sổ trên dashboard.
  2. **Logs:** lọc `response_sent` có `latency_ms > 3000`, lấy một `correlation_id` đại diện.
  3. **Traces:** mở trace cùng ID và so sánh thời gian `retrieval` với `generation`.
- Mitigation tạm thời: tắt incident/practice đang bật; nếu generation và token tăng sau đổi prompt thì rollback label `production`; nếu retrieval chậm thì chuyển sang fallback context trong lúc khôi phục nguồn dữ liệu.
- Owner: `student-02449`

## Alert 2

- Tên: `HighRequestErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỷ lệ `request_failed / request_received`; error budget 0,5% trong 28 ngày.
- Điều kiện và thời gian duy trì: error rate lớn hơn 2% liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: request trả HTTP 500 và không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** xác nhận error rate và breakdown `error_type` trong cửa sổ cảnh báo.
  2. **Logs:** lọc `request_failed`, chọn một `correlation_id` và kiểm tra `error_type`, `tool_name`, `tool_success`.
  3. **Traces:** mở trace cùng ID để xác định observation lỗi và trạng thái các span trước đó.
- Mitigation tạm thời: tắt cấu hình gây lỗi, khôi phục dependency retrieval hoặc bật fallback; nếu trùng thời điểm deploy/prompt change thì rollback thay đổi gần nhất có bằng chứng.
- Owner: `student-02449`

## Alert 3

- Tên: `LowRetrievalSuccessRate`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: retrieval success rate tối thiểu 90% trên mọi event có `tool_success`.
- Điều kiện và thời gian duy trì: tỷ lệ `tool_success == true` thấp hơn 90% trong 10 phút.
- Ảnh hưởng tới người dùng: API có thể lỗi hoặc trả lời thiếu context, làm giảm quality dù generation vẫn hoạt động.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** xác nhận retrieval success giảm và đối chiếu error rate/quality trong cùng cửa sổ.
  2. **Logs:** lọc event có `tool_success=false`, lấy `correlation_id`, `error_type` và feature bị ảnh hưởng.
  3. **Traces:** mở trace cùng ID, kiểm tra `retrieval` observation và liệu `generation` có được gọi hay không.
- Mitigation tạm thời: dùng context fallback an toàn, kiểm tra kết nối vector store và tắt incident `tool_fail`; không che lỗi bằng cách ghi `tool_success=true` giả.
- Owner: `student-02449`

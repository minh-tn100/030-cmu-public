# Kết quả Giai đoạn 2 (baseline)

Cấu hình: LLM = **StubLLM tất định** (quy tắc, không phải mô hình thật); nhãn = **tự gán của tác giả**; bộ nhúng = vector từ tĩnh; kho = 15 đoạn. Chạy qua MCP server thật (`--mcp`) và gọi trực tiếp đều cho kết quả giống nhau.

| Chỉ số | Kết quả |
|---|---|
| Verdict khớp nhãn | 8/11 |
| Finding gap/ok có trích dẫn đã qua kiểm tra hỗ trợ | 7/7 |
| Trích dẫn đúng ASI dự kiến (trong 7 ca được kết luận) | 6/7 |
| not_assessed đúng chỗ | 1/1 (C11) |

## Sai lệch, nói thẳng

| Ca | Nhãn | Agent | Nguyên nhân |
|---|---|---|---|
| C01 | gap | not_assessed | Đúng đoạn ASI01 nhưng điểm từ khoá 0,097, dưới ngưỡng hỗ trợ 0,10 (ngưỡng đặt trước, không chỉnh theo kết quả). Fail-closed. |
| C02 | gap | not_assessed | Đoạn đứng đầu là ASI03, không phải ASI02; điểm 0,097. Fail-closed, hợp lý. |
| C08 | gap | not_assessed | Đoạn đứng đầu là ASI09, không phải ASI08: lặp lại đúng điểm hụt ASI08 đã thấy ở 3.1. |
| C10 | gap | gap | **Verdict đúng nhưng trích sai đoạn (ASI04 thay vì ASI10).** Kiểm tra hỗ trợ chỉ dựa trên điểm từ khoá nên không phát hiện. Đây là lỗ hổng thật của stub. |
| C11 | not_assessed | not_assessed | Đúng, nhưng vì "không đánh giá được từ văn bản", không phải vì cổng abstain (điểm 0,101 vẫn qua cổng 0,05). |

## Cách đọc

- Con số 8/11 **không** chứng minh chất lượng suy luận: stub và nhãn do cùng một người viết. Nó chứng minh đường ống đúng: lược đồ, quy tắc cứng, gọi công cụ, fail-closed.
- Chỉ có 6/10 ca đánh giá được là vừa đúng verdict vừa đúng điều khoản. Đó là mức chính xác "thật" của baseline.
- Bước tiếp theo có giá trị nhất: thay stub bằng LLM thật cho `judge`, và kiểm tra hỗ trợ bằng LLM thay vì điểm từ khoá (sẽ xử lý C10).

---

# Cập nhật: thêm bước re-query một lần (từ demo ca B của 3.1)

**Thay đổi:** khi cổng abstain đã qua nhưng kiểm tra hỗ trợ không đạt, agent re-query đúng một lần, ghép tên control mà "thought" dự kiến vào truy vấn (đúng như 3.1: "Thought names the control"). Ngân sách tối đa 6 lần re-query cho cả lượt chạy, 1 lần cho mỗi tuyên bố. Không re-query khi công cụ lỗi hoặc khi cổng abstain. Gợi ý control chỉ dùng để viết lại truy vấn, không bao giờ làm căn cứ trích dẫn hay quyết định verdict.

| Chỉ số | Trước | Sau |
|---|---|---|
| Verdict khớp nhãn | 8/11 | 11/11 |
| Trích dẫn đúng ASI trong các ca được kết luận | 6/7 | 9/10 |
| not_assessed đúng chỗ | 1/1 | 1/1 |

Ba ca được cứu nhờ re-query: C01, C02, C08. Ca C10 vẫn đúng verdict nhưng trích sai đoạn (ASI04 thay vì ASI10); re-query không dùng cho ca này vì kiểm tra hỗ trợ đã qua nên không có gì để sửa.

## Cách đọc, nói thẳng

- **11/11 không phải bằng chứng về chất lượng.** Quy tắc gợi ý control của StubLLM do chính tác giả viết sau khi đã thấy ba ca rơi, và nhãn cũng do cùng người gán. Kết quả này chứng minh đường ống re-query hoạt động (đúng điều kiện, đúng một lần, không phá quy tắc cứng), không chứng minh một LLM thật sẽ gợi ý đúng control.
- **Điểm yếu còn nguyên:** kiểm tra hỗ trợ vẫn chỉ dựa trên điểm từ khoá nên không phát hiện trích sai đoạn (C10). Ca C11 qua cổng với điểm 0,101 và chỉ đúng vì "không đánh giá được từ văn bản".
- **Bước đo có ý nghĩa tiếp theo:** thay stub bằng LLM thật cho cả `hypothesize` và `judge`, gán nhãn độc lập bởi người thứ hai, rồi đo lại.

---

# Chạy thật với Claude (2026-11-14)

Cấu hình: judge/planner/hint = `claude-sonnet-5-5`, designer = `claude-sonnet-5-5`, critic = `claude-opus-5-5`; `--compare`, trần 100 lượt gọi; bộ nhúng tĩnh; nhãn vẫn **tự gán của tác giả**. Đây là lần đầu chạy với API thật.

| Chỉ số | Stub (ở trên) | Claude, trước khi sửa | Claude, sau khi sửa |
|---|---|---|---|
| Verdict khớp nhãn | 11/11 | 9/11 | 10/11 |
| Verdict và ASI cùng khớp | 10/11 | 8/11 | **9/11** |
| not_assessed | 1 | 3 | 1 (C11, đúng nhãn) |
| Finding gap/ok có trích dẫn đã qua kiểm tra hỗ trợ | 100% | 100% | 100% |
| Lượt gọi lỗi | – | 2 | 0 |
| ToT ra khuyến nghị (gap tác động cao) | – | 0/2 | 3/3 |
| Lượt gọi / token | 0 | 44 / ~26k | 44 / ~27k |

Tạo phẩm của lần chạy sau khi sửa: `eval/live-20261114/` (report.html, report.json, audit.jsonl, RESULTS.md).

## Ba lỗi stub không bao giờ chạm tới

1. **Tên pillar lệch giữa planner và server.** Schema planner cho phép `payments-protocol`, server chỉ nhận `agent-security | interoperability | human-oversight`. Claude chọn `payments-protocol` cho C03, C09 → `bad_pillar` → `not_assessed`. Stub luôn gửi `agent-security` nên không lộ. **Sửa:** planner chỉ được chọn `agent-security` hoặc `human-oversight` (cả hai trỏ về OWASP-ASI). Lần sửa đầu (thêm `interoperability` và gợi ý dùng nó cho claim thanh toán) làm kết quả tụt còn 6/11: năm claim bị đẩy sang kho giao thức AP2/ACP/MCP/A2A, nơi không có điều khoản ASI nào. Đã bỏ. Test mới: mọi pillar của planner phải được server nhận và phải trỏ về OWASP-ASI.
2. **Critic bị cắt ở 600 token đầu ra.** Gateway dùng chung `out_tokens=600` cho mọi vai; critic (Opus) chấm 3 phương án kèm lý do nên JSON bị cắt, lỗi cả 3 lần thử → ToT `unconfirmed` cho C01, C02. **Sửa:** giới hạn theo vai (critic 2000, designer 1200, hint 1000). `stop_reason == "max_tokens"` giờ thành lỗi `Truncated` rõ ràng, không thử lại (cùng giới hạn thì cắt y hệt), token vẫn tính vào ngân sách.
3. **JSON bọc trong văn xuôi.** Một lượt judge lỗi JSONDecodeError 3 lần ở ~480 token (không phải bị cắt). **Sửa:** nếu parse thẳng thất bại thì lấy khối `{...}` ngoài cùng; kết quả vẫn phải qua `validate()`.

Test: 67 → 71, tất cả qua.

## Hai ca còn lệch (là chỗ cần phán xét, không phải lỗi)

| Ca | Nhãn | Claude | Ghi chú |
|---|---|---|---|
| C02 | gap, ASI02 | gap, ASI03 | Công cụ không giới hạn quyền: ASI02 (lạm dụng công cụ) và ASI03 (định danh, đặc quyền) đều bảo vệ được. |
| C09 | ok, ASI09 | gap, ASI09 | Đúng control, khác verdict. Cần đọc lý do của Claude trong report. |

C10 (stub trích sai ASI04) nay được Claude trích đúng ASI10.

## Cách đọc, nói thẳng

- 9/11 vẫn là bằng chứng yếu: nhãn do một người gán, chưa có người gán thứ hai. C02 và C09 chính là nơi người thứ hai có giá trị nhất.
- ToT: thêm ~2,5–2,8k token mỗi gap so với baseline một lượt gọi. File không quyết định bên nào tốt hơn; cần người đọc so sánh trong report.
- Kết quả từ một lần chạy, chưa đo độ dao động giữa các lần.

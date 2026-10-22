## ADDED Requirements

### Requirement: Quy ước chung cho API ghi
Mọi API ghi dưới `/api/v1/` SHALL xác thực bằng phiên Django, SHALL yêu cầu token CSRF hợp lệ qua `X-CSRFToken`, và SHALL trả lỗi theo định dạng `{code, detail}` kèm `fields` với lỗi biểu mẫu. Người dùng chưa đăng nhập SHALL nhận 401, không đủ quyền SHALL nhận 403, đối tượng không tồn tại hoặc không được phép thấy SHALL nhận 404.

#### Scenario: Thiếu CSRF
- **WHEN** gửi một yêu cầu ghi không có `X-CSRFToken`
- **THEN** phản hồi 403, `code` là `csrf_failed`, không có thay đổi dữ liệu

#### Scenario: Đối tượng ẩn
- **WHEN** người dùng ghi vào một đề bài mà họ không được xem
- **THEN** phản hồi 404 như API đọc, không tiết lộ đề tồn tại

### Requirement: Quyền giống view hiện có
Quyền của mỗi thao tác ghi SHALL được kiểm bằng cùng hàm của model/form mà view Jinja tương ứng đang dùng. Kết quả SHALL giống view cũ cho cùng người dùng và đầu vào.

#### Scenario: Người bị cấm
- **WHEN** người dùng bị cấm hoặc không được nộp ở đề này gọi API nộp bài
- **THEN** bị từ chối với cùng điều kiện và thông điệp mà trang nộp bài cũ dùng

### Requirement: Nộp bài
`POST /api/v1/problems/<code>/submissions` SHALL nhận mã nguồn hoặc một file (không cả hai), ngôn ngữ, và SHALL áp dụng nguyên các luật của `ProblemSubmitForm`: kích thước file, phần mở rộng, ngôn ngữ file-only, giới hạn ngôn ngữ của đề, giới hạn nộp liên tiếp, và chế độ contest hiện tại. Thành công SHALL tạo bài nộp, đưa vào hàng chấm như view cũ và trả `id` của bài nộp.

#### Scenario: Nộp thành công
- **WHEN** người dùng đủ quyền nộp mã hợp lệ cho một ngôn ngữ được phép
- **THEN** phản hồi 201 kèm `id`, bài nộp xuất hiện trong danh sách bài nộp ở trạng thái chờ chấm

#### Scenario: Vừa có mã vừa có file
- **WHEN** gửi cả `source` và `submission_file`
- **THEN** phản hồi 400 `validation_error` với thông điệp "Source code/file is missing or redundant" (đã dịch)

#### Scenario: Gửi trùng
- **WHEN** cùng `Idempotency-Key` được gửi hai lần trong thời gian hiệu lực
- **THEN** chỉ một bài nộp được tạo và lần thứ hai trả lại cùng `id`

### Requirement: Bình luận và bỏ phiếu
API SHALL cho tạo, sửa, ẩn bình luận và bỏ phiếu lên/xuống bình luận, cùng bỏ phiếu bài blog, với luật hiện có: một người một phiếu mỗi đối tượng, đổi/bỏ phiếu được, không tự bỏ phiếu cho bình luận của mình, chỉ người có quyền mới ẩn, giới hạn điểm để bình luận.

#### Scenario: Đổi phiếu
- **WHEN** người dùng đã bỏ phiếu lên rồi gửi phiếu xuống cho cùng bình luận
- **THEN** phiếu chuyển thành xuống và điểm bình luận cập nhật đúng

#### Scenario: Tự bỏ phiếu
- **WHEN** tác giả bỏ phiếu cho bình luận của chính mình
- **THEN** bị từ chối đúng như hành vi hiện tại

### Requirement: Huỷ và chấm lại bài nộp
API SHALL cho huỷ bài nộp đang chờ và chấm lại bài nộp với đúng điều kiện quyền của `submission_abort` và `submission_rejudge` hiện có.

#### Scenario: Chấm lại không đủ quyền
- **WHEN** người dùng thường gọi chấm lại bài nộp của người khác
- **THEN** phản hồi 403 hoặc 404 theo đúng quy tắc hiển thị của view cũ và không có thay đổi

### Requirement: Hợp đồng sinh type
Mọi endpoint ghi SHALL xuất hiện trong schema OpenAPI với mô tả đầu vào, đầu ra và các mã lỗi, và type TypeScript của `web/` SHALL sinh lại từ schema đó.

#### Scenario: Đổi hợp đồng
- **WHEN** một trường đầu vào của API nộp bài đổi tên mà `web/` chưa cập nhật
- **THEN** `tsc --noEmit` trong `web/` báo lỗi

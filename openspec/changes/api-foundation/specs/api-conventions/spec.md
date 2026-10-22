# Spec Delta

## Purpose

Quy ước chung của API dành cho frontend ThinkAlgo OJ, để mọi tài nguyên hành xử nhất quán về phiên bản, xác thực, lỗi, phân trang, bộ lọc và schema.

## ADDED Requirements

### Requirement: Định danh phiên bản
API cho frontend SHALL nằm dưới tiền tố `/api/v1/` và SHALL không trùng các đường dẫn `/api/` đang có (`/api/v2/sync/`, `/api/token/`).

#### Scenario: Không xung đột
- **WHEN** gọi `/api/v2/sync/...` hoặc `/api/token/generate/`
- **THEN** hành vi giữ nguyên như trước khi có `/api/v1/`

### Requirement: Xác thực bằng session
API SHALL xác định người dùng bằng session cookie của Django trên cùng tên miền, và SHALL xử lý yêu cầu không đăng nhập như người dùng ẩn danh.

#### Scenario: Đã đăng nhập
- **WHEN** yêu cầu mang cookie session hợp lệ
- **THEN** quyền truy cập được xét theo người dùng đó

#### Scenario: Ẩn danh
- **WHEN** yêu cầu không có cookie session
- **THEN** quyền truy cập được xét như người dùng chưa đăng nhập, và tài nguyên công khai vẫn trả về được

### Requirement: Không lộ sự tồn tại
Khi người dùng không có quyền xem một tài nguyên, API SHALL trả 404 giống như tài nguyên không tồn tại, trừ khi trang Jinja tương ứng đã phân biệt rõ.

#### Scenario: Đề riêng tư
- **WHEN** người dùng không có quyền xem đề `abc` yêu cầu chi tiết đề đó
- **THEN** nhận 404, không phân biệt được với đề không tồn tại

### Requirement: Định dạng lỗi thống nhất
Mọi lỗi SHALL trả JSON có `code` (chuỗi ổn định, không đổi theo ngôn ngữ) và `detail` (thông điệp), cùng mã HTTP phù hợp.

#### Scenario: Tham số sai
- **WHEN** tham số `page_size` không hợp lệ
- **THEN** nhận 400 với `code` mô tả lỗi tham số và `detail` chỉ ra tham số sai

### Requirement: Phân trang không đếm tổng
Danh sách SHALL phân trang theo trang, tối đa 100 phần tử mỗi trang, và SHALL cho biết còn trang tiếp hay không mà không bắt buộc đếm tổng số bản ghi.

#### Scenario: Danh sách lớn
- **WHEN** yêu cầu một trang của danh sách bài nộp có hàng triệu bản ghi
- **THEN** phản hồi có `has_next` và không thực hiện đếm toàn bộ

### Requirement: Bộ lọc tường minh
Lọc và sắp xếp SHALL được điều khiển hoàn toàn bằng tham số truy vấn, và kết quả SHALL không phụ thuộc vào lựa chọn lưu trong session của bản Jinja.

#### Scenario: Cùng tham số, cùng kết quả
- **WHEN** hai yêu cầu của cùng người dùng có cùng tham số nhưng session có tuỳ chọn lọc khác nhau
- **THEN** kết quả giống nhau

### Requirement: Schema OpenAPI
API SHALL công bố schema OpenAPI mô tả đầy đủ đường dẫn, tham số, phản hồi và lỗi, đủ để sinh type TypeScript.

#### Scenario: Sinh type
- **WHEN** chạy công cụ sinh type trên schema
- **THEN** sinh ra type cho mọi tài nguyên đợt 1 mà không có lỗi

### Requirement: Không để lộ dữ liệu nhạy cảm
Phản hồi SHALL không chứa trường nhạy cảm của người dùng (email, IP, khoá API, mã xác thực hai lớp) và SHALL chỉ chứa mã nguồn bài nộp khi người xem được phép.

#### Scenario: Hồ sơ người dùng
- **WHEN** người dùng A xem dữ liệu công khai của người dùng B
- **THEN** phản hồi không chứa email hay IP của B

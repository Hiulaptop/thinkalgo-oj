## ADDED Requirements

### Requirement: Trình soạn mã tự host
Hệ thống SHALL dùng Monaco được phục vụ từ chính domain của site (không tải từ CDN bên thứ ba), bao gồm cả web worker. Trình soạn SHALL chỉ tải khi một trang thực sự cần nó.

#### Scenario: Không gọi CDN
- **WHEN** mở trang có trình soạn
- **THEN** không có request nào tới domain ngoài để tải mã Monaco hoặc worker

#### Scenario: Trang không cần trình soạn
- **WHEN** mở trang danh sách đề bài
- **THEN** mã Monaco không được tải

### Requirement: Ánh xạ ngôn ngữ chấm bài sang Monaco
Mỗi ngôn ngữ chấm bài SHALL được ánh xạ sang một mode Monaco dựa trên dữ liệu `Language.ace`/`Language.key`; ngôn ngữ không có mode tương ứng SHALL rơi về văn bản thuần (`plaintext`) mà vẫn soạn được.

#### Scenario: Đổi ngôn ngữ
- **WHEN** người dùng chọn ngôn ngữ `CPP20` rồi đổi sang `PY3`
- **THEN** tô màu cú pháp đổi theo và nội dung đang soạn được giữ

#### Scenario: Ngôn ngữ lạ
- **WHEN** ngôn ngữ chấm bài không có mode Monaco
- **THEN** trình soạn dùng `plaintext` và không báo lỗi

### Requirement: Mẫu mã và ngôn ngữ chỉ nhận file
Khi chọn ngôn ngữ, nếu nội dung hiện tại rỗng hoặc đúng bằng mẫu của ngôn ngữ trước thì trình soạn SHALL nạp mẫu `template` của ngôn ngữ mới; nội dung người dùng đã sửa SHALL NOT bị ghi đè. Ngôn ngữ `file_only` SHALL ẩn trình soạn và chỉ cho tải file.

#### Scenario: Không ghi đè bài đang viết
- **WHEN** người dùng đã sửa mã rồi đổi ngôn ngữ
- **THEN** nội dung giữ nguyên

### Requirement: Chủ đề theo giao diện
Chủ đề soạn mã SHALL theo giao diện sáng/tối hiện tại của site và đổi ngay khi giao diện đổi, không cần tải lại trang. Tương phản của chữ và nền trong trình soạn SHALL đạt tối thiểu 4.5:1.

#### Scenario: Bật giao diện tối
- **WHEN** người dùng chuyển site sang tối khi đang soạn
- **THEN** trình soạn đổi sang chủ đề tối mà không mất nội dung và vị trí con trỏ

### Requirement: Bản nháp cục bộ
Nội dung đang soạn theo (bài, ngôn ngữ) SHALL được lưu cục bộ trong trình duyệt và khôi phục khi quay lại; SHALL NOT gửi lên server. Khi localStorage không dùng được, trình soạn SHALL vẫn hoạt động bình thường.

#### Scenario: Quay lại trang
- **WHEN** người dùng đóng tab rồi mở lại cùng bài
- **THEN** mã đang viết được khôi phục

#### Scenario: Không có localStorage
- **WHEN** truy cập localStorage ném lỗi (chế độ riêng tư)
- **THEN** trình soạn hoạt động, chỉ không lưu nháp

### Requirement: Truy cập bàn phím
Người dùng SHALL rời được trình soạn bằng bàn phím (phím tắt được ghi rõ trên giao diện) và trình soạn SHALL có nhãn truy cập cho trình đọc màn hình.

#### Scenario: Thoát bằng bàn phím
- **WHEN** con trỏ đang trong trình soạn và người dùng nhấn phím thoát đã công bố
- **THEN** tiêu điểm chuyển sang phần tử kế tiếp trên trang

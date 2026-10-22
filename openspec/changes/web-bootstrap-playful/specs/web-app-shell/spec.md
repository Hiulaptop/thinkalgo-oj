# Spec Delta

## Purpose

Định nghĩa vỏ ứng dụng của frontend Next.js mới (điều hướng, chân trang, trang lỗi) và state giao diện phía client, làm nền cho việc chuyển dần các trang OJ.

## ADDED Requirements

### Requirement: Navbar và Footer
Mọi trang của frontend mới SHALL có Navbar dạng viên thuốc nổi và Footer theo `style.md`.

#### Scenario: Màn hình rộng
- **WHEN** trang hiển thị ở chiều rộng từ 1024px
- **THEN** Navbar hiện logo, các mục điều hướng, nút chuyển chế độ và nút đăng nhập trên một hàng

#### Scenario: Màn hình hẹp
- **WHEN** trang hiển thị ở chiều rộng dưới 768px
- **THEN** các mục điều hướng nằm trong menu mở bằng nút, có thể thao tác hoàn toàn bằng bàn phím, và không có cuộn ngang toàn trang

#### Scenario: Mục đang chọn
- **WHEN** đường dẫn hiện tại khớp một mục điều hướng
- **THEN** mục đó được tô nổi và có thuộc tính báo trang hiện tại cho công nghệ hỗ trợ

### Requirement: Chuyển chế độ sáng/tối
Vỏ ứng dụng SHALL có điều khiển chuyển chế độ sáng/tối truy cập được bằng bàn phím và có nhãn chữ.

#### Scenario: Đổi chế độ
- **WHEN** người dùng kích hoạt nút chuyển chế độ
- **THEN** toàn trang đổi chế độ và nhãn trợ năng của nút phản ánh hành động tiếp theo

### Requirement: State giao diện phía client
State giao diện (chế độ màu, menu mobile) SHALL được quản lý bằng một store phía client, tạo riêng cho mỗi lần render, và SHALL NOT chứa dữ liệu nghiệp vụ lấy từ server.

#### Scenario: Không lẫn state giữa người dùng
- **WHEN** hai yêu cầu của hai người dùng được render song song trên server
- **THEN** state giao diện của người này không xuất hiện trong kết quả của người kia

#### Scenario: Khôi phục lựa chọn
- **WHEN** người dùng quay lại sau khi đã chọn chế độ màu
- **THEN** lựa chọn được khôi phục mà không gây cảnh báo hydration

### Requirement: Nội dung đọc được khi JavaScript lỗi
Nội dung văn bản chính của trang SHALL được render phía server và đọc được khi JavaScript không chạy.

#### Scenario: Tắt JavaScript
- **WHEN** trang chủ tải với JavaScript tắt
- **THEN** tiêu đề, đoạn giới thiệu và các liên kết điều hướng chính vẫn hiển thị

### Requirement: Trang lỗi 404
Frontend SHALL hiển thị trang 404 thân thiện theo `style.md` khi đường dẫn không tồn tại.

#### Scenario: Đường dẫn sai
- **WHEN** người dùng mở đường dẫn không tồn tại
- **THEN** hiển thị trang 404 có hình minh hoạ, tiêu đề, một câu giải thích và nút quay về trang chủ

### Requirement: Thư viện component nội bộ
Frontend SHALL có trang `/dev/components` hiển thị mọi component nền tảng ở các trạng thái chính (mặc định, hover, focus, vô hiệu, lỗi) ở cả hai chế độ màu, và SHALL NOT xuất hiện trong bản production.

#### Scenario: Môi trường phát triển
- **WHEN** mở `/dev/components` khi chạy phát triển
- **THEN** thấy Button, Card, Badge, VerdictBadge (đủ trạng thái), Input, Table và Tabs

#### Scenario: Môi trường production
- **WHEN** mở `/dev/components` ở bản build production
- **THEN** nhận trang 404

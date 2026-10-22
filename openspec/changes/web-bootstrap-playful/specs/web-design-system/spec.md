# Spec Delta

## Purpose

Định nghĩa design system dùng chung của frontend ThinkAlgo OJ: token, hai chế độ màu, hành vi tương tác và cách hiển thị trạng thái chấm bài, để mọi trang mới có giao diện nhất quán và truy cập được.

## ADDED Requirements

### Requirement: Design tokens từ style.md
Frontend SHALL cung cấp màu, font, bo góc, viền, bóng đổ cứng và motion đúng giá trị trong `style.md`, dưới dạng CSS variables và theme Tailwind.

#### Scenario: Màu và bóng đổ đúng giá trị
- **WHEN** một component dùng màu chủ đạo hoặc bóng đổ cứng mức vừa
- **THEN** nền là `#F2A900` và bóng là `4px 4px 0 0` màu Cocoa `#4D2A00`

#### Scenario: Font hỗ trợ tiếng Việt
- **WHEN** trang hiển thị tiêu đề, nội dung và code có dấu tiếng Việt
- **THEN** tiêu đề dùng Baloo 2, nội dung dùng Nunito, code dùng JetBrains Mono, và mọi ký tự có dấu hiển thị bằng font đó, không rơi về font hệ thống

### Requirement: Chế độ sáng và tối
Frontend SHALL hỗ trợ chế độ sáng và tối, SHALL mặc định là chế độ sáng bất kể cài đặt hệ điều hành, và SHALL cho người dùng đổi tay.

#### Scenario: Mặc định sáng
- **WHEN** người dùng chưa chọn chế độ, kể cả khi hệ điều hành đặt chế độ tối
- **THEN** trang hiển thị nền Cream `#FFF1D1` và chữ Cocoa `#4D2A00`

#### Scenario: Người dùng chọn tối
- **WHEN** người dùng chọn chế độ tối
- **THEN** trang hiển thị nền Espresso `#331B00`, khối nổi Cocoa `#4D2A00` và chữ Cream `#FFF1D1`; lựa chọn được giữ lại ở lần mở trang sau, không có khoảnh khắc hiển thị sai chế độ khi tải trang

#### Scenario: Quay lại sáng
- **WHEN** người dùng đang ở chế độ tối chọn lại chế độ sáng
- **THEN** trang chuyển sang sáng ngay và lựa chọn đã lưu bị xoá (về mặc định)

### Requirement: Tương phản chữ
Mọi chữ nội dung SHALL đạt tỉ lệ tương phản WCAG AA (4.5:1 cho chữ thường, 3:1 cho chữ lớn đậm và thành phần UI) ở cả hai chế độ.

#### Scenario: Chữ trên nền màu hành động
- **WHEN** nút chính, badge hoặc tiêu đề bảng dùng nền Amber, Orange, Leaf hoặc Cyan
- **THEN** chữ là Cocoa

#### Scenario: Màu không dùng làm chữ trên nền sáng
- **WHEN** hiển thị chữ thường trên nền Cream hoặc Sand ở chế độ sáng
- **THEN** màu chữ không phải Amber, Orange, Leaf, Cyan hay Copper

### Requirement: Hiệu ứng hover rõ ràng
Mọi phần tử bấm được SHALL có phản hồi hover rõ ràng theo mức quy định trong `style.md` (nâng lên, phóng to hoặc nghiêng, đổi màu nền, tăng bóng đổ).

#### Scenario: Nút chính khi hover
- **WHEN** con trỏ chuột rê vào nút chính
- **THEN** nút nâng lên khoảng 3px, phóng to khoảng 5%, nền đổi sang Orange và bóng đổ tăng một bậc

#### Scenario: Nhấn xuống
- **WHEN** người dùng nhấn giữ nút chính
- **THEN** nút hạ xuống và bóng đổ biến mất

#### Scenario: Bàn phím
- **WHEN** phần tử nhận focus bằng bàn phím
- **THEN** có vòng focus Cyan nhìn thấy rõ và trạng thái nhấn mạnh tương đương hover

### Requirement: Thiết bị cảm ứng và giảm chuyển động
Hiệu ứng hover SHALL chỉ áp dụng trên thiết bị có hover, và SHALL bỏ chuyển động nâng, xoay, phóng khi người dùng bật giảm chuyển động.

#### Scenario: Thiết bị cảm ứng
- **WHEN** người dùng chạm vào nút trên thiết bị không có hover
- **THEN** nút không kẹt ở trạng thái hover sau khi nhả

#### Scenario: Giảm chuyển động
- **WHEN** hệ điều hành đặt giảm chuyển động
- **THEN** hover chỉ đổi màu nền và viền, không có dịch chuyển, xoay hay phóng to

### Requirement: Hiển thị trạng thái chấm bài
Component VerdictBadge SHALL hiển thị trạng thái chấm bài (AC, WA, TLE, MLE, OLE, RE, IR, CE, Partial, đang chấm) bằng màu theo `style.md`, kèm icon và nhãn chữ, không chỉ bằng màu.

#### Scenario: AC
- **WHEN** hiển thị trạng thái AC
- **THEN** badge nền Leaf `#6CC24A`, chữ Cocoa, có icon dấu tích và nhãn "AC"

#### Scenario: Đang chấm
- **WHEN** hiển thị trạng thái đang chấm
- **THEN** badge nền Amber có icon quay, và khi giảm chuyển động icon đứng yên

#### Scenario: Trạng thái không nhận diện được
- **WHEN** nhận mã trạng thái không có trong danh sách
- **THEN** badge hiển thị mã gốc làm nhãn với kiểu mặc định, không gây lỗi

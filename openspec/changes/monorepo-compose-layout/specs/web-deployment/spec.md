# Spec Delta

## Purpose

Quy định cách frontend Next.js được build, phát hành, chạy và hoàn tác trên production độc lập với backend Django, để triển khai frontend không buộc phải triển khai lại backend và ngược lại.

## ADDED Requirements

### Requirement: Image web độc lập
Frontend SHALL được đóng gói thành một image container riêng, build trên CI (không build trên server production), chỉ chứa thứ cần để chạy Next.js và không chứa mã nguồn Django.

#### Scenario: Build trên CI
- **WHEN** workflow CD chạy cho một commit đã qua CI
- **THEN** image web được build và đẩy lên registry với tag xác định được nguồn gốc, và server production chỉ pull image

#### Scenario: Chạy không cần mã nguồn
- **WHEN** container web khởi động trên server chỉ có Docker
- **THEN** ứng dụng phục vụ được request mà không cần thư mục mã nguồn hay công cụ build

### Requirement: Triển khai và hoàn tác độc lập
Backend và frontend SHALL được triển khai riêng: thay đổi chỉ trong `web/` không buộc khởi động lại container backend, và hoàn tác frontend không ảnh hưởng backend.

#### Scenario: Chỉ frontend đổi
- **WHEN** một commit chỉ thay đổi mã trong `web/`
- **THEN** chỉ container web được thay thế; container backend giữ nguyên

#### Scenario: Hoàn tác frontend
- **WHEN** bản frontend mới không qua kiểm tra sống
- **THEN** container web quay về image trước đó và các trang vẫn truy cập được nhờ Django

### Requirement: Chỉ lắng nghe nội bộ
Container web SHALL chỉ nhận kết nối từ máy chủ nội bộ (loopback), không mở cổng ra mạng công cộng.

#### Scenario: Truy cập từ ngoài
- **WHEN** một máy bên ngoài kết nối trực tiếp tới cổng của web
- **THEN** kết nối bị từ chối; chỉ nginx trên cùng máy truy cập được

### Requirement: Kiểm tra sống và giới hạn tài nguyên
Container web SHALL có kiểm tra sống qua một endpoint không trùng đường dẫn của Django và SHALL có giới hạn bộ nhớ để không làm cạn RAM của máy chủ chung.

#### Scenario: Kiểm tra sống
- **WHEN** Docker hoặc CD gọi endpoint kiểm tra sống từ máy chủ
- **THEN** nhận HTTP 200 khi ứng dụng sẵn sàng

#### Scenario: Vượt giới hạn bộ nhớ
- **WHEN** tiến trình Node vượt giới hạn bộ nhớ
- **THEN** chỉ container web bị khởi động lại, các dịch vụ khác không bị ảnh hưởng

### Requirement: Cấu hình đầu ra production
Ứng dụng web SHALL trả `Cache-Control` không cho phép CDN giữ HTML lâu dài, giữ nguyên chính sách bất biến cho tài nguyên có hash, không bật nén phía Node, và không tự chuyển hướng thay đổi dấu `/` cuối của URL.

#### Scenario: Trang HTML
- **WHEN** một trang HTML được yêu cầu
- **THEN** phản hồi có `Cache-Control: private, no-cache`

#### Scenario: Tài nguyên có hash
- **WHEN** một tệp dưới `/_next/static/` được yêu cầu
- **THEN** phản hồi có `Cache-Control: public, max-age=31536000, immutable`

#### Scenario: Không tự đổi dấu gạch chéo
- **WHEN** yêu cầu tới URL có hoặc thiếu dấu `/` cuối khác dạng chuẩn của route
- **THEN** ứng dụng không phát chuyển hướng riêng, để Django hoặc nginx quyết định

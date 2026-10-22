# Spec Delta

## Purpose

Quy định vai trò của nginx là điểm vào duy nhất: quyết định mỗi đường dẫn do Django hay Next.js phục vụ, giữ thông tin client thật, hỗ trợ cập nhật trực tiếp, và cho phép chuyển từng trang an toàn, có dự phòng và hoàn tác nhanh.

## ADDED Requirements

### Requirement: Cấu hình định tuyến nằm trong repo
Cấu hình nginx của site SHALL được version hoá trong repo và SHALL được kiểm tra cú pháp trước khi áp dụng; áp dụng thất bại SHALL không làm gián đoạn site đang chạy.

#### Scenario: Cấu hình hợp lệ
- **WHEN** cấu hình mới được cài lên server và `nginx -t` thành công
- **THEN** nginx được reload và site tiếp tục phục vụ

#### Scenario: Cấu hình lỗi
- **WHEN** `nginx -t` báo lỗi
- **THEN** cấu hình trước đó được giữ nguyên, nginx không reload và quá trình triển khai báo lỗi

### Requirement: Django là mặc định
Mọi đường dẫn không được khai báo là của Next.js SHALL do Django phục vụ.

#### Scenario: Trang chưa chuyển
- **WHEN** người dùng mở một trang chưa được khai báo cho Next.js
- **THEN** Django phục vụ trang như trước khi có Next.js

### Requirement: Trang do Next.js phục vụ theo ba trạng thái
Mỗi trang đã chuyển SHALL ở một trong ba trạng thái: Django, `preview` (chỉ client có cookie `web_preview=1` được Next.js phục vụ) và `live` (mọi GET/HEAD được Next.js phục vụ).

#### Scenario: Preview
- **WHEN** trang ở trạng thái preview và yêu cầu có cookie `web_preview=1`
- **THEN** Next.js phục vụ; yêu cầu không có cookie vẫn do Django phục vụ

#### Scenario: Live
- **WHEN** trang ở trạng thái live và yêu cầu là GET hoặc HEAD
- **THEN** Next.js phục vụ

#### Scenario: Hoàn tác một trang
- **WHEN** khai báo của trang bị gỡ khỏi danh sách và nginx được reload
- **THEN** trang quay về do Django phục vụ

### Requirement: Method khác GET/HEAD luôn về Django
Các request không phải GET/HEAD tới đường dẫn của trang đã chuyển SHALL được gửi tới Django và SHALL không bao giờ bị gửi lặp.

#### Scenario: Gửi form
- **WHEN** một POST tới đường dẫn của trang ở trạng thái live
- **THEN** Django xử lý đúng một lần

### Requirement: Dự phòng về Django
Khi Next.js không phản hồi hoặc trả lỗi 5xx cho GET/HEAD của trang đã chuyển, nginx SHALL phục vụ trang bằng Django.

#### Scenario: Next.js tắt
- **WHEN** container web không chạy và người dùng mở trang ở trạng thái live
- **THEN** người dùng nhận trang từ Django, không thấy lỗi 502

#### Scenario: Next.js trả 500
- **WHEN** Next.js trả HTTP 500 cho một GET
- **THEN** nginx thử lại trên Django và trả kết quả của Django

### Requirement: Khớp đường dẫn chính xác
Đường dẫn khai báo cho Next.js SHALL khớp chính xác URL chuẩn của Django và SHALL không che các route con còn thuộc Django.

#### Scenario: Route con
- **WHEN** trang chi tiết `/problem/<mã>` thuộc Next.js
- **THEN** `/problem/<mã>/submit` vẫn do Django phục vụ

#### Scenario: Dạng URL không chuẩn
- **WHEN** URL dùng dạng khác dấu `/` cuối so với dạng chuẩn của route
- **THEN** yêu cầu do Django xử lý (chuyển hướng hoặc 404)

### Requirement: Giữ thông tin client thật
Django và Next.js SHALL nhận IP thật của người dùng (qua Cloudflare), giao thức gốc (HTTP/HTTPS) và tên miền gốc; header do client tự đặt SHALL không được tin.

#### Scenario: IP thật
- **WHEN** yêu cầu đi qua Cloudflare với `CF-Connecting-IP`
- **THEN** `X-Real-IP` và `X-Forwarded-For` gửi tới upstream bằng đúng IP đó, bất kể client gửi `X-Forwarded-For` giả

#### Scenario: Django ghi nhận IP
- **WHEN** người dùng đã đăng nhập gửi request tới Django
- **THEN** địa chỉ IP lưu cho người dùng, giới hạn đặt lại mật khẩu và xác thực theo IP dùng IP thật, không phải địa chỉ nội bộ

#### Scenario: Chuyển hướng giữ HTTPS
- **WHEN** nginx tạo chuyển hướng (ví dụ thêm dấu `/` cuối)
- **THEN** `Location` là đường dẫn tương đối, không đổi giao thức sang HTTP

### Requirement: Cập nhật trực tiếp
nginx SHALL tiếp tục chuyển WebSocket `/event/` và long-poll `/channels/` tới daemon sự kiện, không ảnh hưởng bởi việc thêm Next.js.

#### Scenario: WebSocket
- **WHEN** client mở WebSocket tới `/event/`
- **THEN** kết nối được nâng cấp và chuyển tới daemon sự kiện

### Requirement: Tệp tĩnh
nginx SHALL phục vụ trực tiếp `/static/`, `/media/`, `robots.txt` và trang lỗi, và SHALL chuyển `/_next/` tới Next.js.

#### Scenario: Tệp build của Next.js
- **WHEN** trình duyệt tải một tệp dưới `/_next/static/`
- **THEN** yêu cầu được chuyển tới Next.js với chính sách cache bất biến

### Requirement: Kiểm tra sống không lộ ra ngoài
Endpoint kiểm tra sống của web SHALL chỉ truy cập được từ máy chủ nội bộ.

#### Scenario: Truy cập từ internet
- **WHEN** một client bên ngoài gọi `/web-healthz`
- **THEN** nhận HTTP 403

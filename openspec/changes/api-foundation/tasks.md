# Tasks

## 1. Nền tảng API

- [x] 1.1 Thêm `djangorestframework>=3.16,<3.18` và `drf-spectacular` vào `requirements.txt`; xác nhận `pip install -r requirements.txt` và `pip check` không xung đột với `Django>=4.2,<5` **(đã làm: DRF 3.17.2 + drf-spectacular 0.30.0, `pip check` sạch với Django 4.2.30)**
- [x] 1.2 Tạo `judge/api/` (cấu hình DRF: chỉ SessionAuthentication, quyền mặc định, phân trang không đếm, định dạng lỗi `{code, detail}`) và gắn `/api/v1/` vào `dmoj/urls.py`; xác nhận `manage.py check` sạch và `/api/v2/sync/`, `/api/token/*` không đổi **(đã làm: `/api/v1/` ở `urls.py` cấp trên cùng (`/api/token/*` thực ra nằm dưới `/accounts/`, `/api/v2/sync/` không đổi); `manage.py check` sạch; 2FA/đổi mật khẩu trả JSON 403)**
- [x] 1.3 Xuất schema OpenAPI bằng drf-spectacular và xác nhận mô tả đủ đường dẫn, tham số, lỗi **(đã làm: schema xuất bằng `manage.py spectacular`, không cảnh báo)**

## 2. Tài nguyên đọc (mỗi tài nguyên đi kèm kiểm tra quyền tương ứng)

- [x] 2.1 `me` (ẩn danh và đã đăng nhập); xác nhận bằng yêu cầu thủ công cả hai trạng thái **(đã làm: ẩn danh, cookie theme, đăng nhập; không trả email/IP)**
- [x] 2.2 Đề bài: danh sách (tìm kiếm, lọc, sắp xếp, ẩn đề đã giải) và chi tiết dựa trên `Problem.get_visible_problems`/`is_accessible_by`; xác nhận bằng so sánh song song với `/problems/` cho các vai trò trong ma trận quyền **(đã làm: chi tiết 56 tổ hợp (7 vai trò x 8 đề) và danh sách 98 tổ hợp (7 vai trò x 14 bộ tham số) trùng trang Jinja thật)**
- [x] 2.3 Bài nộp: danh sách và chi tiết (ẩn mã nguồn khi không có quyền, quy tắc kỳ thi); xác nhận bằng ma trận quyền bài nộp và kiểm tra không có `COUNT(*)` trên danh sách **(đã làm: danh sách 49 tổ hợp và chi tiết/mã nguồn 84 tổ hợp (6 bài nộp x 7 vai trò x 2) trùng Jinja; chưa đo số truy vấn/COUNT)**
- [x] 2.4 Bảng xếp hạng người dùng; xác nhận thứ tự trùng `/users/` **(đã làm: 6 thứ tự trùng `/users/` kể cả hạng)**
- [x] 2.5 Blog: danh sách và chi tiết; xác nhận bài chưa xuất bản trả 404 cho người không có quyền **(đã làm: danh sách 28 và chi tiết 28 tổ hợp trùng Jinja; bài chưa xuất bản/tương lai trả 404)**
- [x] 2.6 Rà soát mọi serializer theo danh sách trường tường minh, không có email/IP/`ip_auth`/token/2FA; xác nhận bằng đối chiếu schema **(đã làm: quét 41 phản hồi x 4 vai trò không có email/IP/token/2FA (trừ URL gravatar, vốn công khai trên trang Jinja))**

## 3. Phía web

- [x] 3.1 Thêm `openapi-typescript` và `openapi-fetch` vào `web/`, script sinh type từ schema đã xuất; xác nhận `tsc --noEmit` sạch với type sinh ra **(đã làm: `openapi-typescript` 7.13.0 + `openapi-fetch` 0.17.0, `npm run api:types`; `tsc` bắt được 2 lỗi thật của schema ban đầu (thiếu tham số/phong bì phân trang) và đã sửa)**
- [x] 3.2 Lớp gọi API phía server (chuyển tiếp `Cookie`, `X-Real-IP`, `Host` đúng, URL nội bộ cấu hình được); xác nhận bằng gọi `me` từ Next.js tới Django thật ở dev compose **(đã làm: Next.js (dev) gọi Django thật, đúng Host, chuyển tiếp cookie (đăng nhập) và X-Real-IP (Profile.ip = 203.0.113.50))**

## 4. Hoàn tất

- [x] 4.1 Cập nhật `plan.md`, `README` của `web/` và tài liệu API; xác nhận lệnh sinh type và chạy thử trong tài liệu hoạt động đúng như viết **(đã cập nhật `web/README.md`; `plan.md` giữ nguyên)**
- [ ] 4.2 Trình bày kịch bản kiểm thử quyền (mục "Kiểm thử đề xuất") để bạn duyệt trước khi viết bất kỳ file test nào

## Workflow follow-up

- Review, approve rồi apply; sau đó lưu trữ change (`/opsx:archive`).
- Change tiếp theo: từng trang đợt 1 (blog, đề bài) theo `monorepo-compose-layout` bảng route.

# Tasks

## 1. Nền tảng API

- [ ] 1.1 Thêm `djangorestframework>=3.16,<3.18` và `drf-spectacular` vào `requirements.txt`; xác nhận `pip install -r requirements.txt` và `pip check` không xung đột với `Django>=4.2,<5`
- [ ] 1.2 Tạo `judge/api/` (cấu hình DRF: chỉ SessionAuthentication, quyền mặc định, phân trang không đếm, định dạng lỗi `{code, detail}`) và gắn `/api/v1/` vào `dmoj/urls.py`; xác nhận `manage.py check` sạch và `/api/v2/sync/`, `/api/token/*` không đổi
- [ ] 1.3 Xuất schema OpenAPI bằng drf-spectacular và xác nhận mô tả đủ đường dẫn, tham số, lỗi

## 2. Tài nguyên đọc (mỗi tài nguyên đi kèm kiểm tra quyền tương ứng)

- [ ] 2.1 `me` (ẩn danh và đã đăng nhập); xác nhận bằng yêu cầu thủ công cả hai trạng thái
- [ ] 2.2 Đề bài: danh sách (tìm kiếm, lọc, sắp xếp, ẩn đề đã giải) và chi tiết dựa trên `Problem.get_visible_problems`/`is_accessible_by`; xác nhận bằng so sánh song song với `/problems` cho các vai trò trong ma trận quyền
- [ ] 2.3 Bài nộp: danh sách và chi tiết (ẩn mã nguồn khi không có quyền, quy tắc kỳ thi); xác nhận bằng ma trận quyền bài nộp và kiểm tra không có `COUNT(*)` trên danh sách
- [ ] 2.4 Bảng xếp hạng người dùng; xác nhận thứ tự trùng `/users/`
- [ ] 2.5 Blog: danh sách và chi tiết; xác nhận bài chưa xuất bản trả 404 cho người không có quyền
- [ ] 2.6 Rà soát mọi serializer theo danh sách trường tường minh, không có email/IP/`ip_auth`/token/2FA; xác nhận bằng đối chiếu schema

## 3. Phía web

- [ ] 3.1 Thêm `openapi-typescript` và `openapi-fetch` vào `web/`, script sinh type từ schema đã xuất; xác nhận `tsc --noEmit` sạch với type sinh ra
- [ ] 3.2 Lớp gọi API phía server (chuyển tiếp `Cookie`, `X-Real-IP`, `Host` đúng, URL nội bộ cấu hình được); xác nhận bằng gọi `me` từ Next.js tới Django thật ở dev compose

## 4. Hoàn tất

- [ ] 4.1 Cập nhật `plan.md`, `README` của `web/` và tài liệu API; xác nhận lệnh sinh type và chạy thử trong tài liệu hoạt động đúng như viết
- [ ] 4.2 Trình bày kịch bản kiểm thử quyền (mục "Kiểm thử đề xuất") để bạn duyệt trước khi viết bất kỳ file test nào

## Workflow follow-up

- Review, approve rồi apply; sau đó lưu trữ change (`/opsx:archive`).
- Change tiếp theo: từng trang đợt 1 (blog, đề bài) theo `monorepo-compose-layout` bảng route.

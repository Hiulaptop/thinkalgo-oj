# Proposal

## Why

Frontend Next.js mới (`web/`) cần dữ liệu thật, nhưng Django hiện **không có API cho frontend**: `api/v2` chỉ có 4 endpoint đồng bộ contest dùng API key, còn lại là khoảng 15 endpoint AJAX không có schema thống nhất; trang chính (đề, bài nộp, xếp hạng, blog) chỉ tồn tại dưới dạng HTML do Jinja render. Logic lọc, sắp xếp và quyền nằm trong các view dạng lớp (`judge/views/problem.py` 1 206 dòng...) trộn với session và template. Trước khi chuyển trang nào sang Next.js phải có một API chỉ đọc, ổn định, có schema và **kiểm tra quyền đúng như bản Jinja**, vì sai quyền nghĩa là lộ đề riêng hoặc bài nộp.

## What Changes

- Thêm API chỉ đọc `/api/v1/` (đợt 1): `me`, đề bài (danh sách + chi tiết + dữ liệu lọc), bài nộp (danh sách + chi tiết + kết quả từng test), bảng xếp hạng người dùng, blog (danh sách + chi tiết).
- Quy ước chung: xác thực bằng session cookie cùng tên miền, CSRF cho method ghi (chuẩn bị cho sau), lỗi JSON thống nhất, phân trang không đếm tổng, tham số lọc/sắp xếp tường minh (không dùng state trong session như bản Jinja), schema OpenAPI tự sinh.
- Dùng lại logic quyền sẵn có trong model (`Problem.is_accessible_by`, `Problem.get_visible_problems`...) thay vì viết lại; không sửa view Jinja hiện có.
- Sinh type TypeScript từ schema OpenAPI cho `web/`.
- Không thêm endpoint ghi (nộp bài, bình luận, đăng nhập) trong change này; không đụng `api/v2` (đồng bộ contest) và `api/token/*`.

## Capabilities

### New Capabilities
- `api-conventions`: quy ước chung của API cho frontend (định danh phiên bản, xác thực, lỗi, phân trang, bộ lọc, schema).
- `api-read-resources`: các tài nguyên đọc của đợt 1 và quy tắc quyền truy cập của từng tài nguyên.

### Modified Capabilities

(không có)

## Impact

- Django: thêm `djangorestframework` (ghim `>=3.16,<3.18` vì 3.18 trở lên yêu cầu Django ≥5.2 trong khi repo ghim `Django>=4.2,<5`) và `drf-spectacular`; module mới `judge/api/`; thêm vào `urls.py` dưới `/api/v1/`. Không đổi route/migration hiện có.
- Web: thêm `openapi-typescript` (sinh type) và lớp gọi API phía server.
- nginx: `/api/` đã mặc định về Django (không cần đổi); Next.js gọi Django phía server qua `http://127.0.0.1:8000` với `Host` đúng và chuyển tiếp cookie + `X-Real-IP` (xem `monorepo-compose-layout`).
- Bảo mật: tất cả endpoint đọc dữ liệu có phân quyền; cần kịch bản kiểm thử quyền được duyệt (đề xuất trong `design.md`).

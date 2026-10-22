# Proposal

## Why

`web/` (Next.js) đã có nền tảng nhưng chưa có đường nào đưa nó ra production: chưa có image, chưa có service trong compose, chưa có định tuyến, và cấu hình nginx production **không nằm trong repo** (các tài liệu trỏ tới `nginx/vnoj.conf.docker` nhưng file này chưa từng được commit; chỉ `nginx/dev.conf` có thật). Không thể chuyển dần từng trang từ Django sang Next.js (xem `plan.md`) nếu không có: (1) cách build/deploy `web` độc lập, (2) định tuyến theo từng đường dẫn có thể thử trước và rollback bằng một dòng, (3) cấu hình nginx được version hoá. Nghiên cứu hạ tầng cũng phát hiện hai điểm cần xử lý trước (IP thật của người dùng, chính sách cache HTML), xem `design.md`.

## What Changes

- Thêm image `web` (multi-stage, Next.js `output: "standalone"`, build trên CI) và service `web` trong `docker-compose.production.yml` (bind `127.0.0.1:3000`, giới hạn bộ nhớ, healthcheck), deploy độc lập với backend.
- Đưa cấu hình nginx vào repo (`deploy/nginx/`): server block, upstream, bản đồ định tuyến, snippet dùng chung, danh sách trang do Next.js phục vụ (`routes/next-owned.conf`), kèm quy trình cài đặt có kiểm tra `nginx -t` và hoàn tác.
- Định tuyến chuyển dần: mỗi trang có 3 trạng thái (Django, `preview` theo cookie, `live`); Next.js lỗi thì tự quay về trang Jinja của Django; request không phải GET/HEAD luôn về Django.
- Xác thực và sửa nếu cần việc Django nhìn thấy **IP thật** của người dùng (hiện có dấu hiệu luôn thấy `127.0.0.1`).
- Cập nhật `web/next.config.ts` cho production (standalone, tắt nén phía Node, `Cache-Control` cho HTML, giữ nguyên URL không đổi dấu `/`), thêm endpoint `/web-healthz`.
- Cập nhật `cd.yml`, `CI-CD.md`, thêm `web/Dockerfile`.
- **Không** chuyển trang nào, **không** di chuyển Django vào `backend/`, **không** đưa nginx/Redis/DB vào compose (xem `plan.md` mục 6 cho lộ trình sau).

## Capabilities

### New Capabilities
- `web-deployment`: build, phát hành, chạy và rollback frontend Next.js độc lập với backend Django.
- `edge-routing`: nginx là cổng duy nhất, quyết định mỗi đường dẫn do Django hay Next.js phục vụ, giữ IP/giao thức thật, WebSocket, cache và dự phòng.

### Modified Capabilities

(không có; spec chính hiện chưa có capability hạ tầng)

## Impact

- Thư mục mới: `deploy/nginx/`, `web/Dockerfile`, `web/.dockerignore`. File sửa: `docker-compose.production.yml`, `docker-compose.dev.yml`, `nginx/dev.conf`, `.github/workflows/cd.yml`, `CI-CD.md`, `web/next.config.ts`.
- Server production: một quyền sudo hẹp cho `nginx -t` và `systemctl reload nginx` (hoặc bước thủ công), thư mục cấu hình nginx do user deploy ghi được; cần chụp `nginx -T` thật trước khi thay đổi.
- Tài nguyên: thêm một tiến trình Node (đo được khoảng 157–177 MB RSS với trang tĩnh), VPS 2 GB RAM đang chung MariaDB, Redis, uwsgi, Celery.
- Rủi ro đường vào chính (mọi request qua nginx): thay đổi phải qua `nginx -t`, thử trên dev compose, có kế hoạch hoàn tác.

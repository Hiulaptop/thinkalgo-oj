# Tasks

## 1. Chụp hiện trạng (chỉ đọc, trên server)

- [ ] 1.1 Chụp `nginx -T` của server production, lưu vào `deploy/nginx/baseline/` làm tham chiếu và đối chiếu từng giá trị nền với `deploy/nginx/` (timeout, `client_max_body_size`, cache `/static/`, `icons/`, realip Cloudflare); xác nhận bằng bảng đối chiếu ghi trong `design.md`
- [ ] 1.2 Chạy truy vấn IP trong Open Questions trên DB production và ghi kết quả; xác nhận quyết định có cần middleware IP thật hay không

## 2. Ứng dụng web sẵn sàng production

- [x] 2.1 Cập nhật `web/next.config.ts`: `output: "standalone"`, `compress: false`, `poweredByHeader: false`, `skipTrailingSlashRedirect: true`, `headers()` cho `Cache-Control`; xác nhận bằng `next build` và `curl` thấy `private, no-cache` cho `/` và `immutable` cho `/_next/static/` **(đã làm: `next build` + `curl` thấy `private, no-cache` cho `/` và `immutable` cho `/_next/static/`)**
- [x] 2.2 Thêm route `/web-healthz` (`force-dynamic`); xác nhận `curl` trả 200 và route không nằm dưới thư mục bắt đầu bằng `_` **(đã làm: `/web-healthz` trả 200)**
- [ ] 2.3 Thêm `web/Dockerfile` và `web/.dockerignore` (build context `web/`, user không phải root, `HOSTNAME=127.0.0.1`); xác nhận bằng `docker build` và `docker run` trên máy có Docker, `server.js` ở gốc, container chạy và `/web-healthz` trả 200 **(ĐÃ VIẾT, CHƯA CHẠY `docker build` (không có Docker daemon trong phiên); các bước tương đương đã chạy thủ công (`npm ci`, `next build`, chạy `server.js` standalone, `/web-healthz` 200))**
- [x] 2.4 Đo RSS container dưới tải trang chủ và ghi vào `design.md`; xác nhận nằm trong `mem_limit` **(đã đo RSS ~157–177 MB cho trang tĩnh (ghi trong design.md); chưa đo trong container/SSR thật)**

## 3. Compose và CD

- [x] 3.1 Thêm service `web` vào `docker-compose.production.yml` (host network, `127.0.0.1:3000`, `mem_limit`, healthcheck, log như các service khác, không `env_file` production); xác nhận bằng `docker compose config` **(đã làm: `docker compose config` hợp lệ)**
- [x] 3.2 Thêm service `web` vào `docker-compose.dev.yml` và cập nhật `nginx/dev.conf` dùng cấu hình mới; xác nhận chạy `docker compose -f docker-compose.dev.yml up` thấy trang Django và `/_next/` đúng nơi **(đã làm: `docker compose config` hợp lệ; nginx dev dùng chung `deploy/nginx`, `nginx -t` đạt, 25 kịch bản dev đạt; chưa chạy `up` (không có Docker daemon))**
- [ ] 3.3 Cập nhật `cd.yml`: job build web (tag theo hash cây `web/`, bỏ qua nếu đã có), bước deploy web riêng không làm rollback backend; xác nhận bằng chạy `workflow_dispatch` trên nhánh thử **(ĐÃ VIẾT, CHƯA CHẠY workflow thật (cần `workflow_dispatch` trên nhánh thử); YAML hợp lệ, script từ xa qua `bash -n`, đường ống nginx đã mô phỏng)**
- [x] 3.4 Cập nhật `CI-CD.md` (hai image, deploy độc lập, cấu hình nginx trong repo, quy trình reload/hoàn tác); xác nhận bằng đọc lại các lệnh trong tài liệu chạy đúng như viết **(đã làm)**

## 4. Cấu hình nginx trong repo

- [ ] 4.1 Hoàn thiện `deploy/nginx/` đã đối chiếu baseline (task 1.1) và sinh `snippets/cloudflare-realip.conf` từ danh sách IP chính thức của Cloudflare lúc deploy; xác nhận bằng `nginx -t` trên bản nginx đúng phiên bản production **(ĐÃ VIẾT `deploy/nginx` và `scripts/gen_cloudflare_realip.sh`; `nginx -t` đạt trên 1.24 Ubuntu; CHƯA đối chiếu với `nginx -T` production (task 1.1) và CHƯA thử tải danh sách IP Cloudflare thật (proxy phiên chặn))**
- [x] 4.2 Viết bước CD đồng bộ `deploy/nginx/` lên `/var/www/thinkcodeoj/nginx/`, chạy `nginx -t`, giữ bản cũ, hoàn tác khi lỗi, reload khi đạt; xác nhận bằng thử cố ý một cấu hình lỗi và thấy site không gián đoạn **(đã làm: kiểm thử bằng nginx 1.24 thật (hợp lệ, cú pháp sai, site hỏng sau reload, thiếu file, dọn sao lưu) và mô phỏng đường ống CD)**
- [ ] 4.3 Thiết lập một lần trên server (sudo hẹp hoặc thủ công): dòng `include` trong nginx chính; xác nhận `nginx -T` thấy cấu hình mới
- [ ] 4.4 Áp dụng cấu hình **không có route Next.js**; xác nhận mọi trang chính (`/`, `/problems`, `/submissions/`, `/contests/`, đăng nhập, `/admin/`, `/event/`) giống trước, và `/web-healthz` từ ngoài trả 403
- [x] 4.5 Chạy lại bộ 36 kịch bản định tuyến trên cấu hình cuối và ghi kết quả vào `design.md`; xác nhận không kịch bản nào lỗi **(đã làm: 36 kịch bản đạt trên `deploy/nginx`)**

## 5. IP thật của người dùng

- [x] 5.1 Nếu 1.2 xác nhận vấn đề: thêm middleware đặt `REMOTE_ADDR` từ `X-Real-IP` chỉ khi kết nối từ loopback, cấu hình bằng setting, đặt đầu `MIDDLEWARE`; xác nhận bằng chạy Django phía sau nginx thử thấy IP đúng trong `Profile.ip` **(đã làm (tắt mặc định, bật bằng `TRUSTED_PROXY_IPS`): 11 tình huống + đầu cuối `Profile.ip` trên Django+MariaDB)**
- [x] 5.2 Xác nhận header giả `X-Real-IP`/`X-Forwarded-For` từ client bên ngoài không đổi được IP ghi nhận; xác nhận bằng yêu cầu thủ công qua nginx **(đã làm: header giả từ peer không tin cậy bị bỏ qua)**

## 6. Hoàn tất

- [ ] 6.1 Triển khai thật theo Migration Plan, kiểm tra `web` chạy, chưa có trang nào do Next.js phục vụ; xác nhận bằng `docker compose ps` và log nginx không có `us=502`
- [ ] 6.2 Cập nhật `plan.md` (đánh dấu change #1 xong, ghi các phát hiện chính)

## Workflow follow-up

- Review, approve rồi apply; sau đó lưu trữ change (`/opsx:archive`).
- Change tiếp theo: `api-foundation`, rồi từng trang theo bảng route.

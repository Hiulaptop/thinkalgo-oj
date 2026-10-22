# Cấu hình nginx của ThinkAlgo OJ

Nguồn sự thật cho định tuyến Django ↔ Next.js. Thiết kế và các thử nghiệm: `openspec/changes/monorepo-compose-layout/design.md`.

```
oj.conf               server block (realip, gzip, static, /_next/, /web-healthz, /event/, /channels/, routes, /admin/, /)
upstreams.conf        django_app, web_app, web_with_fallback, wsevent_get, wsevent_poll
maps.conf             owner_live, owner_preview, forwarded_proto, connection_upgrade, log_format
routes/next-owned.conf  trang do Next.js phục vụ (mặc định rỗng)
snippets/             proxy-headers, proxy-django, proxy-next, route-page
snippets/cloudflare-realip.conf   KHÔNG nằm trong repo: sinh lúc deploy bằng scripts/gen_cloudflare_realip.sh
```

Cài đặt trên server: cả thư mục này được chép tới `/var/www/thinkcodeoj/nginx/`, nginx chính có một dòng
`include /var/www/thinkcodeoj/nginx/oj.conf;` (include dùng đường dẫn **tuyệt đối**; include tương đối của nginx
được tính từ `/etc/nginx`, không phải từ file đang include). Áp dụng bằng `scripts/deploy_nginx_config.sh`
(có `nginx -t`, giữ bản cũ, tự hoàn tác nếu lỗi).

## Chuyển một trang sang Next.js

Thêm một khối vào `routes/next-owned.conf` (xem mẫu trong file). Ba trạng thái: không có khối (Django),
`$owner_preview` (cookie `web_preview=1`), `$owner_live` (mọi GET/HEAD; Django là dự phòng). Khớp URL chính xác
(`location =` hoặc regex có `$`), đúng dấu `/` cuối của Django. Hoàn tác: gỡ khối và áp dụng lại.

## Môi trường dev

`docker-compose.dev.yml` mount thư mục này vào nginx dev và ghi đè `upstreams.conf` (tên service) và
`snippets/cloudflare-realip.conf` (rỗng) bằng các file trong `nginx/dev/`.

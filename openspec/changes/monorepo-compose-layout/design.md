# Design

## Context

Xem `proposal.md` cho lý do. Hiện trạng đọc từ repo (CI-CD.md, `cd.yml`, `docker-compose.*.yml`, `dmoj/urls.py`, `settings`, `websocket/`):

- Production là một VPS (2 vCPU / 2 GB). MariaDB, Redis và **nginx chạy native**; 4 container (`site`, `bridged`, `celery`, `wsevent`) dùng chung một image, `network_mode: host`. Image build trên GitHub Actions, đẩy lên GHCR; CD ghi compose tạm lên server rồi `down` + `up -d`.
- Cloudflare **Flexible SSL**: Cloudflare nói HTTPS với người dùng, HTTP thường tới origin; WebSocket client dùng `wss://oj.thinkcode.vn/event/`.
- Django nghe `127.0.0.1:8000` bằng `uwsgi --http-socket`; `ALLOWED_HOSTS` chỉ có `oj.thinkcode.vn` nên mọi request tới Django phải mang đúng `Host`.
- `wsevent`: 15100 (client WebSocket), 15101 (Django POST sự kiện, nội bộ), 15102 (long-poll `/channels/`, timeout 29 s). Judge nói chuyện với `bridged` qua TCP 9999, không qua nginx.
- Tệp tĩnh: nginx đọc `/var/www/thinkcodeoj/static` (bind-mount ghi được vào `site` vì django-compressor chạy online, xem CI-CD.md §3.4), `/var/www/thinkcodeoj/media`, `static-passthrough/` (`502.html`, `robots.txt`), `icons/`.
- Django có 90 mẫu URL cấp đầu; dạng dấu `/` khác nhau giữa danh sách và chi tiết. Quy tắc dấu `/` cuối ở Django (đã kiểm bằng request thật): **trang danh sách có `/` cuối** (`/problems/`, `/submissions/`, `/users/`, `/blogs/`, `/contests/`), **trang chi tiết thì không** (`/problem/<mã>`, `/user/<tên>`, `/contest/<key>`); dạng còn lại Django tự 301 sang dạng chuẩn.
- Cloudflare đang có Redirect Rule cho `/martor/`, `/pdf/`, `/static-upload/` sang `media.oj.thinkcode.vn`.

### Điều đã kiểm chứng và điều chưa

**Đã kiểm chứng bằng thử nghiệm trong phiên làm việc** (nginx 1.24 + upstream giả; uwsgi cài bản mới nhất; Next.js 15.5.28 build thật):
1. `output: "standalone"` build được với Next.js 15.5.28; `server.js` ở gốc thư mục standalone khi build trong thư mục không có `package.json`/lockfile cha. Khi có một `package.json` ở thư mục cha, Next suy ra gốc theo dõi sai và lồng `server.js` vào thư mục con. Repo này có `package.json` ở gốc nên **build context của image phải là `web/`**.
2. Thư mục App Router bắt đầu bằng `_` là private, không thành route. Endpoint kiểm tra sống không được đặt dưới `/_w/...`; dùng `/web-healthz`.
3. Trang tĩnh của Next.js mặc định gửi `Cache-Control: s-maxage=31536000`. Cấu hình `headers()` trong `next.config.ts` ghi đè được thành `private, no-cache` mà vẫn giữ `public, max-age=31536000, immutable` cho `/_next/static/`.
4. `compress: false` có tác dụng (không có `Content-Encoding`).
5. Bộ nhớ: tiến trình `next-server` standalone ở mức khoảng 157 MB RSS sau ~900 request, ~177 MB sau thêm 4 000 request đồng thời (40 luồng), trang tĩnh, máy 16 GB. Trang SSR có dữ liệu sẽ nặng hơn, chưa đo.
6. **uwsgi `--http-socket` + `proxy_pass` làm Django thấy `REMOTE_ADDR=127.0.0.1`** với mọi người dùng; `X-Real-IP` đúng nhưng chỉ nằm trong header. Cùng ứng dụng với `--socket` + `uwsgi_pass` thì `REMOTE_ADDR` đúng IP thật. `SERVER_SOFTWARE` không có trong cả hai.
7. nginx: location có dấu `/` cuối (kể cả `location =`) với `proxy_pass` tự trả 301 khi thiếu dấu `/` và mặc định dùng `http://` tuyệt đối; cần `absolute_redirect off` sau Cloudflare Flexible SSL. `include` tương đối được tính từ thư mục cấu hình chính chứ không phải thư mục của file đang include; `proxy_read_timeout` đặt hai lần trong một location là lỗi `[emerg]`.
8. Bản nháp trong `deploy/nginx/` qua `nginx -t` và 36 kịch bản định tuyến (mặc định Django, `/_next/`, live/preview/POST, khớp chính xác `/problem/<mã>`, header IP/proto, tệp tĩnh, WebSocket, long-poll, `/web-healthz`, dự phòng khi Next trả 500 hoặc tắt) đều đạt. Kịch bản chạy bằng script tạm, **không đưa vào repo**.

**Chưa kiểm chứng (cần làm trên server hoặc có Docker daemon):**
- Cấu hình nginx production thật (không có trong repo): vì vậy bản nháp là *đề xuất*, mọi giá trị nền (timeout, kích thước upload, cache `/static/`, vị trí `icons/`, realip Cloudflare) phải đối chiếu với `nginx -T`.
- Việc Django thật sự ghi `127.0.0.1` cho IP người dùng trên production (suy ra từ thử nghiệm 6 và việc repo không có middleware đọc `X-Real-IP`/`X-Forwarded-For`; `Profile.ip`, giới hạn đặt lại mật khẩu `pwreset!<IP>` và xác thực theo IP đều dùng `REMOTE_ADDR`).
- `docker build` của `web/Dockerfile` (không có Docker daemon trong phiên), healthcheck trong container, `mem_limit` của Compose.
- Giá trị `mem_limit`/`--max-old-space-size` dưới tải SSR thật.
- Tài liệu chính thức của Next.js về `standalone`/`headers()` (Context7 và trang tài liệu bị chặn); các kết luận dựa trên chạy thử Next.js 15.5.28.

## Goals / Non-Goals

**Goals:**
- Đưa `web` ra production mà không đổi hành vi của bất kỳ trang nào (mặc định mọi thứ vẫn về Django).
- Mỗi trang chuyển được bằng một khối cấu hình, thử trước bằng cookie, hoàn tác bằng gỡ khối đó, và an toàn khi Next.js lỗi.
- Cấu hình nginx nằm trong repo, áp dụng có kiểm tra và hoàn tác.

**Non-Goals:**
- Không chuyển trang nào (mỗi trang một change riêng).
- Không di chuyển Django vào `backend/` (xem Decisions 1).
- Không đưa nginx/Redis/MariaDB vào compose (change riêng sau, `plan.md` mục 6).
- Không thay đổi hành vi xác thực, session, CSRF.
- Không bật CSP chặt (script khởi tạo chế độ màu của `web/` là inline).

## Decisions

1. **Giữ Django ở thư mục gốc, thêm `web/` bên cạnh** (không dời vào `backend/`). Lý do: dời đổi đường dẫn trong Dockerfile, CI, `CI-CD.md`, script ops, rủi ro lớn mà không mở khoá điều gì ở giai đoạn này. Thay thế: dời ngay (làm sau nếu cần, độc lập).

2. **Hai image, tag khác nhau.** Backend giữ tag `sha-<commit>` như hiện tại. Web gắn tag theo **hash cây `web/`** (`git rev-parse HEAD:web`), nên chỉ đổi khi `web/` đổi; CD bỏ qua build nếu tag đã tồn tại. Thay thế: tag theo commit cho cả hai (mỗi commit đều deploy lại web).

3. **Web chạy `network_mode: host`, nghe `127.0.0.1:3000`** (khớp các container hiện tại; nginx native gọi được). Đặt `HOSTNAME=127.0.0.1` tường minh vì Docker tự gán `HOSTNAME` là id container. Không cấp `env_file` production cho web (không cần mật khẩu DB), chỉ biến cần thiết. Thay thế: mạng bridge (chờ change đưa nginx vào compose).

4. **Dockerfile `web/`** (đa tầng, `node:22-bookworm-slim`): tầng deps `npm ci`, tầng build `npm run build`, tầng chạy copy `.next/standalone` và `.next/static`, chạy bằng user `node`, `NODE_OPTIONS=--max-old-space-size=256`. Build context là `web/`; `outputFileTracingRoot` được ghim vào `web/` nên `server.js` luôn ở gốc thư mục standalone (đã kiểm chứng: không ghim thì lồng vào `web/`). Chọn bản Debian slim thay vì Alpine để tránh khác biệt glibc/musl của binary SWC. `mem_limit: 384m`; healthcheck dùng chính Node (`fetch`) vì image slim không có `wget`/`curl`. Chưa chạy `docker build` được trong phiên (không có Docker daemon).

5. **Nginx giữ native trong change này, cấu hình đặt ở thư mục user deploy ghi được.** Cả `deploy/nginx/` được CD chép tới `/var/www/thinkcodeoj/nginx/`; nginx chính có một dòng `include /var/www/thinkcodeoj/nginx/oj.conf;` (root làm một lần). Áp dụng bằng quyền sudo **hẹp** cho đúng `nginx -t` và `systemctl reload nginx`, cộng bước giữ bản cũ và hoàn tác nếu `nginx -t` lỗi. Thay thế: (a) nginx thành container ngay (loại bỏ sudo nhưng đổi cửa vào, cần cutover cổng 80, để change sau); (b) thủ công mỗi lần chuyển trang (chậm, dễ sai).

6. **Định tuyến ba trạng thái bằng hai `map` và một upstream có dự phòng.** `owner_live` (GET/HEAD → `web_with_fallback`, còn lại → Django) và `owner_preview` (thêm điều kiện cookie `web_preview=1`). `web_with_fallback` = Next.js + Django làm `backup`; `proxy_next_upstream error timeout http_500 http_502 http_503 http_504`. nginx mặc định không thử lại phương thức không idempotent nên POST không bao giờ bị gửi lặp. Thay thế đã loại: `error_page ... = @fallback` (POST có thể bị chạy lặp khi Django 500) và `if ($request_method)` trong location.

7. **Khớp URL chính xác, không dùng prefix rộng.** Mỗi trang là `location = <URL chuẩn của Django>` hoặc regex có neo `$`. Bảng chủ sở hữu ở "Bảng route" bên dưới là nguồn sự thật. Dấu `/` cuối: nginx tự 301 `/x` → `/x/` cho location có `/` cuối (đúng như `APPEND_SLASH` của Django); với route chi tiết không có `/` cuối (`/problem/<mã>`), dạng `/problem/<mã>/` rơi về Django (Django 301 về dạng không `/`). Next.js đặt `skipTrailingSlashRedirect: true` để **không bao giờ** tự đổi dấu `/` ngược với Django (nếu không sẽ vòng lặp chuyển hướng giữa hai bên).

8. **Cache HTML do Next.js tự đặt** (`headers()` → `private, no-cache`), nginx không đụng vào `Cache-Control`. Vì web_with_fallback có thể trả trang Django, nếu nginx ghi đè `Cache-Control` sẽ làm mất chính sách của Django.

9. **IP thật:** nginx dùng `realip` với `CF-Connecting-IP` (danh sách `set_real_ip_from` sinh từ danh sách IP chính thức của Cloudflare lúc deploy, không gõ tay trong repo) và luôn **ghi đè** `X-Real-IP`/`X-Forwarded-For` (không nối). Phía Django thêm **middleware đặt `REMOTE_ADDR` từ `X-Real-IP` chỉ khi kết nối đến từ loopback**, đặt đầu danh sách middleware (sau khi xác nhận vấn đề thật trên production). Next.js khi gọi Django phía server phải chuyển tiếp `X-Real-IP`. Thay thế: đổi uwsgi sang `--socket` + `uwsgi_pass` (đã kiểm chứng cho `REMOTE_ADDR` đúng nhưng Next.js cần thêm một socket HTTP riêng để gọi Django, và đổi healthcheck/CD hiện có). Cả hai đều chấp nhận được; middleware được chọn vì một đường duy nhất cho cả trình duyệt lẫn Next.js.

10. **Endpoint sống `/web-healthz`** (không dưới thư mục `_`), nginx chỉ cho `127.0.0.1`. Không dùng `/healthz` vì có thể đụng route Django sau này.

11. **Không đưa test tự động vào repo.** Kiểm chứng nginx bằng script tạm (36 kịch bản ở trên). Nếu muốn giữ lại thành kịch bản chạy lại được thì cần đề xuất kịch bản riêng và được duyệt.

## Bảng route (nguồn sự thật chủ sở hữu, cập nhật khi chuyển trang)

URL chuẩn lấy từ `dmoj/urls.py`. Cột "Matcher" là dạng nginx dùng khi chuyển sang Next.js.

| Nhóm | URL chuẩn của Django | Dự kiến | Matcher khi chuyển |
|---|---|---|---|
| Blog | `/blogs/`, `/post/<id>-<slug>` | Next.js (đợt 1) | `= /blogs/`, `~ ^/post/\d+-[^/]+$` |
| Đề bài | `/problems/`, `/problem/<mã>` | Next.js (đợt 1) | `= /problems/`, `~ ^/problem/[^/]+$` |
| Bài nộp | `/submissions/`, `/submission/<id>` | Next.js (đợt 2) | `= /submissions/`, `~ ^/submission/\d+$` |
| Xếp hạng | `/users/` | Next.js (đợt 2) | `= /users/` |
| Hồ sơ | `/user/<tên>`, `/user` | Next.js (đợt 3) | `~ ^/user/[^/]+$` |
| Cuộc thi | `/contests/`, `/contest/<key>` (+ ranking) | Next.js (đợt 3; ranking trực tiếp cuối) | `= /contests/`, `~ ^/contest/[^/]+$` |
| Tổ chức | `/organizations/`, `/organization/<slug>` | Next.js (sau) | cân nhắc riêng |
| Giữ ở Django | `/admin/`, `/login/`, `/logout/`, `/accounts/`, `/password/`, `/2fa/`, `/api/`, `/comments/`, `/widgets/`, `/judge-select2/`, `/tasks/`, `/martor/`, `/pdf/`, `/static-upload/`, `/src/<id>`, `/data/`, `/sitemap.xml`, `/feed/`, `/contests.ics`, `/i18n/`, `/shorteners/`, `/mailgun/` | Django | (không có khối) |
| Trang chủ | `/` | Django cho tới khi có bản vẽ/spec trang chủ | `= /` |

Đường dẫn Next.js sở hữu riêng (không đụng Django): `/_next/`, `/web-healthz`. Không dùng `/api/` của Next.js vì `/api/` thuộc Django.

## Thiết kế nginx (`deploy/nginx/`)

```
deploy/nginx/
  oj.conf               server block: realip, gzip, static, /_next/, /web-healthz,
                        /event/, /channels/, include routes, /admin/, /
  upstreams.conf        django_app, web_app, web_with_fallback, wsevent_get, wsevent_poll
  maps.conf             owner_live, owner_preview, forwarded_proto, connection_upgrade, log_format
  routes/next-owned.conf  danh sách trang (mặc định rỗng; có mẫu)
  snippets/             proxy-headers, proxy-django, proxy-next, route-page
```

Các quyết định trong cấu hình:
- `absolute_redirect off` (xem thử nghiệm 7). `X-Forwarded-Proto` lấy từ Cloudflare, rơi về `$scheme` khi thiếu.
- `/event/` dùng `proxy_pass http://wsevent_get/` (bỏ prefix), nâng cấp Upgrade, timeout 3600 s; `/channels/` giữ nguyên đường dẫn, tắt buffering, timeout 120 s (long-poll 29 s). Hai giá trị timeout là đề xuất, đối chiếu với baseline.
- `/_next/` và `/web-healthz` luôn tới Next.js (không có dự phòng vì Django không có các đường dẫn này).
- `/admin/` timeout 600 s theo `uwsgi --harakiri 600`; mặc định Django 120 s. Giá trị nền (upload `200m` lấy từ `nginx/dev.conf`) cần khớp baseline.
- Log có `$upstream_addr`, `$upstream_status`, `$request_id`, `CF-Ray` để theo dõi việc dự phòng; `X-Request-Id` được gửi tới cả hai upstream.
- Khuyến nghị tăng cường (ngoài phạm vi): chỉ cho phép cổng 80 từ dải IP Cloudflare ở tường lửa.

### Quy trình chuyển một trang (dùng cho các change trang sau)
1. Dựng trang Next.js + endpoint API, kiểm tra quyền (xem `api-foundation`).
2. Thêm khối `preview` vào `routes/next-owned.conf`, deploy cấu hình. Chỉ người có cookie `web_preview=1` thấy bản mới; đối chiếu với bản Jinja.
3. Đổi thành `live`. Theo dõi `us=` (upstream status) trong log; mọi lần rơi về Django là tín hiệu cần xem.
4. Hoàn tác: gỡ khối, deploy cấu hình (một commit, vài giây).
5. Khi mọi trang xong: bỏ dự phòng và Jinja (change `retire-jinja-templates`).

## Risks / Trade-offs

- [IP người dùng đang sai (`127.0.0.1`)] → Xác nhận bằng truy vấn trên production (Open Questions); nếu đúng, middleware ở Decisions 9. Trong khi chờ, giới hạn đặt lại mật khẩu đang dùng một nhóm chung cho mọi người.
- [Cấu hình thật khác bản nháp] → Bước đầu tiên là chụp `nginx -T` và đối chiếu từng giá trị trước khi áp dụng; áp dụng đầu tiên không có route Next.js nào (không đổi hành vi).
- [Sai cấu hình nginx làm sập mọi trang] → `nginx -t` trước khi reload, giữ bản cũ để hoàn tác tự động, kiểm tra sống sau reload.
- [Sudo cho user deploy] → Chỉ hai lệnh cụ thể bằng `NOPASSWD`; hoặc thực hiện thủ công nếu không chấp nhận.
- [RAM 2 GB] → `mem_limit` + `--max-old-space-size`, đo lại dưới tải SSR thật trước khi live trang đầu tiên; nếu thiếu, nâng VPS.
- [Vòng lặp chuyển hướng dấu `/`] → `skipTrailingSlashRedirect` và khớp URL chuẩn chính xác; có kịch bản kiểm tra khi thêm route.
- [Cloudflare cache HTML] → `private, no-cache` từ Next.js; kiểm tra `cf-cache-status` sau khi live.
- [`/problem/<mã>/...` bị che] → chỉ dùng matcher neo `$` (kịch bản đã kiểm chứng).
- [CD đổi từ `down` sang cập nhật từng service] → giữ nguyên `down` cho nhóm backend như hiện tại, web triển khai bước riêng; kiểm tra bằng deploy thử trước khi dùng cho release thật.

## Kết quả thực hiện (2026-10-22)

Đã làm và kiểm chứng trong phiên: cấu hình `web/` production, `/web-healthz`, `web/Dockerfile` (viết, chưa build), service `web` trong compose production và dev (`docker compose config` hợp lệ), `deploy/nginx` (nginx 1.24: `nginx -t` + 36 kịch bản), nginx dev dùng chung cấu hình (25 kịch bản), `scripts/gen_cloudflare_realip.sh` (hợp lệ/rác/rỗng/404), `scripts/deploy_nginx_config.sh` (5 tình huống), `cd.yml` mới (3 job thêm), middleware IP thật (tắt mặc định).

Hai lỗi tìm thấy nhờ kiểm thử khi viết `deploy_nginx_config.sh`: (1) hai lần chạy trong cùng một giây dùng chung tên bản sao lưu nên `mv` lồng thư mục vào nhau, giờ hậu tố có PID; (2) `reload` bất đồng bộ nên lần kiểm tra đầu có thể rơi vào worker cũ và báo đạt dù cấu hình mới hỏng, giờ chờ 2 giây rồi bắt buộc 5 lần liên tiếp đều đạt.

Chưa làm (cần server hoặc Docker): task 1.x, `docker build`, chạy workflow thật, thiết lập sudo/include trên server, áp dụng cấu hình production, bật `TRUSTED_PROXY_IPS`.

## Migration Plan

1. Trên server (chỉ đọc): chụp `nginx -T`, kiểm tra IP trong DB (Open Questions), liệt kê thư mục `static-passthrough`/`icons`. Đưa vào `deploy/nginx/baseline/` làm tham chiếu (không áp dụng).
2. Đối chiếu bản nháp với baseline, sửa cho khớp; chạy lại bộ kịch bản định tuyến.
3. Thêm `web/Dockerfile`, `next.config.ts`, `/web-healthz`; build thử `docker build` ở máy có Docker.
4. Cập nhật `cd.yml`: build web, deploy web độc lập; deploy thử.
5. Cài cấu hình nginx mới **không có route Next.js** (chỉ `/_next/`, `/web-healthz`): không đổi hành vi nào; có `nginx -t`, bản cũ lưu sẵn.
6. Bật middleware IP thật (nếu xác nhận cần).
7. Kết thúc: web chạy nhưng chưa nhận traffic trang nào. Việc chuyển trang thuộc các change sau.

Hoàn tác: gỡ include của `oj.conf`, khôi phục bản nginx cũ, `docker compose stop web`.

## Open Questions

- Truy vấn xác nhận IP: `SELECT ip, COUNT(*) AS n FROM judge_profile WHERE ip IS NOT NULL GROUP BY ip ORDER BY n DESC LIMIT 5;` Nếu `127.0.0.1` chiếm đa số thì vấn đề là thật.
- Chấp nhận sudo hẹp cho user deploy, hay làm thủ công mỗi lần đổi cấu hình nginx?
- Cần nâng RAM VPS trước khi live trang SSR đầu tiên không (đo trên server thật)?
- Có thêm kiểm thử tự động cho cấu hình nginx vào repo không? (cần duyệt kịch bản, `AGENTS.md`-style của dự án.)

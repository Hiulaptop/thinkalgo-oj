# plan.md — Chuyển dần ThinkAlgo OJ từ Django sang Next.js

> Trạng thái: **bản nháp định hướng**, chưa phải spec. Theo `AGENTS.md` mục 3, mỗi giai đoạn cần một change OpenSpec (`/opsx:propose`) và được approve rồi mới làm.
> Các tên thư viện và hành vi cụ thể trong file này viết từ kiến thức chung, **chưa được tra tài liệu chính thức**. Phải xác nhận trong spec của từng change (Context7 hoặc tài liệu chính thức, ghi nguồn và ngày tra).

## 1. Mục tiêu và phạm vi hiện tại

- **Mục tiêu dài hạn:** thay stack Django (Jinja2, MariaDB, Redis, Celery) bằng Next.js + Postgres, queue trên Postgres.
- **Ưu tiên bây giờ:** chỉ chuyển **UI sang Next.js**. Backend, DB, queue, judge bridge giữ nguyên. Phần "stack mới" ở mục 6 để xem xét sau.
- **Cách chuyển:** dần dần (strangler). Mỗi lần chuyển một trang, trang chưa chuyển vẫn chạy bằng Jinja. Rollback một trang chỉ cần sửa một dòng nginx.

## 2. Hiện trạng (đã đọc từ repo)

- Fork VNOJ/DMOJ. Django 4.2, MariaDB, Redis, Celery.
- Bốn tiến trình dùng chung một image: `site` (uwsgi), `bridged` (điều phối judge), `celery`, `wsevent` (Node.js, WebSocket sự kiện trực tiếp). Judge chạy ở repo riêng `thinkcode-judge-server`.
- Frontend: khoảng 238 template Jinja2 + SCSS/JS rời rạc trong `resources/`. Design system bắt buộc nằm ở `style.md`.
- API: gần như chưa có. `api/v2` chỉ có 4 endpoint đồng bộ contest (dùng API key); còn lại là khoảng 15 endpoint AJAX không có schema thống nhất.
- Hạ tầng production: một VPS 2 vCPU / 2GB RAM. MariaDB, Redis và **nginx chạy native trên host**; các container dùng `network_mode: host`. Image build trên GitHub Actions rồi đẩy lên `ghcr.io`.

## 3. Kiến trúc đích cho giai đoạn UI

```
Browser → nginx → Next.js (SSR) ──HTTP, forward cookie──▶ Django API ──▶ MariaDB
                └─ trang chưa chuyển ─▶ Django (Jinja2)
                └─ /admin /static /media /api ─▶ Django
                └─ WebSocket ─▶ wsevent
```

- Hai image, một compose: `backend` (image hiện tại) và `web` (Next.js). Service `web` có `WEB_IMAGE_TAG` riêng để deploy frontend không buộc phải deploy backend.
- **Cùng domain** `oj.thinkcode.vn` qua nginx để giữ session cookie của Django, tránh CORS/CSRF cross-origin.
- Trình duyệt chỉ nói chuyện với Next.js (và WebSocket). Server component của Next.js gọi API Django và **chuyển tiếp cookie**.
- **Django vẫn là nơi duy nhất xác thực và kiểm tra quyền** (xem `PERMISSIONS.md`). Next.js không tự suy ra quyền.
- Type TypeScript sinh từ schema OpenAPI của Django, để API đổi mà frontend không đổi theo thì build lỗi.
- Giữ Django admin; không nằm trong phạm vi chuyển UI.

### 3.1 Cấu trúc repo (monorepo)

```
thinkalgo-oj/
  backend/        Django hiện tại (có thể dời sau, xem câu hỏi mở)
  web/            Next.js (thêm mới)
  packages/       tokens, ui, api-client (dùng chung nếu cần)
  deploy/         docker-compose.*, nginx
  openspec/, AGENTS.md, DESIGN.md, plan.md
```

### 3.2 Định tuyến nginx

Đã nghiên cứu và thiết kế chi tiết trong change `monorepo-compose-layout`
(`openspec/changes/monorepo-compose-layout/`, kèm cấu hình `deploy/nginx/` đã qua
`nginx -t` và 36 kịch bản định tuyến). Tóm tắt:

- nginx vẫn native; cấu hình đưa vào repo (`deploy/nginx/`) và được CD đồng bộ.
- Mỗi trang đã chuyển có 3 trạng thái: Django, `preview` (cookie `web_preview=1`), `live`.
  Next.js lỗi thì nginx tự thử lại trên Django (GET/HEAD); POST luôn về Django.
- Khớp URL **chính xác** (`location =` hoặc regex có `$`), không dùng prefix rộng như `/problem/`
  vì sẽ che các route con của Django. Dấu `/` cuối phải giống hệt Django (`/problems` nhưng `/submissions/`).
- `/_next/` và `/web-healthz` luôn tới Next.js; `/event/`, `/channels/`, `/static/`, `/media/` giữ nguyên.
- Phát hiện cần xử lý: Django đang thấy IP người dùng là `127.0.0.1` (uwsgi `--http-socket` +
  `proxy_pass`); trang HTML tĩnh của Next.js mặc định `s-maxage=31536000`.

### 3.3 Design system

- Token màu, font, spacing lấy từ `style.md` thành `tokens` (CSS variables, Tailwind v4 `@theme`) và component trong `ui`.
- Component chỉ đọc token *semantic*; site đổi phong cách bằng cách ánh xạ lại tầng semantic.
- Navbar/footer của Next.js phải trông giống bản Jinja trong thời gian hai hệ thống cùng tồn tại.
- Mọi UI mới đi theo `AGENTS.md` mục 4: vẽ bản phác, được approve rồi mới làm.

## 4. Lộ trình các change OpenSpec (giai đoạn UI)

| # | Change (tên gợi ý) | Nội dung chính |
|---|---|---|
| 1 | `monorepo-compose-layout` | **Đã soạn spec** (`openspec/changes/`). Thêm image/service `web` (chưa nhận traffic), đưa cấu hình nginx vào repo, định tuyến chuyển dần có dự phòng, sửa IP thật. Chờ duyệt |
| 2 | `api-foundation` | **Đã soạn spec**. DRF ghim `<3.18` (3.18 cần Django ≥5.2), drf-spectacular, API đọc đợt 1 (me, đề, bài nộp, xếp hạng, blog), quyền dùng lại phương thức của model. Chờ duyệt |
| 3 | `web-bootstrap-playful` (**đã làm**, xem `openspec/changes/web-bootstrap-playful/`) | Dựng Next.js 15, token từ `style.md`, layout (navbar, footer) giống bản Jinja, i18n (locale `vi` hiện dùng gettext của Django) |
| 4 | Mỗi trang một change (bản vẽ đợt 1 ở `docs/design/web-pages.md`, chờ duyệt) | Thứ tự rủi ro thấp trước: blog → problem list/detail → ranking → submission list → contest → user/profile. Mỗi trang kèm bản vẽ và ảnh chụp đối chiếu |
| 5 | `retire-jinja-templates` | Khi mọi trang đã chuyển: bỏ template Jinja, compressor, SCSS cũ. Giữ API và admin |

Với mỗi trang: viết endpoint API (kèm kiểm tra quyền giống view cũ) → vẽ bản phác → dựng trang → đối chiếu → chuyển route nginx.

## 5. Rủi ro của giai đoạn UI

- **RAM 2GB:** thêm Node.js SSR làm tăng áp lực bộ nhớ khi đã chạy chung MariaDB và Redis. Đo trước khi chuyển trang đầu tiên; đặt giới hạn bộ nhớ cho container `web`; cân nhắc nâng VPS.
- **Phân quyền:** ẩn đề, contest riêng tư, organization. API sai quyền có thể làm lộ đề hoặc bài nộp. Cần liệt kê rõ các trường hợp quyền cho mỗi endpoint trong spec.
- **Đồng thời hai hệ thống:** cache, i18n, session và giao diện tồn tại song song trong thời gian dài.
- **Compressor cache của Django:** `CLAUDE.md` đã ghi sự cố CSS 404 liên quan; khi đổi cấu trúc static/nginx phải giữ nguyên quy tắc bind-mount.
- **Workflow GitHub Actions và `CI-CD.md`:** chưa đọc kỹ, chưa biết mức thay đổi.

## 6. Hướng dài hạn (hoãn, xem lại sau khi UI xong)

Mục tiêu: Next.js + Postgres, queue trên Postgres thay Redis.

- **Làm Postgres trước khi chuyển logic:** Django hỗ trợ Postgres sẵn, nên migrate MariaDB → Postgres có thể làm trong khi ứng dụng vẫn là Django. Sau đó Next.js mới có thể truy cập cùng một DB.
- **Quy tắc "một bảng, một chủ":** khi một miền chuyển sang Next.js, bảng của miền đó chỉ do Next.js ghi; Django chỉ đọc hoặc gọi API. Migration schema chỉ do chủ bảng thực hiện. ORM phía Next.js nên sinh schema từ DB hiện có thay vì tạo lại.
- **Thay thế Redis:**

| Việc của Redis/AMQP | Thay bằng | Điều kiện |
|---|---|---|
| Hàng đợi (Celery) | Hàng đợi trên Postgres (ví dụ pg-boss, Graphile Worker; cần tra tài liệu) | Tác vụ Celery phải được viết lại thành worker Node |
| Pub/sub sự kiện (`event_poster_*`, `wsevent`) | `LISTEN/NOTIFY` của Postgres | Cần daemon giữ kết nối lâu |
| Cache (django-redis, ranking) | Cache Next.js, bảng `UNLOGGED` hoặc materialized view | Xem lại phần ranking contest đang cache nặng |

  Chỉ bỏ Redis sau khi Celery và cache của Django đã được thay.
- **Xác thực:** mật khẩu Django dùng hash chuẩn; Node có thể xác minh nên khi chuyển auth không cần bắt người dùng đặt lại mật khẩu (cần kiểm tra thuật toán thực tế trong DB). 2FA (TOTP, WebAuthn) và social auth phải chuyển cùng lúc, nên auth nên chuyển muộn.
- **Phần không phải web, không thể nhét vào Next.js:**
  1. `bridged`: máy chủ socket giữ kết nối dài với judge. Viết lại phải hiện thực lại giao thức judge của DMOJ, mà phía judge (`thinkcode-judge-server`) là Python. Là phần rủi ro nhất, nên làm cuối cùng và thử song song với judge thật. Có thể chấp nhận giữ Python lâu dài.
  2. Worker xử lý hàng đợi (publish test data lên R2, render PDF, import Polygon...).
  3. WebSocket cho sự kiện trực tiếp (đã là Node sẵn).
- **Hạ tầng:** đưa dần nginx và Redis vào compose; MariaDB/Postgres chỉ vào compose sau khi có volume cố định và backup/restore đã kiểm chứng (repo hiện cố ý giữ DB native để không rủi ro với dữ liệu). Judge giữ riêng, không nhập vào compose chính.

Lộ trình tổng thể sau giai đoạn UI:

| Bước | Nội dung |
|---|---|
| A | MariaDB → Postgres (Django vẫn chạy), kiểm chứng backup/restore |
| B | Next.js làm chủ các bảng đã chuyển; thêm `apps/worker` với hàng đợi Postgres |
| C | Chuyển auth, submission, contest |
| D | Viết lại `bridged`, bỏ Django, bỏ Redis |

## 7. Câu hỏi mở

1. Dời Django vào `backend/` ngay, hay giữ ở gốc trong giai đoạn đầu và chỉ thêm `web/`?
2. Có nâng RAM VPS được không, hay phải giữ 2GB?
3. Deploy production hiện chạy trên nền tảng nào ngoài VPS này (workflow GitHub Actions, domain, Cloudflare)? Cần đọc `CI-CD.md` và `.github/` trước khi soạn change #1.
4. i18n: giữ gettext phía Django cho API hay chuyển sang i18n phía Next.js (ví dụ next-intl)?
5. Auth, `bridged` và việc bỏ hoàn toàn Python (mục 6) sẽ quyết sau khi UI hoàn thành.

## 8. Bước tiếp theo

Kế hoạch chuyển **toàn bộ** trang ngoài admin: xem `docs/migration/page-migration.md` (khảo sát 254 route, phân loại, 12 luồng hạ tầng dùng chung, 7 giai đoạn (0–6, giai đoạn 6 là chạy thử code trực tiếp), 4 quyết định đã chốt: i18n dùng lại `.po`, xác thực (Next.js + Django giữ OAuth/WebAuthn), Monaco tự host, không bỏ trang nào).

Đã làm: `web-bootstrap-playful` (nền tảng web), soạn spec `monorepo-compose-layout` và `api-foundation`,
vẽ bản phác các trang đợt 1 (`docs/design/web-pages.md`).

Cần bạn quyết định, theo thứ tự:
1. Duyệt `monorepo-compose-layout` (chụp `nginx -T` thật trên server là bước đầu tiên, cần bạn hoặc người có quyền SSH).
2. Duyệt `api-foundation` và kịch bản kiểm thử quyền được đề xuất trong `design.md`.
3. Duyệt bản vẽ trang đợt 1 trong `docs/design/web-pages.md`.
4. Trả lời các câu hỏi mở ở mục 7 và trong `design.md` của từng change.

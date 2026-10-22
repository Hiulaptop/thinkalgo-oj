# Kế hoạch chuyển toàn bộ trang (ngoài admin) sang Next.js

> Trạng thái: **kế hoạch chờ duyệt**, chưa phải spec. Mỗi giai đoạn và mỗi nhóm trang sẽ có change OpenSpec riêng, bản vẽ được duyệt rồi mới làm (`plan.md`, `CLAUDE.md`).
> Số liệu lấy từ `dmoj/urls.py`, `templates/`, `judge/views/`, `resources/` ngày 2026-10-22. Cú pháp/thư viện chưa tra tài liệu chính thức (Context7 bị chặn); mỗi change phải tra và ghi nguồn.
> Liên quan: `plan.md` (chiến lược), `openspec/changes/monorepo-compose-layout` (định tuyến), `openspec/changes/api-foundation` (API đọc), `docs/design/web-pages.md` (bản vẽ đợt 1), `style.md`.

## 1. Mục tiêu và phạm vi

- Chuyển **mọi trang người dùng thấy** (trừ `/admin/`) sang Next.js, từng nhóm một, có thể thử và hoàn tác từng trang.
- **Giao diện mặc định sáng.** Đã thực hiện cho `web/`: mặc định sáng kể cả khi hệ điều hành tối; chỉ tối khi người dùng chọn (mục 8).
- Django vẫn là nguồn sự thật cho dữ liệu, quyền, chấm bài và admin trong suốt kế hoạch này (không đổi DB, không đổi `bridged`).

Ngoài phạm vi: `/admin/` (Django admin), đổi DB sang Postgres, viết lại `bridged`/judge, bỏ Python (xem `plan.md` mục 6).

## 2. Khảo sát hiện trạng

| Hạng mục | Số liệu |
|---|---|
| Route lá trong `dmoj/urls.py` (kể cả lồng nhau) | 254 |
| Template ngoài `templates/admin/` | 229 (tổng 238) |
| Trang HTML người dùng thật sự (ước tính, sau khi bỏ AJAX, feed, file, demo) | khoảng 110 |
| File JS giao diện trong `resources/` | 12 file, ~2 100 dòng (tương tác rời rạc: ranking trực tiếp, replay, sự kiện, hồ sơ...) |
| Biểu mẫu Django (`judge/forms.py`) | 908 dòng |
| Bản dịch | `locale/vi` + `locale/en` (Django gettext), khoảng 2 150 chuỗi |

### Theo nhóm (số route lá, số template)

| Nhóm | Route | Template | Ghi chú |
|---|---|---|---|
| Tổ chức (`organization*`) | 34 | 23 | Nhiều thao tác quản trị (thành viên, yêu cầu, tag, hạn mức, kick) |
| Đề bài (`problem*`, `tag*`) | 43 | 32 | Có trình soạn đề, dữ liệu test, import Polygon, rejudge |
| Kỳ thi (`contest*`) | 30 | 26 | Ranking trực tiếp, replay, MOSS, thống kê, tham gia |
| Người dùng, đăng ký, xác thực | ~35 | 42 | 2FA (TOTP/WebAuthn), mật khẩu, OAuth, hồ sơ, xuất dữ liệu |
| Bài nộp | ~8 | 9 | Danh sách, chi tiết, mã nguồn, diff, huỷ |
| Blog, bình luận | ~20 | 23 | Bình luận có bỏ phiếu, sửa, lịch sử |
| Ticket, thông báo | ~13 | 11 | Cập nhật trực tiếp |
| Trạng thái, runtime, license, magazine, stats, flatpages, misc | ~15 | ~25 | Phần lớn đọc đơn giản |
| Widget AJAX (`widgets/*`, `judge-select2/*`, `tasks/*`) | ~37 | — | Không phải trang: thành API/giữ lại |
| Feed, sitemap, iCal, redirect media, file tải về | ~15 | — | Giữ ở Django |

## 3. Phân loại: cái gì đi đâu

**A. Chuyển sang trang Next.js** (HTML do Jinja render hôm nay): toàn bộ danh sách, chi tiết, biểu mẫu, quản trị nội dung của người dùng (đề, kỳ thi, tổ chức, blog, ticket, hồ sơ), trang xác thực, trang lỗi.

**B. Giữ ở Django vĩnh viễn** (không phải "trang"): `/admin/`; `/accounts/` phần OAuth/callback; `/feed/*` (RSS/Atom); `/sitemap.xml`; `/contests.ics`; `/martor/`, `/pdf/`, `/static-upload/` (redirect media); tải file (`/src/<id>/raw`, `/src/<id>/download`, `/problem/<mã>/data/<path>`, `/problem/<mã>/download/package`, `/problem/<mã>/raw|pdf`, `/data/download/`, `/contest/<key>/data/download/`); `/mailgun/`; `/event/` và `/channels/` (daemon). Các route này vẫn phải được kiểm tra quyền như cũ.

**C. Trở thành API** (hiện là AJAX/HTML fragment): `widgets/*` (rejudge, trạng thái, preview Markdown, upload ảnh Martor), `judge-select2/*` và `widgets/select2/*` (JSON dạng Select2, có thể dùng nguyên giai đoạn đầu), `comments/*` (vote/sửa/lịch sử), `tasks/*` (trạng thái tác vụ Celery), `*/ajax`.

**D. Bỏ**: `tasks/success|failure|progress` (demo), `500/` (thay bằng trang lỗi Next.js), `shorteners` nếu không dùng (cần bạn xác nhận), `newsletter` (chỉ có khi app được bật; cần xác nhận).

## 4. Phần dùng chung phải có trước (luồng hạ tầng)

Đây là phần quyết định tiến độ: làm trang mà thiếu các mục này sẽ phải làm lại.

| # | Hạng mục | Nội dung | Phụ thuộc vào |
|---|---|---|---|
| W1 | Triển khai và định tuyến | `monorepo-compose-layout`: image `web`, nginx trong repo, preview/live, dự phòng, IP thật | — |
| W2 | API đọc | `api-foundation` (đợt 1) rồi mở rộng theo từng nhóm trang | W1 |
| W3 | API ghi và biểu mẫu | Quy ước ghi: CSRF, lỗi theo từng trường, idempotency, tải lên tệp, throttle. Mô tả biểu mẫu Django thành schema (trường, nhãn, kiểm tra hợp lệ) để Next.js hiển thị đúng lỗi của server | W2 |
| W4 | Xác thực | Đăng nhập/đăng xuất/đăng ký/đặt lại mật khẩu/2FA/OAuth dưới dạng luồng API + chuyển hướng; giữ session Django (cookie `sessionid`, `csrftoken`); xử lý `Set-Cookie` qua Next.js | W3 |
| W5 | i18n | Chọn cách dịch (xem mục 7, câu 1); `vi` mặc định, `en` | W1 |
| W6 | Markdown và nội dung | Hiển thị HTML đã render từ server (đề, blog, bình luận, KaTeX/MathJax), trình soạn Markdown có xem trước (11 loại preview hiện có), tải ảnh lên, tìm người dùng (`@`) | W3 |
| W7 | Trình soạn code | Chọn Monaco hoặc CodeMirror (kích thước bundle), mẫu theo ngôn ngữ, lưu bản nháp trong Zustand; thay Ace | W2 |
| W8 | Cập nhật trực tiếp | Cổng TypeScript của `event.js` (142 dòng: WebSocket `/event/` + long-poll `/channels/`, lệnh `start-msg`, theo dõi kênh) dùng nguyên daemon `wsevent` | W1 |
| W9 | Thành phần giao diện | DataTable (lọc, sắp xếp, phân trang không đếm), FilterBar, Select tìm kiếm (thay select2), Tabs, Dialog/Sheet, Toast, Pagination, biểu đồ (thống kê, rating), form field | `style.md` |
| W10 | Đồng bộ giao diện sáng/tối | Mặc định sáng; đọc/ghi cùng cookie/hồ sơ với Django (mục 8) | W4 |
| W11 | SEO và metadata | `generateMetadata`, canonical, Open Graph, `robots`; sitemap/feed vẫn do Django; URL giữ nguyên | W1 |
| W12 | Khoá kỳ thi (contest lockdown) | Người đang thi bị hạn chế truy cập (`Profile.current_contest`): `me` và các API phải phản ánh để giao diện chuyển hướng đúng | W2 |

## 5. Lộ trình theo giai đoạn

Mỗi nhóm trang đi qua cùng một quy trình (từ `monorepo-compose-layout`): API → bản vẽ được duyệt → dựng trang → so sánh song song với bản Jinja → `preview` (cookie) → `live` → theo dõi → (cuối cùng) gỡ Jinja. Kích cỡ là ước lượng tương đối (S nhỏ, M vừa, L lớn, XL rất lớn), không phải thời gian.

### Giai đoạn 0: nền tảng (đã làm một phần)
`web-bootstrap-playful` (đã làm), W1, W2 (đợt 1 chỉ đọc), W9 (cơ bản), W10 (mặc định sáng, phần cục bộ đã xong).

### Giai đoạn 1: trang đọc công khai (rủi ro thấp)
| Nhóm | URL chuẩn | Kích cỡ | Ghi chú |
|---|---|---|---|
| Blog | `/blogs/`, `/post/<id>-<slug>` | M | Chi tiết cần render Markdown (W6); bình luận tạm dẫn Django |
| Đề bài | `/problems`, `/problem/<mã>` (không gồm route con) | L | Lọc phức tạp, sắp xếp "đã giải", quyền theo kỳ thi/tổ chức |
| Bài nộp | `/submissions/`, `/submission/<id>`, `/problem/<mã>/submissions/`, `/user/<tên>/submissions/` | L | Cập nhật trực tiếp (W8), quyền xem mã nguồn |
| Xếp hạng | `/users/`, `/contributors/` | S | |
| Tag | `/tags`, `/tag/<tag>` | S | |
| Trạng thái, runtime, license | `/status/`, `/runtimes/`, `/license/<key>` | S | |
| Hồ sơ | `/user/<tên>`, `/user/<tên>/solved/` | M | Biểu đồ rating/điểm |

### Giai đoạn 2: tương tác của người dùng đăng nhập
| Nhóm | Kích cỡ | Ghi chú |
|---|---|---|
| Xác thực (login, logout, register, activate, password, 2FA, OAuth) | XL | W4; bảo mật cao; có thể giữ trang Django cho OAuth/WebAuthn tới khi có thiết kế riêng |
| Nộp bài (`/problem/<mã>/submit`, resubmit) | L | W7; kiểm tra ngôn ngữ, giới hạn nộp |
| Bình luận (đăng, sửa, vote, ẩn, lịch sử) | L | Xuất hiện ở đề, blog, tag, kỳ thi: làm một lần dùng nhiều nơi |
| Thông báo, ticket | L | Cập nhật trực tiếp; nhiều trạng thái |
| Hồ sơ cá nhân (`/edit/profile/`, đổi giao diện, xuất dữ liệu, API token) | M | |
| Trang chủ `/` | M | Hiện là danh sách blog kèm widget (ranking, kỳ thi, bình luận gần đây): làm sau khi các nguồn dữ liệu có API |

### Giai đoạn 3: kỳ thi
| Nhóm | Kích cỡ | Ghi chú |
|---|---|---|
| Danh sách, chi tiết, lịch (`/contests/`, `/contest/<key>`, `/contests/<năm>/<tháng>/`) | M | iCal giữ Django |
| Tham gia, đăng ký, rời (`/join`, `/register`, `/leave`) | M | Ghi; ảnh hưởng khoá kỳ thi (W12) |
| Bảng điểm (`/ranking/`, `/public_ranking/`, `/official_ranking/`) | XL | `contest-ranking.js` 560 dòng, các `contest_format` khác nhau, cập nhật trực tiếp, hiệu năng với nhiều thí sinh |
| Replay (`/replay/<v>/`) | L | `contest-replay.js` 515 dòng |
| Thống kê, bài trong kỳ thi, nộp bài trong kỳ thi | L | |

### Giai đoạn 4: soạn thảo và quản trị nội dung
| Nhóm | Kích cỡ | Ghi chú |
|---|---|---|
| Đề: tạo, sửa, clone, xoá, loại/nhóm, lời giải (`/problem/<mã>/edit...`) | XL | Biểu mẫu lớn, Markdown, nhiều bảng con |
| Dữ liệu test (`/test_data`, `test_data/init`, diff) | XL | Biểu mẫu động theo tập test, tải zip, tác vụ nền |
| Quản lý bài nộp của đề (rejudge, rescore, xem trước) | L | Tác vụ Celery (`tasks/status`) |
| Import Polygon, cập nhật Polygon | L | Tải tệp, tác vụ nền |
| Kỳ thi: tạo, sửa, clone, thông báo, MOSS, chấm lại | XL | |
| Blog: tạo/sửa/xoá (`/posts/new`, `/post/.../edit`) | M | |
| Tag: tạo, gán (`/tags/create`, `/tag/<tag>/assign`) | S | |
| Tổ chức (34 route) | XL | Danh sách/trang chủ (M), thành viên và yêu cầu (L), tag/hạn mức/sử dụng (M), tạo đề/kỳ thi/bài viết trong tổ chức (tái dùng trang chung) |
| Ticket: tạo, trạng thái, ghi chú | M | |
| `/misc_config/` | S | Trang cấu hình của nhân viên; làm cuối |

### Giai đoạn 5: dọn dẹp
- Gỡ trang Jinja, django-compressor, SCSS cũ, select2 và endpoint dư; bỏ `web_with_fallback`.
- Trang lỗi 404/500 trọn bộ, `flatpages` (cần xác nhận còn dùng), `magazine`, `stats`.
- Chuyển hướng URL cũ nếu có đổi.
- Cập nhật `CI-CD.md`, Docker image backend (không còn build SCSS/compress).

## 6. Mỗi trang xong khi nào (tiêu chí hoàn thành)

1. **Tương đương**: nội dung và thứ tự trùng bản Jinja với cùng người dùng/bộ lọc (so sánh song song).
2. **Quyền**: ma trận quyền của trang được duyệt và đạt (đặc biệt: đề riêng, đề tổ chức, bài nộp, kỳ thi đang diễn ra).
3. **Bản vẽ**: đối chiếu ảnh chụp với bản vẽ đã duyệt (sáng và tối, desktop và mobile).
4. **Trợ năng**: tương phản AA, bàn phím, `prefers-reduced-motion`, không phụ thuộc chỉ màu.
5. **Hiệu năng**: số truy vấn và thời gian phản hồi API không tệ hơn Jinja; không có COUNT toàn bảng ở danh sách lớn; kiểm tra RAM của container `web`.
6. **Vận hành**: đã chạy ở `preview` đủ lâu với người dùng thật; theo dõi log nginx (`us=`) không có lần rơi về Django bất thường; hoàn tác thử thành công.
7. **SEO**: tiêu đề, mô tả, canonical đúng; URL không đổi.

## 7. Quyết định cần bạn đưa ra

1. **i18n**: (a) dùng lại `.po` hiện có bằng cách xuất sang JSON (một nguồn dịch cho cả hai phía), (b) chuyển hẳn sang thư viện i18n của Next.js (ví dụ next-intl, phải nhập lại bản dịch), (c) dịch ở Django, API trả chuỗi đã dịch theo `Accept-Language`. Khuyến nghị (a) trong giai đoạn chuyển tiếp.
2. **Xác thực**: render trang đăng nhập/đăng ký bằng Next.js (cần xử lý `Set-Cookie`, CSRF, redirect OAuth, WebAuthn) hay giữ trang Django cho tới giai đoạn cuối? Khuyến nghị giữ Django cho OAuth/WebAuthn, làm lại phần còn lại.
3. **Trình soạn code**: Monaco (mạnh, nặng) hay CodeMirror (nhẹ). Khuyến nghị CodeMirror vì VPS 2 GB và băng thông người dùng.
4. **Trình soạn Markdown**: viết mới hay tái dùng thư viện; cần giữ 11 loại xem trước và tải ảnh (`martor`).
5. **Phạm vi tính năng**: có những trang ít dùng nào có thể **bỏ** thay vì chuyển (ví dụ `shorteners`, `newsletter`, `magazine`, `flatpages`, một số trang tổ chức)? Dữ liệu từ log nginx (đếm theo route) giúp quyết định; lệnh gợi ý: đếm `$request_uri` đã chuẩn hoá theo nhóm trong 30 ngày.
6. **Thứ tự ưu tiên**: giữ thứ tự theo rủi ro (đọc → tương tác → kỳ thi → soạn thảo → tổ chức), hay ưu tiên theo lưu lượng thật?
7. **Trang chủ**: giữ bố cục hiện tại hay thiết kế lại (cần bản vẽ riêng).
8. **Thời điểm gỡ Jinja**: sau từng nhóm hay một lần ở giai đoạn 5? (giữ lâu hơn thì tốn chi phí duy trì hai giao diện).

## 8. Giao diện mặc định sáng

Đã làm cho `web/` (mặc định sáng, chỉ tối khi chọn; đã kiểm bằng Chromium với hệ điều hành tối). Còn lại khi chuyển trang thật:

- Site Django hiện có `Profile.site_theme` (`light` mặc định | `dark` | `auto`), cookie `site_theme` cho khách (hạn 1 năm) và `POST /set-theme/`. Trong thời gian hai giao diện cùng tồn tại, người dùng sẽ thấy chế độ khác nhau giữa trang Jinja và Next.js nếu hai bên không đồng bộ.
- Đề xuất (W10): `web` đọc cookie `site_theme` (khách) và trường `site_theme` trong `me` (đã đăng nhập); khi người dùng đổi chế độ trên Next.js, gọi `set-theme` để cả hai bên cùng đổi. Có thể thêm lại giá trị `auto` (theo hệ điều hành) vì Django đã có, nhưng mặc định luôn là `light`.
- Cho tới khi W10 xong, hai bên độc lập (khoá `localStorage` riêng, mặc định sáng ở cả hai).

## 9. Rủi ro lớn

| Rủi ro | Giảm thiểu |
|---|---|
| Sai quyền làm lộ đề/bài nộp/dữ liệu kỳ thi | Dùng phương thức quyền của model; ma trận quyền duyệt trước; 404 cho mọi từ chối; xem lại từng serializer |
| Khối lượng rất lớn (254 route, ~110 trang HTML) | Chia nhóm, mỗi nhóm một change, chuyển theo `preview`; bỏ trang ít dùng; tái dùng component và trang chung (bình luận, bảng, biểu mẫu) |
| Biểu mẫu phức tạp (đề, test data, kỳ thi, tổ chức) lệch kiểm tra hợp lệ giữa Django và Next.js | Lỗi theo trường do **server** quyết định; Next.js chỉ hiển thị |
| Hai giao diện cùng tồn tại gây lệch trải nghiệm | Điều hướng/footer giống nhau, đồng bộ theme (W10), giữ URL không đổi |
| Bảng điểm kỳ thi trực tiếp nặng, nhiều định dạng điểm | Làm muộn; đo trên dữ liệu thật; có thể giữ Jinja cho trang này lâu hơn |
| RAM 2 GB khi thêm Node + SSR nhiều trang | Đo dưới tải thật; giới hạn bộ nhớ; cache trang công khai; nâng VPS nếu cần |
| Cloudflare cache HTML sai | `private, no-cache` từ Next.js; theo dõi `cf-cache-status` |
| Mất SEO/URL | Giữ URL, metadata, sitemap Django; chuyển hướng nếu có đổi |
| Phụ thuộc `bridged`/judge giữ nguyên | Không đụng; chỉ đọc kết quả chấm qua API và sự kiện |

## 10. Bước tiếp theo

1. Bạn duyệt kế hoạch này và trả lời mục 7 (nhất là i18n, xác thực, trình soạn code).
2. Duyệt `monorepo-compose-layout` và `api-foundation` (phần nền cho giai đoạn 1).
3. Tôi soạn change cho giai đoạn 1 từng nhóm (blog, đề bài, bài nộp, xếp hạng/tag/trạng thái/hồ sơ), mỗi nhóm kèm bản vẽ và ma trận quyền.
4. Song song: thu thập số liệu lưu lượng theo route từ log nginx production để xếp thứ tự và loại bỏ trang ít dùng.

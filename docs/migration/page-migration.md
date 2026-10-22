# Kế hoạch chuyển toàn bộ trang (ngoài admin) sang Next.js

> Trạng thái: **kế hoạch, đã chốt 4 quyết định (mục 7)**; chưa phải spec. Mỗi giai đoạn và mỗi nhóm trang sẽ có change OpenSpec riêng, bản vẽ được duyệt rồi mới làm (`plan.md`, `CLAUDE.md`).
> Số liệu lấy từ `dmoj/urls.py`, `templates/`, `judge/views/`, `resources/` ngày 2026-10-22. Cú pháp/thư viện chưa tra tài liệu chính thức (Context7 bị chặn); mỗi change phải tra và ghi nguồn.
> Liên quan: `plan.md` (chiến lược), `openspec/changes/monorepo-compose-layout` (định tuyến), `openspec/changes/api-foundation` (API đọc), `docs/design/web-pages.md` (bản vẽ đợt 1), `style.md`.

## 1. Mục tiêu và phạm vi

- Chuyển **mọi trang người dùng thấy** (trừ `/admin/`) sang Next.js, từng nhóm một, có thể thử và hoàn tác từng trang. **Không bỏ trang nào** (quyết định của chủ dự án).
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

**D. Không có trang nào bị bỏ.** Mọi trang người dùng thấy đều được chuyển, kể cả loại ít dùng: `shorteners/*` (5 trang: danh sách, tạo, chi tiết, sửa, xoá), `magazine`, `flatpages`, `stats`, `status`, `runtimes`, `license`, `misc_config`. Hai điểm cần lưu ý:
- App `newsletter` **không được cài** (không có trong `INSTALLED_APPS` lẫn `requirements`; route chỉ được thêm khi app có mặt), nên 20 template `templates/newsletter/` là mã chết, không phải trang đang chạy. Không có gì để chuyển; sẽ xoá ở giai đoạn 5. Nếu bạn định bật newsletter, cần nói để đưa vào kế hoạch.
- Ba route `tasks/success|failure|progress` là điểm thử cho tác vụ Celery, không phải trang cho người dùng; mặc định giữ nguyên ở Django (không chuyển, không xoá) trừ khi bạn muốn khác.

## 4. Phần dùng chung phải có trước (luồng hạ tầng)

Đây là phần quyết định tiến độ: làm trang mà thiếu các mục này sẽ phải làm lại.

| # | Hạng mục | Nội dung | Phụ thuộc vào |
|---|---|---|---|
| W1 | Triển khai và định tuyến | `monorepo-compose-layout`: image `web`, nginx trong repo, preview/live, dự phòng, IP thật | — |
| W2 | API đọc | `api-foundation` (đợt 1) rồi mở rộng theo từng nhóm trang | W1 |
| W3 | API ghi và biểu mẫu | Quy ước ghi: CSRF, lỗi theo từng trường, idempotency, tải lên tệp, throttle. Mô tả biểu mẫu Django thành schema (trường, nhãn, kiểm tra hợp lệ) để Next.js hiển thị đúng lỗi của server | W2 |
| W4 | Xác thực | **Đã chốt** (mục 7.2): Next.js làm trang đăng nhập/đăng xuất/đăng ký/kích hoạt/đổi và đặt lại mật khẩu/2FA TOTP; Django giữ OAuth (chuyển hướng và callback) và các endpoint WebAuthn; giữ session Django (cookie `sessionid`, `csrftoken`); xử lý `Set-Cookie` qua Next.js | W3 |
| W5 | i18n | **Đã chốt: dùng lại `.po` hiện có** (mục 7.1). `vi` mặc định, `en` | W1 |
| W6 | Markdown và nội dung | Hiển thị HTML đã render từ server (đề, blog, bình luận, KaTeX/MathJax), trình soạn Markdown có xem trước (11 loại preview hiện có), tải ảnh lên, tìm người dùng (`@`) | W3 |
| W7 | Trình soạn code | **Đã chốt: Monaco, tự host** (mục 7.3): ánh xạ ngôn ngữ OJ ↔ Monaco, mẫu theo ngôn ngữ, bản nháp trong Zustand, thay Ace; nền cho "chạy thử" ở giai đoạn 6 | W2 |
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
| Đề bài | `/problems/`, `/problem/<mã>` (không gồm route con) | L | Lọc phức tạp, sắp xếp "đã giải", quyền theo kỳ thi/tổ chức |
| Bài nộp | `/submissions/`, `/submission/<id>`, `/problem/<mã>/submissions/`, `/user/<tên>/submissions/` | L | Cập nhật trực tiếp (W8), quyền xem mã nguồn |
| Xếp hạng | `/users/`, `/contributors/` | S | |
| Tag | `/tags`, `/tag/<tag>` | S | |
| Trạng thái, runtime, license, magazine, flatpages | `/status/`, `/runtimes/`, `/license/<key>`, `/magazine/`, trang flatpage | S | Phần lớn đọc đơn giản; flatpages cần xác định đường dẫn thật đang dùng |
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
| Rút gọn liên kết (`/shorteners/`, tạo, chi tiết, sửa, xoá) | S | 5 trang, biểu mẫu đơn giản; tên miền rút gọn riêng vẫn do Django chuyển hướng |
| Thống kê (`/stats/data/all/` và trang dùng) | M | Biểu đồ phía client |

### Giai đoạn 5: dọn dẹp
- Gỡ trang Jinja, django-compressor, SCSS cũ, select2 và endpoint dư; bỏ `web_with_fallback`.
- Trang lỗi 404/500 trọn bộ; xoá mã chết (`templates/newsletter/`, template Jinja đã thay).
- Chuyển hướng URL cũ nếu có đổi.
- Cập nhật `CI-CD.md`, Docker image backend (không còn build SCSS/compress).

### Giai đoạn 6: chạy thử code trực tiếp (kiểu LeetCode)

Đây là **tính năng mới**, không phải chuyển trang: người dùng gõ code, nhập dữ liệu, bấm "Chạy" và thấy kết quả ngay mà không nộp bài. Monaco được chọn để chuẩn bị cho việc này. Hiện chưa có hỗ trợ ở hệ thống (DMOJ chỉ có nộp bài chấm theo bộ test). Cần một change riêng với thiết kế và có thể cần sửa cả `thinkcode-judge-server` (repo khác). Các điểm phải giải quyết:
- Giao thức giữa `bridged` và judge cho một lần chạy tạm với input tuỳ ý (không lưu thành bài nộp, hoặc lưu loại riêng, không tính điểm).
- **Công suất**: production chỉ có 1 judge worker (`CI-CD.md`); chạy thử làm tăng tải, cần hàng đợi/ưu tiên tách khỏi bài nộp chấm điểm, giới hạn tần suất theo người dùng/IP, giới hạn thời gian/bộ nhớ/độ dài xuất.
- An toàn và lạm dụng: cùng sandbox của judge, chặn spam, không lộ test chấm điểm.
- API: `POST` tạo lượt chạy, nhận kết quả qua kênh sự kiện `wsevent` (W8).
- Giao diện: khung input/output cạnh Monaco, trạng thái đang chạy/lỗi biên dịch/hết giờ, chia sẻ với trang nộp bài.

## 6. Mỗi trang xong khi nào (tiêu chí hoàn thành)

1. **Tương đương**: nội dung và thứ tự trùng bản Jinja với cùng người dùng/bộ lọc (so sánh song song).
2. **Quyền**: ma trận quyền của trang được duyệt và đạt (đặc biệt: đề riêng, đề tổ chức, bài nộp, kỳ thi đang diễn ra).
3. **Bản vẽ**: đối chiếu ảnh chụp với bản vẽ đã duyệt (sáng và tối, desktop và mobile).
4. **Trợ năng**: tương phản AA, bàn phím, `prefers-reduced-motion`, không phụ thuộc chỉ màu.
5. **Hiệu năng**: số truy vấn và thời gian phản hồi API không tệ hơn Jinja; không có COUNT toàn bảng ở danh sách lớn; kiểm tra RAM của container `web`.
6. **Vận hành**: đã chạy ở `preview` đủ lâu với người dùng thật; theo dõi log nginx (`us=`) không có lần rơi về Django bất thường; hoàn tác thử thành công.
7. **SEO**: tiêu đề, mô tả, canonical đúng; URL không đổi.

## 7. Quyết định

### Đã chốt (2026-10-22)

**7.1 i18n: dùng lại `.po` hiện có.** Một nguồn dịch cho cả hai phía (`locale/vi`, `locale/en`, ~2 150 chuỗi).
- Cách làm: bước build (CI) xuất `django.po` thành JSON theo ngôn ngữ cho `web/`. Không dịch lại bằng tay.
- Lưu ý kỹ thuật cần giải quyết trong change i18n: chuỗi Django dùng `%(tên)s`, `%s`, `ngettext` (số nhiều), `{% blocktrans %}`; các thư viện ICU của Next.js dùng `{tên}`, nên chuyển đổi tự động có thể sai. Đề xuất hàm `t()` nhỏ trong `web/` đọc trực tiếp danh mục đã xuất, hỗ trợ đúng placeholder và số nhiều của Django, thay vì ép sang ICU.
- Dữ liệu từ server (thông báo lỗi, tên model) dịch ở Django theo ngôn ngữ của yêu cầu (`Accept-Language` hoặc cookie ngôn ngữ, `/i18n/setlang`). `statici18n` đã có sẵn nhưng chỉ chứa chuỗi của miền `djangojs`, không đủ cho các chuỗi trong template.

**7.2 Xác thực.**
- Next.js làm: đăng nhập, đăng xuất, đăng ký, kích hoạt, đổi mật khẩu, đặt lại mật khẩu, 2FA TOTP (bật/tắt/làm mới/mã dự phòng), token API, đổi giao diện.
- Django giữ: OAuth (chuyển hướng tới nhà cung cấp và callback; trang lỗi `/social/error/` có thể chuyển về Next.js), các endpoint WebAuthn (`/2fa/webauthn/*`, Next.js gọi được).
- Session vẫn là cookie `sessionid` của Django, cùng tên miền; thêm endpoint đăng nhập/đăng xuất dạng API (đặt cookie, kiểm tra CSRF) thuộc `W3/W4`. Phải xử lý chuyển hướng `next` và khoá kỳ thi sau khi đăng nhập.

**7.3 Trình soạn code: Monaco, tự host, để chuẩn bị chạy thử trực tiếp.**

Đã thử trong phiên (`monaco-editor` 0.57.0 + `@monaco-editor/react` 4.7.0, hỗ trợ React 19; Next.js 15.5.28 build `standalone`, Chromium thật):
- Chạy được khi tự host tại `/monaco/vs/` (cấu hình `loader.config({ paths: { vs } })`), **không có request ra CDN nào**; hiện highlight C++, gõ tiếng Việt đúng, khởi tạo trong khoảng 1,7 giây trên máy cục bộ.
- Mặc định `@monaco-editor/react` tải từ `cdn.jsdelivr.net`; phải tự host để không phụ thuộc CDN (sự cố, quyền riêng tư, CSP).
- `next/dynamic` với `ssr: false` **không được phép trong Server Component** (Next 15) nên phải bọc trong Client Component.
- Bản chép nguyên `min/vs` nặng 25 MB và trang tải khoảng 5,5 MB (chưa nén) vì kéo cả worker JSON/HTML/CSS/TypeScript không cần cho OJ. Cần cắt gọn: chỉ giữ lõi editor, `editor.worker`, các `basic-languages` mà OJ dùng (c/cpp, java, python, pascal, go, rust, kotlin, csharp, javascript...) và bỏ language service. Mục tiêu và đo lại thuộc change W7.
- Phục vụ tĩnh ở đường dẫn có phiên bản (`/monaco/<phiên bản>/vs/`), `Cache-Control: public, max-age=31536000, immutable`; chỉ nạp khi vào trang cần soạn code (lazy), không nằm trong bundle chung.
- Việc còn lại: ánh xạ `Language` của OJ sang id của Monaco (có thể có ngôn ngữ không được hỗ trợ cú pháp, dùng văn bản thuần), theme sáng/tối theo `style.md`, bản nháp theo từng đề lưu trong Zustand.

**7.4 Không bỏ trang nào.** Mọi trang ngoài admin đều được chuyển (mục 3.D). Hệ quả: số lượng trang tăng thêm các trang nhỏ (rút gọn liên kết, magazine, flatpages, stats), và không có việc "cắt giảm" để giảm khối lượng.

### Còn mở
5. **Thứ tự ưu tiên**: giữ theo rủi ro (đọc → tương tác → kỳ thi → soạn thảo → tổ chức), hay theo lưu lượng thật (cần log nginx)? Vì không bỏ trang nào nên log chỉ dùng để xếp thứ tự.
6. **Trang chủ**: giữ bố cục hiện tại hay thiết kế lại (cần bản vẽ riêng).
7. **Thời điểm gỡ Jinja**: sau từng nhóm hay một lần ở giai đoạn 5.
8. **Chạy thử trực tiếp (giai đoạn 6)**: mức ưu tiên và phạm vi (chỉ chạy với input mẫu hay input tuỳ ý), có sẵn sàng sửa `thinkcode-judge-server` không, có thêm judge worker không.

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

1. Bạn duyệt kế hoạch và trả lời các câu hỏi còn mở (mục 7: 5–8).
2. Duyệt `monorepo-compose-layout` và `api-foundation` (nền cho giai đoạn 1).
3. Tôi soạn các change nền dùng chung đã chốt: i18n (`.po` → JSON, hàm `t()`), xác thực (API đăng nhập + trang), Monaco (tự host, cắt gọn, đo), API ghi và biểu mẫu.
4. Tôi soạn change cho giai đoạn 1 từng nhóm (blog, đề bài, bài nộp, xếp hạng/tag/trạng thái/hồ sơ), mỗi nhóm kèm bản vẽ và ma trận quyền.
5. Song song: thu thập số liệu lưu lượng theo route từ log nginx production để xếp thứ tự.

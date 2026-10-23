# Tasks

## 1. Tra cứu và xác nhận

- [x] 1.1 Tra tài liệu chính thức (Context7 nếu dùng được, nếu không thì trang chính thức + `npm view`) cho thư viện đọc `.po` và `cookies()`/`headers()`/server action của Next 15.5. Ghi URL và ngày tra vào mục "Nguồn" cuối `design.md`. Xong khi mục "Nguồn" có đủ các URL.
- [x] 1.2 Xác nhận `LANGUAGE_COOKIE_NAME` của repo là `django_language` (grep `settings.py`, `local_settings*`) và thứ tự chọn ngôn ngữ của `LocaleMiddleware` Django 4.2 bằng tài liệu chính thức. Xong khi kết quả được ghi vào `design.md`.

## 2. Catalog

- [x] 2.1 Viết `web/scripts/build-catalog` đọc `locale/{en,vi}/LC_MESSAGES/django.po` và `web.po`, ghi `web/src/locales/<lang>.json` (khoá `msgctxt\u0004msgid`, số nhiều là mảng, giữ `Plural-Forms`). Xong khi chạy lệnh sinh ra hai file và số khoá bằng số msgid không rỗng của `.po` (đếm bằng `msgfmt --statistics`).
- [x] 2.2 Thêm bước cắt theo khoá dùng trong `web/src/**` và in danh sách msgid dùng nhưng thiếu trong `.po`. Xong khi một chuỗi thử thiếu trong `.po` xuất hiện trong báo cáo và một chuỗi chỉ dùng ở admin không có trong catalog.
- [x] 2.3 Thêm `npm run i18n:build` và `npm run i18n:check` vào `web/package.json`, nối `i18n:check` vào CI (`.github/workflows`). Xong khi `i18n:check` thất bại khi sửa tay một catalog và qua khi sinh lại.

## 3. Module i18n

- [x] 3.1 Cài `t`, `nt`, `pt`, nội suy `%(name)s`/`%d`/`%s`/`%%` và bộ đánh giá `Plural-Forms` không dùng `eval`. Xong khi `tsc --noEmit` sạch và các ví dụ trong spec cho đúng kết quả khi chạy tay.
- [x] 3.2 Cài `getLocale()` (cookie → `Accept-Language` → `DEFAULT_LOCALE`, mặc định `vi`) và server action đổi ngôn ngữ ghi cookie `django_language`. Xong khi bộ ví dụ `Accept-Language` (`vi-VN`, `en-GB;q=0.5,vi`, `*`, rỗng, `fr`) cho kết quả trùng `LocaleMiddleware` của Django.
- [x] 3.3 `I18nProvider` cho client component, chỉ truyền phần catalog cần. Xong khi trang `/dev` có một client component dịch được và kích thước JSON gửi xuống nhỏ hơn catalog đầy đủ.
- [x] 3.4 Thêm nút đổi ngôn ngữ vào shell (theo `style.md`, đã có chỗ trong navbar) và dùng `t()` cho chuỗi của shell. Xong khi đổi ngôn ngữ ở Next.js rồi mở một trang Jinja trên dev compose thì trang đó cùng ngôn ngữ.

## 4. Đối chiếu

- [ ] 4.1 Trình bày kịch bản kiểm thử chi tiết cho người dùng duyệt (phạm vi: mọi khoá × hai locale, các ca số nhiều và ngữ cảnh, `Accept-Language`). Xong khi người dùng approve. Không viết file `*.test.*`.
- [ ] 4.2 Sau khi được duyệt, chạy script đối chiếu một lần (đặt ngoài repo) so `t`/`nt`/`pt` với `gettext`/`ngettext`/`pgettext` của Django. Xong khi 0 khác biệt và kết quả được ghi vào `design.md`.
- [x] 4.3 Chạy `npm run lint`, `npx tsc --noEmit`, `npm run build` trong `web/`. Xong khi cả ba qua.

## Workflow follow-up

- Sau khi các trang sau dùng i18n xong thì `/opsx:archive`. Việc gỡ template Jinja theo từng trang thực hiện trong change của từng trang.

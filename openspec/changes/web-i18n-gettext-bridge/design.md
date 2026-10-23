# Design

## Context

Xem `proposal.md` - Why. Hiện trạng đã đo trong repo:

- `locale/{en,vi}/LC_MESSAGES/django.po` (en 7280 dòng, vi 9446 dòng), `vi`: 2097 msgid, 44 số nhiều, 5 `msgctxt`, 0 `fuzzy`, header `Plural-Forms: nplurals=1; plural=0;`. Có `djangojs.po` riêng (30 dòng) cho JS cũ, không dùng trong Next.js.
- Template Jinja dùng `_()` 1091 lần và `{% trans %}` 45 lần, rải trong 157 file.
- `settings.py`: `LANGUAGES = [('en'), ('vi')]`, `LANGUAGE_CODE = 'en'`, `LocaleMiddleware` bật, `path('i18n/', include('django.conf.urls.i18n'))` (endpoint `setlang`).
- `openspec/specs/` chưa có spec nào, nên spec ở change này là spec đầu tiên.

Ràng buộc: giai đoạn song song Jinja/Next.js kéo dài nhiều tháng; người dùng chuyển qua lại hai stack phải thấy cùng một ngôn ngữ và cùng một câu chữ.

## Goals / Non-Goals

**Goals:**
- `.po` là nguồn duy nhất; kết quả `t()` trùng gettext của Django.
- Không thêm dịch vụ chạy nền; không gọi mạng lúc render để lấy bản dịch.
- Chuỗi gửi xuống trình duyệt tối thiểu.

**Non-Goals:**
- Không đổi quy trình Crowdin, không đổi `.po`.
- Không dịch nội dung người dùng nhập, không thêm ngôn ngữ thứ ba, không prefix ngôn ngữ trên URL (Django hiện không dùng; giữ URL không đổi để nginx không phải đổi).

## Decisions

1. **Sinh catalog JSON tại build, không đọc `.po` lúc chạy.** Script Node trong `web/scripts/` đọc `.po`, ghi `web/src/locales/generated/<lang>.json` (gitignored, sinh ở `prebuild`/`dev`). Khoá theo quy ước gettext `msgctxt\u0004msgid`; giá trị là chuỗi, hoặc mảng cho số nhiều. Lý do: lúc chạy không cần parser, lỗi `.po` hỏng bị bắt ở build.
   - Phương án khác: đọc `.mo` (đã có sẵn) - nhị phân, thêm một định dạng phải parse; gọi Django API lấy catalog - thêm một lần round trip và phụ thuộc runtime. Bị loại.
   - Thư viện parse `.po` (ứng viên `gettext-parser`): **chưa tra tài liệu**, phải tra qua Context7/trang chính thức và `npm view` trước khi chọn (AGENTS quy tắc "kiến thức có thể sai"; Context7 đang không kết nối trong phiên này).
2. **Cắt catalog theo chuỗi được dùng.** Script quét `web/src/**` tìm lời gọi `t(`/`nt(`/`pt(` với đối số chuỗi literal để tạo danh sách khoá; chỉ khoá đó vào catalog. Bắt buộc dùng literal (lint rule hoặc kiểm tra trong script) để quét tĩnh được. Chuỗi động phải đi qua danh sách khoá khai báo tay ở một file `keys.ts`.
   - Phương án khác: nhúng toàn bộ catalog - 2097 chuỗi, phần lớn là admin, phình bundle client.
3. **Server nạp, client nhận phần cần.** `getLocale()` đọc `cookies()`/`headers()` (Next 15: bất đồng bộ). Server component gọi `t` trực tiếp từ catalog nạp ở server. Client component nhận catalog con qua `I18nProvider` (Zustand không cần cho việc này vì ngôn ngữ cố định theo request). Hệ quả: các trang dùng i18n là dynamic, khớp với `Cache-Control: private, no-cache` đã đặt.
4. **Chọn ngôn ngữ giống Django.** Thứ tự cookie `django_language` → `Accept-Language` (có xử lý `q` và tiền tố như `vi-VN`→`vi`) → ngôn ngữ mặc định. Mặc định phải bằng `LANGUAGE_CODE` của Django: `settings.py` đặt `en` nhưng `dmoj/local_settings.docker.py.example` (file thực sự đóng vào image production) đặt `vi`, nên `web` đọc `DEFAULT_LOCALE` (mặc định `vi`) thay vì cứng `en`. Cookie `django_language` là tên mặc định của `LANGUAGE_COOKIE_NAME`, repo không đổi (đã xác nhận, xem mục Nguồn). Next.js ghi cùng cookie (Path `/`, SameSite Lax, 1 năm) khi người dùng đổi ngôn ngữ, qua server action; không gọi `/i18n/setlang/` để tránh phụ thuộc CSRF của Django.
5. **Plural-Forms.** Đọc `Plural-Forms` từ header, đánh giá bằng một bộ biểu thức nhỏ tự viết (chỉ `n`, số, `== != < > <= >= && || ? : %` và ngoặc), **không** dùng `eval`/`new Function`. Hiện chỉ có hai biểu thức (`en`: `n != 1`, `vi`: `0`); thêm ngôn ngữ mới nếu cần biểu thức khác thì mở rộng bộ này.
6. **Nội suy.** Hỗ trợ `%(name)s`, `%d`, `%s`, `%%`. Thiếu tham số thì giữ nguyên placeholder (không ném lỗi, không trả `undefined`). Không đưa HTML từ chuỗi dịch vào `dangerouslySetInnerHTML`; chuỗi có thẻ HTML phải tách thành đoạn văn bản và phần tử React.
7. **Đối chiếu với Django bằng script dùng một lần**, đặt ngoài repo (theo quy tắc không tự viết file test): với mọi khoá, gọi `django.utils.translation` ở hai locale và so với Node. Kịch bản kiểm thử chi tiết được trình bày trong tasks để người dùng duyệt trước khi chạy.

## Risks / Trade-offs

- [Chuỗi động hoặc ghép chuỗi làm quét tĩnh bỏ sót] → bắt buộc literal, script báo lỗi khi gặp đối số không phải literal, danh sách khoá khai báo tay cho trường hợp ngoại lệ.
- [msgid chưa có trong `.po` vì chưa qua Crowdin] → rơi về msgid tiếng Anh (đúng hành vi spec); script in danh sách msgid thiếu mỗi lần build để bổ sung vào `.po`.
- [Hai bản dịch lệch nhau nếu ai sửa catalog sinh ra] → thư mục sinh ra bị gitignore, build luôn ghi đè.
- [`Accept-Language` phân tích khác Django ở trường hợp biên] → đối chiếu bằng bộ ví dụ (`vi-VN`, `en-GB;q=0.5,vi`, `*`, rỗng) trước khi chấp nhận.
- [Trang dynamic hoá làm tăng tải SSR trên VPS 2GB] → đã nằm trong rủi ro RAM chung của kế hoạch; i18n không thêm bộ nhớ đáng kể (catalog cắt, nạp một lần mỗi tiến trình).

## Migration Plan

1. Thêm script và module i18n vào `web/`, chưa trang nào dùng ngoài trang `/dev`.
2. Các change trang sau dùng `t()` cho mọi chuỗi UI.
3. Rollback: bỏ module khỏi trang; không có thay đổi dữ liệu hay Django nên không cần migration.

## Open Questions

- Tên thư viện đọc `.po` cuối cùng (sau khi tra tài liệu). Không đổi spec hay danh sách task.

## Nguồn (đã tra)

- gettext-parser README (`po.parse`, cấu trúc `translations[context][msgid]`, `msgstr` là mảng, `msgid_plural`) - https://github.com/smhg/gettext-parser/blob/master/README.md, tra 2026-10-23; `npm view gettext-parser`: 10.0.0, MIT.
- Next.js 15.5 `cookies()` là hàm async, đọc trong Server Component, ghi chỉ trong Server Action/Route Handler, dùng nó chuyển route sang dynamic rendering - https://github.com/vercel/next.js/blob/v15.5.0/docs/01-app/03-api-reference/04-functions/cookies.mdx, tra 2026-10-23 (nextjs.org bị proxy chặn nên đọc bản nguồn trên GitHub).
- Next.js 15.5 `headers()` - cùng thư mục docs, tra 2026-10-23.
- Django 4.2 thứ tự chọn ngôn ngữ của `LocaleMiddleware` (tiền tố URL, cookie `LANGUAGE_COOKIE_NAME` mặc định `django_language`, `Accept-Language`, `LANGUAGE_CODE`) - https://github.com/django/django/blob/4.2/docs/topics/i18n/translation.txt, tra 2026-10-23. Session không còn nằm trong thứ tự này.
- Đã xác nhận trong repo: không có `LANGUAGE_COOKIE_NAME` nào được đặt (grep `dmoj/`, `.ci.settings.py`, `local_settings.docker.py.example`), nên tên cookie là `django_language`; `LANGUAGE_CODE` production là `vi`.

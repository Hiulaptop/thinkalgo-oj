## ADDED Requirements

### Requirement: Nguồn bản dịch duy nhất là file .po
Catalog JSON dùng bởi Next.js SHALL được sinh tự động từ `locale/<lang>/LC_MESSAGES/django.po` và SHALL NOT được sửa tay. Không có chuỗi dịch nào được định nghĩa riêng trong mã `web/`.

#### Scenario: Cập nhật bản dịch
- **WHEN** một msgstr trong `locale/vi/LC_MESSAGES/django.po` thay đổi và build catalog được chạy lại
- **THEN** trang Next.js hiển thị chuỗi mới mà không cần sửa mã nguồn `web/`

#### Scenario: Chuỗi chưa có bản dịch
- **WHEN** msgid không tồn tại trong catalog, hoặc msgstr rỗng
- **THEN** `t()` trả về chính msgid tiếng Anh và không ném lỗi

### Requirement: Hàm dịch tương thích gettext
Module i18n SHALL cung cấp `t(msgid, params?)`, `nt(singular, plural, n, params?)` và `pt(context, msgid, params?)` với khoá tra cứu theo quy ước gettext (`msgctxt` + ký tự `\u0004` + `msgid`). Nội suy SHALL hỗ trợ `%(name)s` và `%d`. Dạng số nhiều SHALL được chọn theo `Plural-Forms` trong header của từng file `.po`.

#### Scenario: Số nhiều tiếng Anh
- **WHEN** gọi `nt("%d comment successfully hidden.", "%d comments successfully hidden.", 2)` với locale `en`
- **THEN** kết quả là dạng số nhiều có `%d` được thay bằng 2

#### Scenario: Tiếng Việt chỉ có một dạng
- **WHEN** locale là `vi` (`nplurals=1; plural=0`) và `n` là 1 hoặc 5
- **THEN** cả hai đều dùng `msgstr[0]`

#### Scenario: Có ngữ cảnh
- **WHEN** gọi `pt("contest problem", "%(problem)s in %(contest)s", {problem, contest})`
- **THEN** kết quả dùng bản dịch của đúng msgctxt đó, không lẫn với msgid cùng chữ không có ngữ cảnh

### Requirement: Chọn ngôn ngữ giống Django
Với mỗi request, ngôn ngữ SHALL được chọn theo thứ tự: cookie `django_language` (nếu là ngôn ngữ được hỗ trợ), rồi header `Accept-Language`, rồi `en`. Tập ngôn ngữ hỗ trợ SHALL khớp `LANGUAGES` của Django (`en`, `vi`).

#### Scenario: Cookie thắng Accept-Language
- **WHEN** request có cookie `django_language=vi` và `Accept-Language: en-US`
- **THEN** trang hiển thị tiếng Việt

#### Scenario: Giá trị lạ
- **WHEN** cookie `django_language=fr` hoặc header chỉ chứa ngôn ngữ không hỗ trợ
- **THEN** trang rơi xuống mức kế tiếp và cuối cùng dùng `en`

#### Scenario: Đổi ngôn ngữ
- **WHEN** người dùng chọn ngôn ngữ trên trang Next.js
- **THEN** cookie `django_language` được ghi (Path `/`, SameSite Lax) và trang Jinja tải sau đó cũng hiển thị cùng ngôn ngữ

### Requirement: Giống bản Django cho cùng chuỗi
Với cùng msgid, locale và tham số, kết quả của `t`/`nt`/`pt` SHALL trùng kết quả `gettext`/`ngettext`/`pgettext` của Django.

#### Scenario: Đối chiếu toàn bộ catalog
- **WHEN** chạy đối chiếu trên mọi khoá của catalog cho cả hai locale
- **THEN** không có khoá nào cho kết quả khác Django

### Requirement: Catalog gọn cho client
Catalog đưa xuống trình duyệt SHALL chỉ gồm các chuỗi được mã `web/` tham chiếu. Server component SHALL nạp catalog ở server và không gửi toàn bộ file xuống client.

#### Scenario: Chuỗi của admin không bị gửi
- **WHEN** build catalog cho `web/`
- **THEN** các msgid chỉ dùng ở `judge/admin/` không có trong catalog

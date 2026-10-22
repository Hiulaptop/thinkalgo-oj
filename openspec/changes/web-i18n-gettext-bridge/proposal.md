# Proposal

## Why

Mọi trang Next.js (kế hoạch ở `docs/migration/page-migration.md`) cần hiển thị đúng tiếng Việt/Anh như bản Jinja hiện tại. Bản dịch đang nằm ở `locale/{en,vi}/LC_MESSAGES/django.po` (khoảng 2097 msgid ở bản `vi`, gồm 44 dạng số nhiều và 5 `msgctxt`), được dịch qua Crowdin và dùng chung với Django admin. Nếu viết lại chuỗi bằng tay trong Next.js thì hai nơi sẽ lệch nhau ngay trong giai đoạn hai hệ thống cùng chạy. Cần một cầu nối để `.po` vẫn là nguồn duy nhất, và bản dịch hiển thị trên Next.js giống hệt bản Django cho cùng một người dùng.

## What Changes

- Thêm bước build `po → JSON`: đọc `.po`, ghi catalog JSON cho Next.js. `.po` vẫn là nguồn sự thật, không sửa tay file JSON sinh ra.
- Thêm module i18n trong `web/` với các hàm tương thích gettext: `t`, `nt` (số nhiều), `pt` (có ngữ cảnh `msgctxt`), nội suy `%(name)s` và `%d`.
- Chọn ngôn ngữ cho mỗi request theo đúng thứ tự của Django `LocaleMiddleware`: cookie `django_language` → `Accept-Language` → `en`. Đổi ngôn ngữ ghi cùng cookie đó để hai stack luôn đồng ý.
- Catalog chỉ gồm chuỗi mà mã `web/` dùng thật (cắt bớt chuỗi của admin và backend) để giữ gói client nhỏ.
- Ghi quyết định về việc gỡ Jinja: **gỡ sớm theo từng trang**. Template Jinja của một trang bị xoá ngay sau khi trang Next.js tương ứng chạy ổn trên production vài ngày (mặc định 3 ngày, không có lỗi mới và đã đối chiếu), thay vì chờ cuối lộ trình. Template chỉ bị xoá khi không còn view/route nào khác dùng nó. Việc gỡ thực tế nằm trong change của từng trang, không nằm trong change này.

## Capabilities

### New Capabilities
- `web-i18n`: chọn ngôn ngữ theo request, nạp catalog sinh từ `.po`, và hàm dịch tương thích gettext cho Next.js.

### Modified Capabilities

(Không có. `openspec/specs/` hiện chưa có spec nào.)

## Impact

- Thêm: `web/src/lib/i18n/*`, script build `web/scripts/` (po → JSON), thư mục catalog sinh ra trong `web/`, dependency đọc `.po` (cần tra tài liệu, xem design).
- Không đổi Django, `.po`, hay quy trình Crowdin. Không đổi nginx.
- Hệ quả cho các change sau: mọi chuỗi UI trong `web/` đi qua `t()`; chuỗi mới phải được thêm vào `.po` (Crowdin) thì mới có bản dịch.
- Ngoài phạm vi: dịch nội dung do người dùng/admin nhập (đề bài, blog, tên ngôn ngữ lập trình); bản dịch của Django admin; thêm ngôn ngữ thứ ba.

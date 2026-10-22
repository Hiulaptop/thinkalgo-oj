# Proposal

## Why

Các trang đăng nhập, đăng ký, kích hoạt, đổi/đặt lại mật khẩu và 2FA (TOTP) là cửa vào của mọi trang khác; chưa chuyển chúng thì người dùng vẫn bị đẩy sang giao diện Jinja ở bước nào cũng cần tài khoản. Quyết định đã chốt: Next.js dựng giao diện các trang này, còn Django vẫn là nơi duy nhất xác thực (OAuth và endpoint WebAuthn giữ nguyên ở Django). Hiện Django chỉ có view HTML (`CustomLoginView`, `RegistrationView`, `TOTPView`, ...), chưa có API để Next.js gọi, và trình duyệt cần giữ **cùng một cookie phiên Django** để trang Jinja chưa chuyển vẫn nhận ra người đã đăng nhập.

## What Changes

- Thêm nhóm API `/api/v1/auth/*` trong Django, **dùng lại đúng form và logic của view hiện có** (không viết lại luật xác thực): lấy CSRF, đăng nhập, đăng xuất, đăng ký, kích hoạt, đổi mật khẩu, quên/đặt lại mật khẩu, 2FA TOTP (đăng nhập, bật, làm mới, tắt).
- Trình duyệt gọi các API này trực tiếp (cùng domain, qua nginx) để Django đặt cookie phiên; Next.js không tự giữ hay ký phiên. Bảo vệ CSRF bằng cookie `csrftoken` + header `X-CSRFToken`.
- Dựng các trang Next.js tương ứng theo `style.md` và bản vẽ trong `docs/design/web-auth.md`, giữ nguyên đường dẫn hiện có (`/accounts/login/`, `/accounts/register/`, ...) để link trong email kích hoạt/đặt lại mật khẩu và dấu trang cũ vẫn chạy.
- Giao diện cho WebAuthn (đăng ký khoá, đăng nhập bằng khoá) trong trang 2FA, gọi lại các endpoint `/accounts/2fa/webauthn/*` đã có; không viết lại phía Django.
- Đăng nhập OAuth (Google/Facebook/GitHub) vẫn là liên kết sang `social_django` của Django; các trang nằm giữa pipeline OAuth (`username_select`, `profile_creation`, `oauth`) **chưa chuyển** và được ghi là ngoại lệ còn lại Jinja.
- nginx: chỉ `GET/HEAD` các đường dẫn `/accounts/...` sang Next.js; `POST` vào các đường dẫn đó vẫn về Django (form Jinja cũ còn mở trong tab vẫn gửi được). Template Jinja của từng trang bị gỡ sau khi trang Next.js tương ứng chạy ổn trên production ~3 ngày (theo `web-i18n-gettext-bridge`).

## Capabilities

### New Capabilities
- `web-auth`: đăng nhập/đăng xuất, đăng ký và kích hoạt, đổi và đặt lại mật khẩu, 2FA (TOTP, giao diện WebAuthn) qua API phiên của Django và các trang Next.js.

### Modified Capabilities

(Không có; `openspec/specs/` chưa có spec nào.)

## Impact

- Django: thêm `judge/api/v1/views/auth.py` + serializer/form adapter, route `api/v1/auth/`; không đổi model, không migration; `settings.py` có thể cần cấu hình CSRF/cookie (xem design).
- Next.js: các trang `/accounts/*`, client gọi API phiên, component form theo `style.md`, dùng `t()` của `web-i18n-gettext-bridge` (change này phụ thuộc nó).
- nginx: thêm route cho `/accounts/...` trong `routes/next-owned.conf` (mặc định tắt/preview).
- Ngoài phạm vi: bỏ qua OAuth/WebAuthn phía server, đổi thuật toán băm mật khẩu, chống dò mật khẩu (rate limit) mới, đăng nhập qua API token cho máy khác, trang trong pipeline OAuth.

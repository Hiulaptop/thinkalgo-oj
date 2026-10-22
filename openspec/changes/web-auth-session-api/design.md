# Design

## Context

Xem `proposal.md` - Why. Hiện trạng đã đọc trong repo:

- `dmoj/urls.py`: các đường dẫn auth nằm dưới `accounts/` (`login/`, `logout/`, `register/`, `register/complete/`, `register/closed/`, `password/change/(done/)`, `password/reset/(done|complete|confirm/<uid>-<token>/)`, `2fa/`, `2fa/enable|refresh|disable/`, `2fa/webauthn/attest|assert|delete/<pk>`, `social/error/`); `social_django.urls` ở gốc.
- `AUTHENTICATION_BACKENDS`: Google/Facebook/GitHub OAuth, `ModelBackend`, `IPBasedAuthBackend`. Phiên: `cached_db`. `CSRF_FAILURE_VIEW = judge.views.widgets.csrf_failure`.
- `CustomLoginView` dùng `CustomAuthenticationForm`, sau khi hợp lệ kiểm mật khẩu bằng `PwnedPasswordsValidator` và đặt `session['password_pwned']`.
- `RegistrationView` dùng `CustomRegistrationForm` (reCAPTCHA, email trùng, tên miền bị chặn, tổ chức) và gửi email sau commit.
- `judge/middleware.py` (đã sửa ở `api-foundation`) chặn bằng 403 JSON `two_factor_required` / `password_change_required` cho `/api/v1/`.
- Bước 2FA: `TwoFactorLoginView`, TOTP bật/làm mới/tắt, WebAuthn attest/assert/delete.
- Trang nằm giữa pipeline OAuth: `username_select.html`, `profile_creation.html`, `oauth.html`.

## Goals / Non-Goals

**Goals:**
- Next.js dựng toàn bộ giao diện auth hiện có (trừ trang trong pipeline OAuth) mà Django vẫn là chủ duy nhất của phiên.
- Không đổi luật xác thực; thông điệp lỗi vẫn từ form Django.

**Non-Goals:**
- Không viết lại WebAuthn, OAuth, băm mật khẩu; không thêm rate limit mới (ghi nhận là rủi ro hiện có); không token API cho máy khác.

## Decisions

1. **Trình duyệt gọi thẳng `/api/v1/auth/*` (không qua server action của Next).** Lý do: Django cần tự đặt `Set-Cookie` cho phiên trên domain người dùng; để Next proxy thì phải chuyển tiếp `Set-Cookie` thủ công, dễ lệch thuộc tính (`HttpOnly`, `SameSite`, `Secure`). nginx đã định tuyến `/api/` về Django.
   - Phương án khác: server action + chuyển tiếp cookie - thêm một tầng có thể sai thuộc tính cookie; JWT do Next ký - bỏ phiên Django, buộc trang Jinja mất đăng nhập. Cả hai bị loại.
2. **CSRF kiểu Django, không đổi cơ chế.** `GET /api/v1/auth/csrf` dùng `ensure_csrf_cookie`; client gửi `X-CSRFToken`. DRF `SessionAuthentication` đã kiểm CSRF cho người dùng đã đăng nhập, còn các endpoint chưa đăng nhập (login, register, reset) phải bọc bằng kiểm CSRF tường minh (`csrf_protect`) vì DRF bỏ qua CSRF khi chưa xác thực. Cần xác nhận bằng tài liệu DRF 3.17 và Django 4.2 (chưa tra).
3. **Adapter dùng lại form, không sao chép luật.** View API tạo `CustomAuthenticationForm(request, data=...)`, `CustomRegistrationForm`, `PasswordChangeForm`, `PasswordResetForm`, `TOTPForm`... rồi chuyển `form.errors` thành `fields`. Đổi luật ở form thì cả Jinja và API cùng đổi. Logic hiện nằm trong `form_valid` của view (ví dụ kiểm pwned) được tách thành hàm dùng chung để cả hai cùng gọi, tránh hai bản.
4. **Đăng nhập hai bước = một phiên "đang chờ 2FA".** Giữ đúng cơ chế hiện có của `TwoFactorLoginView`/middleware thay vì tạo cơ chế mới; API trả `two_factor_required` và danh sách phương thức. Chi tiết trạng thái phiên cần đọc kỹ `two_factor.py` và `judge/middleware.py` khi thực hiện (task 1.2).
5. **Đường dẫn giữ nguyên, nginx tách theo phương thức.** `GET/HEAD /accounts/<trang>` → Next.js (dùng `web_with_fallback`), `POST` → Django. Trong thời gian chuyển, form Jinja mở sẵn vẫn gửi được. Sau khi template Jinja của trang bị gỡ, `POST` còn lại vô hại (view Django giữ để trả JSON/redirect, hoặc 405 do chính sách nginx); quyết định cụ thể ghi ở change gỡ Jinja của từng trang.
6. **Email giữ nguyên.** Template email (`activation_email*`, `password_reset_email*`) vẫn do Django render; liên kết trong đó trỏ `/accounts/...` nên tự đi qua nginx tới Next.js khi trang đã chuyển.
7. **Trang trong pipeline OAuth ở lại Jinja** (`username_select`, `profile_creation`, `oauth`) vì pipeline `social_core` dừng giữa chừng, lưu trạng thái ở phiên và render template do Django; chuyển cần thiết kế lại pipeline bán phần thành API. Ghi vào `docs/migration/page-migration.md` như ngoại lệ, sẽ có change riêng. Đây là trường hợp ngoại lệ duy nhất so với "chuyển hết ngoài admin".
8. **reCAPTCHA.** Client dùng widget của Google với site key từ cấu hình; token gửi trong thân đăng ký và kiểm ở server bằng `ReCaptchaField` hiện có. Site key cấp cho Next.js qua biến môi trường của container `web` (khoá bí mật không rời Django). Cần xác nhận cách `judge/utils/recaptcha.py` đang nhận token (task 1.3).

## Risks / Trade-offs

- [Gọi API từ trình duyệt làm lộ bề mặt tấn công mới] → chỉ dùng form hiện có, CSRF bắt buộc, giới hạn phương thức, kiểm `next`, không trả thông tin phân biệt "sai tên" và "sai mật khẩu" hơn view hiện tại.
- [Lệch hành vi giữa API và view Jinja] → tách logic chung; đối chiếu từng kịch bản (đúng/sai mật khẩu, 2FA, pwned, đăng ký, reset) với view cũ trước khi đổi nginx.
- [Không có rate limit] → đã tồn tại ở hệ thống cũ; ghi nhận, đề xuất change riêng, không mở rộng phạm vi.
- [Cookie `SameSite`/`Secure` sau Cloudflare Flexible SSL] → kiểm thực tế `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS` với `X-Forwarded-Proto`, vì Next.js và Django đứng sau cùng nginx.
- [Người dùng có phiên đang mở khi chuyển] → phiên dùng chung nên không bị đăng xuất.

## Migration Plan

1. Thêm API và test thủ công ở dev compose; chưa mở route nginx.
2. Dựng trang Next.js, so với bản Jinja bằng ảnh chụp; mở bằng cookie `web_preview=1`.
3. Bật `GET/HEAD /accounts/<trang>` sang Next.js từng trang. Rollback: xoá một dòng nginx.
4. Sau ~3 ngày ổn định, gỡ template Jinja của trang đó (change nhỏ riêng cho mỗi trang hoặc nhóm trang).

## Open Questions

- Có muốn chặn dò mật khẩu (giới hạn số lần thử) ngay đợt này không? Mặc định: không, làm change riêng.

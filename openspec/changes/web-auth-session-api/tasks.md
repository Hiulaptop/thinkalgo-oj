# Tasks

## 1. Tra cứu và đọc kỹ

- [ ] 1.1 Tra tài liệu chính thức (Django 4.2: CSRF, `ensure_csrf_cookie`, `csrf_protect`, `url_has_allowed_host_and_scheme`, `login`, `PasswordResetForm`; DRF 3.17: `SessionAuthentication` và CSRF; reCAPTCHA v2). Ghi URL và ngày tra vào mục "Nguồn" cuối `design.md`. Xong khi mục "Nguồn" đủ URL.
- [ ] 1.2 Đọc `judge/views/two_factor.py`, `judge/middleware.py`, `judge/ip_auth.py` và ghi vào `design.md` trạng thái phiên chính xác của bước 2FA. Xong khi quyết định 4 được cập nhật bằng sơ đồ trạng thái.
- [ ] 1.3 Đọc `judge/utils/recaptcha.py` và `judge/forms.py` (các form auth); ghi cách nhận token reCAPTCHA và các trường mỗi form. Xong khi bảng trường được thêm vào `design.md`.
- [ ] 1.4 Kiểm cookie/CSRF sau nginx + Cloudflare (`SESSION_COOKIE_*`, `CSRF_*`, `CSRF_TRUSTED_ORIGINS`) trên dev compose. Xong khi `design.md` ghi giá trị cần đặt cho production.

## 2. Bản vẽ (chờ duyệt trước khi làm UI)

- [ ] 2.1 Vẽ `docs/design/web-auth.md`: đăng nhập, đăng ký (+ hoàn tất/đóng), kích hoạt, đổi mật khẩu, quên và đặt lại mật khẩu, 2FA (TOTP + WebAuthn), bật/tắt TOTP; mọi trạng thái lỗi, tải, thành công, cả sáng và tối, theo `style.md`. Xong khi người dùng approve bản vẽ.

## 3. API Django

- [ ] 3.1 Tách logic dùng chung khỏi `form_valid` (kiểm pwned, tạo hồ sơ khi đăng ký) thành hàm dùng bởi cả view Jinja và API. Xong khi view Jinja hoạt động như cũ (thử đăng nhập tay trên dev compose).
- [ ] 3.2 `GET /api/v1/auth/csrf`, `POST login`, `POST logout`, `GET me` (đã có) trả trạng thái phiên và `two_factor_required`/`password_change_required`. Xong khi các tình huống đúng/sai mật khẩu, thiếu CSRF, `next` ngoài site cho kết quả như spec.
- [ ] 3.3 Đăng ký, kích hoạt, trang hoàn tất/đóng. Xong khi email kích hoạt gửi được (backend email console ở dev) và liên kết kích hoạt hoạt động.
- [ ] 3.4 Đổi mật khẩu, quên và đặt lại mật khẩu. Xong khi luồng đầy đủ đổi được mật khẩu và phiên cũ bị xử lý như view hiện tại.
- [ ] 3.5 2FA: đăng nhập TOTP, bật, làm mới, tắt; danh sách phương thức. Xong khi bật rồi đăng nhập lại đòi mã, tắt xong thì không đòi.
- [ ] 3.6 Cập nhật `schema.yml` và `web/src/lib/api/schema.d.ts`. Xong khi `npm run api:types` sạch và `tsc --noEmit` qua.

## 4. Next.js

- [ ] 4.1 Client API phiên chạy trong trình duyệt (lấy CSRF, gửi `X-CSRFToken`, xử lý `fields`, `two_factor_required`). Xong khi gọi thử từ trang `/dev` đăng nhập được trên dev compose.
- [ ] 4.2 Các trang đăng nhập/đăng ký/kích hoạt/mật khẩu/2FA đúng bản vẽ, dùng `t()`, giữ đường dẫn cũ. Xong khi từng trang hiển thị đúng ở sáng/tối, tiếng Việt/Anh.
- [ ] 4.3 Giao diện WebAuthn gọi endpoint hiện có. Xong khi đăng ký và dùng một khoá bảo mật ảo (Chromium virtual authenticator) thành công.
- [ ] 4.4 Chụp ảnh các trang bằng Playwright/Chromium và đối chiếu với bản vẽ, báo kết quả. Xong khi báo cáo đối chiếu được gửi.

## 5. Định tuyến và đối chiếu

- [ ] 5.1 Thêm route `GET/HEAD /accounts/...` vào `deploy/nginx/routes/next-owned.conf` (POST vẫn về Django); kiểm bằng bộ kịch bản nginx. Xong khi `nginx -t` đạt và các kịch bản GET/POST/preview đúng.
- [ ] 5.2 Trình bày kịch bản kiểm thử chi tiết (đăng nhập đúng/sai, khoá, 2FA, pwned, đăng ký các lỗi, kích hoạt hết hạn, reset, CSRF, `next` độc hại, đa ngôn ngữ) để người dùng duyệt; sau đó chạy một lần ngoài repo. Xong khi người dùng approve và kết quả được ghi vào `design.md`. Không viết file `*.test.*`.
- [ ] 5.3 `flake8`, `python manage.py check`, `npm run lint`, `tsc --noEmit`, `npm run build`. Xong khi tất cả qua.

## Workflow follow-up

- Sau ~3 ngày ổn định trên production: gỡ template Jinja `registration/*` đã thay (trừ `username_select`, `profile_creation`, `oauth`, email) trong change riêng, rồi `/opsx:archive`.

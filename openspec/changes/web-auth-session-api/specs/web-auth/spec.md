## ADDED Requirements

### Requirement: Django là nơi duy nhất xác thực và giữ phiên
Mọi thao tác đăng nhập, đăng xuất, đăng ký, đổi/đặt lại mật khẩu và 2FA SHALL do Django thực hiện qua `/api/v1/auth/*` bằng cùng form và validator với view hiện có. Next.js SHALL NOT tự ký, lưu hay giải mã phiên. Phiên SHALL là cookie phiên của Django trên cùng domain để trang Jinja và trang Next.js dùng chung.

#### Scenario: Đăng nhập rồi sang trang Jinja
- **WHEN** người dùng đăng nhập ở trang Next.js rồi mở một trang còn Jinja
- **THEN** trang đó nhận ra người dùng đã đăng nhập

#### Scenario: Luật xác thực không đổi
- **WHEN** nhập sai mật khẩu, tài khoản bị khoá, hoặc đăng nhập bằng IP-based backend theo cấu hình hiện có
- **THEN** kết quả giống view hiện tại cho cùng đầu vào

### Requirement: Bảo vệ CSRF
Mọi API ghi dưới `/api/v1/auth/` SHALL yêu cầu token CSRF hợp lệ qua header `X-CSRFToken`. Có endpoint `GET /api/v1/auth/csrf` đặt cookie `csrftoken`.

#### Scenario: Thiếu token
- **WHEN** gửi `POST /api/v1/auth/login` không có `X-CSRFToken`
- **THEN** phản hồi 403 với `code` là `csrf_failed` và phiên không thay đổi

### Requirement: Lỗi nhất quán và dịch
Lỗi SHALL theo định dạng của `api-foundation` (`{code, detail}`) và với lỗi biểu mẫu thêm `fields` là ánh xạ tên trường tới danh sách thông điệp. Thông điệp SHALL được Django dịch theo ngôn ngữ của request (cookie `django_language`/`Accept-Language`).

#### Scenario: Lỗi trường
- **WHEN** đăng ký với email đã dùng
- **THEN** phản hồi 400, `code` là `validation_error` và `fields.email` chứa thông điệp đúng của form hiện có, bằng ngôn ngữ của request

### Requirement: Chuyển hướng sau đăng nhập an toàn
Tham số `next` SHALL chỉ được chấp nhận khi cùng host (kiểm bằng `url_has_allowed_host_and_scheme`); ngược lại SHALL dùng trang mặc định. API SHALL trả về URL đích, Next.js không tự dựng.

#### Scenario: next ngoài site
- **WHEN** `next=https://evil.example/`
- **THEN** URL đích trả về là trang mặc định

### Requirement: 2FA và buộc đổi mật khẩu
Khi tài khoản bật 2FA, đăng nhập mật khẩu đúng SHALL chưa hoàn tất phiên cho tới khi bước 2FA qua (TOTP hoặc WebAuthn). Khi phiên có `password_pwned`, các API và trang SHALL dẫn người dùng tới đổi mật khẩu, dùng mã `two_factor_required` / `password_change_required` đã có ở middleware.

#### Scenario: Cần mã TOTP
- **WHEN** tài khoản có 2FA nhập đúng mật khẩu
- **THEN** API trả `code: two_factor_required` kèm các phương thức khả dụng (`totp`, `webauthn`), và trang Next.js chuyển sang `/accounts/2fa/`

#### Scenario: Mật khẩu từng lộ
- **WHEN** mật khẩu nằm trong danh sách lộ (kiểm bằng `PwnedPasswordsValidator` như hiện nay)
- **THEN** người dùng được dẫn tới trang đổi mật khẩu trước khi dùng các trang khác

### Requirement: Giữ đường dẫn và liên kết email
Các trang SHALL giữ đường dẫn hiện có (`/accounts/login/`, `/accounts/register/`, `/accounts/register/complete/`, `/accounts/activate/<key>/`, `/accounts/password/change/`, `/accounts/password/reset/`, `/accounts/password/reset/confirm/<uidb64>-<token>/`, `/accounts/2fa/`, ...). Email do Django gửi SHALL tiếp tục chứa liên kết hợp lệ tới các trang này.

#### Scenario: Liên kết kích hoạt cũ
- **WHEN** mở liên kết kích hoạt trong email đã gửi trước khi chuyển
- **THEN** trang Next.js kích hoạt tài khoản qua API và hiển thị kết quả

### Requirement: Đăng ký giữ luật hiện có
Đăng ký SHALL giữ nguyên: cờ `REGISTRATION_OPEN`, reCAPTCHA, kiểm tra email trùng và danh sách tên miền bị chặn, chọn tổ chức, email kích hoạt hết hạn sau `ACCOUNT_ACTIVATION_DAYS`.

#### Scenario: Đóng đăng ký
- **WHEN** `REGISTRATION_OPEN` là false
- **THEN** trang đăng ký hiển thị thông báo đóng như `registration_closed` hiện tại

### Requirement: Đăng nhập OAuth và WebAuthn giữ ở Django
Nút đăng nhập Google/Facebook/GitHub SHALL là liên kết tới endpoint `social_django` hiện có. Giao diện WebAuthn SHALL gọi các endpoint `/accounts/2fa/webauthn/*` hiện có mà không đổi hợp đồng của chúng.

#### Scenario: Đăng nhập Google
- **WHEN** bấm nút Google trên trang đăng nhập Next.js
- **THEN** luồng OAuth chạy ở Django và quay lại site với phiên Django hợp lệ

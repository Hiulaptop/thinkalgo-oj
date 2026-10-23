# Bản vẽ các trang tài khoản (chờ duyệt)

> Trạng thái: **bản vẽ chờ approve** (vẽ trước, duyệt rồi mới làm). Thuộc change `web-auth-session-api`. Tuân thủ `style.md` (Playful Friendly: viền Cocoa dày, bóng đổ cứng, hover rõ; mặc định sáng). Copy tiếng Việt là bản nháp; mỗi chuỗi đi qua `t()` nên có bản `en` tương ứng trong `web.po`. Khung chung (navbar/footer) như `web-pages.md`.

Ký hiệu: `[ ]` nút/ô nhập, `( )` badge, `⟲` đang tải, `✕` lỗi, `✓` thành công.

## Quy ước chung cho mọi biểu mẫu

- **Trang đơn cột**, thẻ (Card nền Cream, viền Cocoa 3px, bóng cứng) rộng tối đa 480px, canh giữa, cách navbar 48px. Tiêu đề Baloo 2 trên đầu thẻ.
- **Ô nhập**: nhãn luôn hiển thị phía trên (không dùng placeholder thay nhãn), cao 48px, viền Cocoa 2px, bo 14px. Focus: vòng focus của `style.md` (dải Cyan + viền ngoài `edge`). Hover: viền đổi Copper, thẻ không nhích.
- **Lỗi theo trường**: viền ô đổi Red (tối: Orange), dưới ô có icon `✕` + câu lỗi (nguyên văn từ Django, đã dịch), ô gắn `aria-invalid` và `aria-describedby`. Khi gửi thất bại, tiêu điểm nhảy vào ô lỗi đầu tiên và có một khối tóm tắt lỗi (viền Red 3px) ở đầu thẻ.
- **Lỗi chung** (sai tài khoản, CSRF hết hạn, mạng): khối viền Red 3px + icon + câu + nút "Thử lại".
- **Nút chính** Amber, chữ Cocoa, rộng 100% thẻ, hover: nảy lên 2px + bóng sâu; khi đang gửi: nút khoá, hiển thị `⟲` và chữ "Đang xử lý…"; không gửi đúp.
- **Hiện/ẩn mật khẩu**: nút con mắt trong ô, có nhãn truy cập "Hiện mật khẩu"/"Ẩn mật khẩu".
- Liên kết phụ (quên mật khẩu, đăng ký) dạng chữ gạch chân Copper, hover đậm hơn.
- **Mobile (<768px)**: thẻ chiếm toàn chiều rộng trừ lề 16px, bỏ bóng đổ lớn (giữ bóng nhỏ), nút cao 52px.
- Giảm chuyển động: tắt nảy/nhích, giữ đổi màu.

## 1. Đăng nhập (`/accounts/login/`)

```
┌ Đăng nhập ─────────────────────────────────────┐
│ Tên đăng nhập  [__________________________]    │
│ Mật khẩu       [______________________] [👁]   │
│ ☐ Ghi nhớ tôi        Quên mật khẩu?            │
│ [          Đăng nhập          ]                │
│ ───────────── hoặc đăng nhập bằng ──────────── │
│ [ G  Google ]  [ f  Facebook ]  [ ⌥  GitHub ]  │
│ Chưa có tài khoản? Đăng ký                     │
└────────────────────────────────────────────────┘
```

- Nút OAuth là liên kết tới `social_django` (tải trang đầy đủ), cao 48px, viền Cocoa 2px, hover: nền Sand + nhích 2px. Chỉ hiện nhà cung cấp được bật trong cấu hình.
- Nếu đã đăng nhập: chuyển hướng tới `next` an toàn hoặc trang chủ.
- `?next=` được giữ qua các bước (2FA, đổi mật khẩu).
- Mật khẩu bị lộ (`password_pwned`): sau khi đăng nhập thành công chuyển thẳng sang mục 6.
- Lỗi thường gặp: "Tên đăng nhập hoặc mật khẩu không đúng" (nguyên văn của form hiện có, hiển thị ở khối lỗi chung, không chỉ ra cái nào sai).

## 2. Xác thực hai bước (`/accounts/2fa/`)

```
┌ Xác thực hai bước ─────────────────────────────┐
│ Nhập mã 6 chữ số từ ứng dụng xác thực của bạn. │
│  [ _ ][ _ ][ _ ][ _ ][ _ ][ _ ]                │
│ [          Xác nhận          ]                 │
│ ───────────────── hoặc ──────────────────────  │
│ [ 🔑 Dùng khoá bảo mật ]  (nếu tài khoản có)   │
│ Đăng xuất                                       │
└────────────────────────────────────────────────┘
```

- Ô mã: một ô nhập `inputmode="numeric"`, `autocomplete="one-time-code"` hiển thị như 6 ô; dán mã tự điền; tự gửi khi đủ 6 số.
- Nút khoá bảo mật gọi `navigator.credentials` qua endpoint WebAuthn hiện có. Trạng thái: chờ thao tác trên thiết bị ("Hãy chạm vào khoá của bạn…" + `⟲`), thất bại ("Không dùng được khoá này, thử lại hoặc nhập mã"), trình duyệt không hỗ trợ (ẩn nút).
- Mã sai: lỗi dưới ô mã, xoá ô, tiêu điểm quay lại ô.

## 3. Đăng ký (`/accounts/register/`) và hoàn tất (`/accounts/register/complete/`)

```
┌ Tạo tài khoản ─────────────────────────────────┐
│ Tên đăng nhập  [____________]                  │
│ Email          [____________]                  │
│ Mật khẩu       [____________] [👁]  (gợi ý độ mạnh) │
│ Nhập lại mật khẩu [_________]                  │
│ Múi giờ [Asia/Ho_Chi_Minh ▾]   Ngôn ngữ [Python ▾] │
│ Tổ chức (tuỳ chọn) [Chọn…     ▾]               │
│ [ reCAPTCHA ]                                  │
│ [          Đăng ký          ]                  │
│ Đã có tài khoản? Đăng nhập                     │
└────────────────────────────────────────────────┘
```

- Trường đúng như `CustomRegistrationForm` hiện có; thứ tự và bắt buộc/tuỳ chọn theo form (danh sách trường chính xác chốt ở task 1.3, sẽ cập nhật bản vẽ nếu form có trường khác).
- Gợi ý độ mạnh mật khẩu chỉ là chữ + thanh màu (Red/Orange/Leaf), không thay luật của Django.
- Hoàn tất: thẻ có icon phong bì, "Đã gửi email kích hoạt tới <email>. Liên kết có hiệu lực <N> ngày." + nút "Về trang chủ".
- Đóng đăng ký (`REGISTRATION_OPEN=false`): thẻ "Hiện chưa mở đăng ký" + nút "Về trang chủ".

## 4. Kích hoạt (`/accounts/activate/<key>/`) và kích hoạt xong

- Mở trang: đang tải (`⟲ Đang kích hoạt…`) rồi một trong ba trạng thái: `✓ Tài khoản đã kích hoạt` + nút "Đăng nhập"; `✕ Liên kết đã hết hạn hoặc không hợp lệ` + giải thích + liên kết "Đăng ký lại"; đã kích hoạt trước đó + nút "Đăng nhập".

## 5. Quên và đặt lại mật khẩu

```
/accounts/password/reset/          /accounts/password/reset/confirm/<uid>-<token>/
┌ Quên mật khẩu ───────────────┐   ┌ Đặt mật khẩu mới ────────────────┐
│ Email [_________________]    │   │ Mật khẩu mới     [__________] [👁] │
│ [ Gửi liên kết đặt lại ]     │   │ Nhập lại         [__________]      │
└──────────────────────────────┘   │ [ Đổi mật khẩu ]                   │
 sau khi gửi: "Nếu email có trong  └────────────────────────────────────┘
 hệ thống, bạn sẽ nhận được thư"   liên kết hết hạn: thẻ lỗi + "Yêu cầu liên kết mới"
```

- Thông báo sau khi gửi luôn giống nhau dù email có tồn tại hay không (không lộ tài khoản).
- Đặt xong: `✓ Đã đổi mật khẩu` + nút "Đăng nhập".

## 6. Đổi mật khẩu (`/accounts/password/change/`)

- Ba ô: mật khẩu hiện tại, mới, nhập lại. Thành công: `✓ Đã đổi mật khẩu` + quay về `next`.
- Chế độ bắt buộc (từ `password_pwned`): khối cảnh báo vàng ở đầu thẻ "Mật khẩu của bạn nằm trong danh sách bị lộ. Hãy đổi mật khẩu để tiếp tục.", không có nút bỏ qua; chỉ cho đổi hoặc đăng xuất.

## 7. Bật/làm mới/tắt TOTP (`/accounts/2fa/enable/`, `/refresh/`, `/disable/`)

```
┌ Bật xác thực hai bước ─────────────────────────┐
│ 1. Quét mã QR bằng ứng dụng xác thực            │
│        [ QR 192×192 ]                           │
│    Hoặc nhập khoá: ABCD EFGH IJKL  [Sao chép]   │
│ 2. Nhập mã 6 chữ số để xác nhận                 │
│    [ _ _ _ _ _ _ ]                              │
│ [          Bật          ]                       │
└────────────────────────────────────────────────┘
```

- QR là ảnh do Django trả (hoặc sinh từ URI `otpauth`), có `alt` mô tả; khoá văn bản để người dùng trình đọc màn hình dùng được.
- Tắt: thẻ xác nhận "Tắt xác thực hai bước làm tài khoản kém an toàn hơn" + ô mã + nút Red "Tắt".
- Các trạng thái lỗi: mã sai, mã hết hạn (hướng dẫn kiểm tra đồng hồ thiết bị).

## 8. Đăng xuất (`/accounts/logout/`)

- Trang xác nhận đơn giản "Bạn đã đăng xuất" + nút "Đăng nhập lại" và "Về trang chủ". Nút Đăng xuất trên navbar gọi API rồi chuyển tới trang này.

## Trạng thái cần chụp để đối chiếu sau khi làm

Mỗi trang ở: mặc định, ô lỗi, đang gửi, thành công; sáng và tối; tiếng Việt và tiếng Anh; desktop 1280px và mobile 390px.

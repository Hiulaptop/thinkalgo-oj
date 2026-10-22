# Bản vẽ các trang đợt 1 (chờ duyệt)

> Trạng thái: **bản vẽ chờ approve** (theo quy trình: vẽ trước, duyệt rồi mới làm). Tuân thủ `style.md` (Playful Friendly: viền Cocoa dày, bóng đổ cứng, hover rõ). Dữ liệu lấy từ `api-foundation`; định tuyến theo `monorepo-compose-layout`. Chưa có bản vẽ cho trang chủ, contest, hồ sơ, tổ chức, ticket (đợt sau). Copy tiếng Việt là bản nháp.

Ký hiệu: `[ ]` nút/ô bấm được, `( )` badge, `▓` thanh nhấn, `⟲` đang tải. Bố cục dưới đây ở màn rộng ≥1024px; mục "Mobile" mô tả khác biệt ở dưới 768px.

## Khung chung (mọi trang)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ (Navbar viên thuốc nổi: logo · Đề bài · Bài nộp · Cuộc thi · Xếp hạng · Blog │ [☾] [Đăng nhập] │
└──────────────────────────────────────────────────────────────────────────┘
   <tiêu đề trang Baloo 2>                       <hành động chính nếu có>
   ───────────────────────────────────────────────
   <nội dung>
┌──────────────────────────────────────────────────────────────────────────┐
│ Footer nền Cocoa, liên kết dạng viên thuốc                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

Trạng thái chung: **đang tải** (khung xương Sand có nhịp nhấp nháy nhẹ, tắt khi giảm chuyển động), **rỗng** (hình minh hoạ + một câu + nút), **lỗi** (khối viền Red 3px, icon + chữ + nút "Thử lại"), **404** (đã có).

## 1. Danh sách đề (`/problems/`)

```
Đề bài                                                     [ Đề ngẫu nhiên ]
┌ Bộ lọc (Card nền Sand) ────────────────────────────────────────────────────┐
│ [🔍 Tìm đề…                              ]  Nhóm [Tất cả ▾]  Điểm [__]–[__]  │
│ Chủ đề: (dp)(đồ thị)(chuỗi)(toán)…  ☐ Ẩn đề đã giải  ☐ Hiện chủ đề  [Áp dụng] │
└───────────────────────────────────────────────────────────────────────────┘
┌ Mã ▾ ─ Tên đề ───────────────── Nhóm ───── Điểm ─ %AC ─ Giải ─ Trạng thái ─┐
│ ▓ AC001  Tổng hai số            Nhập môn    1.0   92%   8 421   (✓ AC)    │
│   SORT02 Sắp xếp                Nhập môn    1.0   71%   5 103             │
│   DP015  Dãy con tăng dài nhất  Quy hoạch   3.0   38%   1 920   (⟲ Đang chấm)│
│   …  (50 dòng / trang)                                                        │
└───────────────────────────────────────────────────────────────────────────┘
                              [‹ Trước]  Trang 2  [Sau ›]     (không hiện tổng)
```

- Cột sắp xếp được bấm vào tiêu đề: cột đang sắp xếp nền Orange + mũi tên. Mặc định: ngày mới nhất.
- Hover hàng: nền đổi, thanh nhấn Amber 6px bên trái, tên nhích phải 4px. Bấm cả hàng mở đề. Hàng đã giải có (✓ AC).
- Bộ lọc là tham số URL (chia sẻ được); tuỳ chọn người dùng (ẩn đề đã giải, hiện chủ đề) lưu ở store phía client và luôn gửi lên.
- Rỗng: "Chưa có đề nào khớp. Thử bỏ bớt bộ lọc nhé!" + nút "Xoá bộ lọc".
- Mobile: bộ lọc thu gọn thành nút "Bộ lọc" mở Sheet; bảng thành danh sách thẻ (mã + tên + badge + điểm).

## 2. Chi tiết đề + nộp bài (`/problem/<mã>`)

```
‹ Quay lại đề bài
AC001 · Tổng hai số                                (✓ Bạn đã giải)
Giới hạn: ⏱ 1 s   🧠 256 MB   Điểm 1.0   Nhóm: Nhập môn   (dp)(toán)
┌ Tabs: [Đề bài]  Bài nộp  Thống kê ────────────────────────────────────────┐
│ ┌ Nội dung đề (nền Cream, chữ 18px, KaTeX) ─────────┐ ┌ Nộp bài ────────┐ │
│ │ Cho hai số nguyên a, b …                           │ │ Ngôn ngữ [C++ ▾] │ │
│ │ ## Input / ## Output                               │ │ [  Soạn code…  ]│ │
│ │ ┌ Ví dụ ──────────────┐ ┌ ───────────────┐        │ │ [ Nộp bài ]      │ │
│ │ │ 3 5     (Sao chép)  │ │ 8              │        │ │ Ngôn ngữ hợp lệ… │ │
│ │ └─────────────────────┘ └────────────────┘        │ └──────────────────┘ │
│ └────────────────────────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────────────────┘
```

- Ví dụ input/output: khối `--font-mono`, nút "Sao chép" (hover: nảy + đổi nền); khối hover có viền Copper.
- Ở đợt 1 **chỉ đọc**: cột "Nộp bài" hiển thị nút dẫn tới trang nộp của Django (`/problem/<mã>/submit`) vì endpoint ghi thuộc change sau; khi có endpoint ghi mới thay bằng khung soạn code tại chỗ.
- Đề đã xoá: trang riêng "Đề này đã bị xoá" (copy theo trang Jinja). Đề không có quyền: 404 chung.
- Mobile: hai cột xếp dọc; "Nộp bài" thành thanh cố định dưới cùng với nút chính.

## 3. Danh sách bài nộp (`/submissions/`)

```
Bài nộp                                   Lọc: [Kết quả ▾] [Ngôn ngữ ▾] [Đề ▾] [Người nộp]
┌ # ──── Thời điểm ─ Người nộp ─ Đề ───────── Kết quả ─── Thời gian ─ Bộ nhớ ─ Ngôn ngữ ┐
│ ▓ 10231  2 phút    nam_vn     Tổng hai số    (✓ AC)      0.02 s    3.1 MB   C++20     │
│   10230  5 phút    lan_it     Dãy con…       (⏱ TLE)     2.00 s    14.8 MB  Python    │
│   10229  9 phút    minh       Đường đi…      (✕ WA 3/10) 0.11 s    9.4 MB   Java      │
│   10228  vừa xong  bạn        Xâu đối xứng   (⟲ Đang chấm…)  -        -       C++20     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

- Cập nhật trực tiếp qua WebSocket `/event/` (giữ nguyên daemon hiện tại): dòng đang chấm tự đổi sang kết quả, badge nảy 1 lần khi đổi (giảm chuyển động: đổi tức thì). Mất kết nối: chuyển sang làm mới định kỳ qua long-poll `/channels/`.
- VerdictBadge luôn có icon + nhãn; hover badge: phóng 1.1, xoay 3°, tooltip giải thích.
- Dòng của chính người xem có thanh nhấn Leaf. Mã nguồn chỉ có link khi được phép.
- Mobile: mỗi bài nộp là một thẻ gọn (đề, kết quả, thời gian).

## 4. Chi tiết bài nộp (`/submission/<id>`)

```
Bài nộp #10229 · Đường đi ngắn nhất                        (✕ WA)  Điểm 30/100
Người nộp: minh · C++20 · 0.11 s · 9.4 MB · 9 phút trước
┌ Kết quả theo nhóm test ──────────────────────────────────────────────────┐
│ Nhóm 1 (30đ)  ✓ 1  ✓ 2  ✓ 3                                              │
│ Nhóm 2 (70đ)  ✓ 4  ✕ 5  ⏱ 6  …                                           │
│ Test 5: sai đáp án · 0.04 s · 8.2 MB      (hiển thị khi được phép xem)      │
└──────────────────────────────────────────────────────────────────────────┘
┌ Mã nguồn (chỉ hiện nếu được phép) ───────────────────────────────────────┐
│ <khối code, nền White, font mono>                          [ Sao chép ]  │
└──────────────────────────────────────────────────────────────────────────┘
```

- Ô test là viên nhỏ có icon + số; hover: nâng 2px + tooltip (thời gian, bộ nhớ, phản hồi).
- Không được xem mã nguồn: khối thay bằng thông báo "Bạn không có quyền xem mã nguồn bài nộp này" (không phải 404 nếu bài nộp vẫn xem được tóm tắt, theo hành vi Jinja).

## 5. Xếp hạng người dùng (`/users/`)

```
Xếp hạng                                          Sắp xếp: [Điểm ▾]   [🔍 Tìm người dùng]
┌ Hạng ─ Người dùng ───────────── Điểm ─ Đã giải ─ Rating ───────────────┐
│ ▓ 1    (avatar) nam_vn  🏅        4 210   512     2 150 (Kiện tướng)    │
│   2    (avatar) lan_it            4 105   498     1 980                 │
│  …                                                                       │
└───────────────────────────────────────────────────────────────────────────┘
```

- Top 3 có huy hiệu (Amber, Sand, Copper) với hiệu ứng hover xoay nhẹ. Màu rating theo bậc (kèm nhãn chữ, không chỉ màu).
- Hover hàng như bảng chung; bấm mở hồ sơ (đợt sau; hiện liên kết sang Django).

## 6. Blog (`/blogs/`, `/post/<id>-<slug>`)

```
Blog
┌ Card bài viết (nâng khi hover) ───────────┐ ┌ ──────────────────────┐
│ Tiêu đề (Baloo 2)                          │ │ …                      │
│ Tóm tắt 2 dòng · tác giả · ngày · 💬 12     │ │                        │
└────────────────────────────────────────────┘ └────────────────────────┘
```

- Lưới thẻ 2 cột (1 cột trên mobile). Trang chi tiết: cột đọc ~720px, mục lục nằm ở cột phụ, bình luận do Django phục vụ cho tới khi có endpoint bình luận (hiển thị liên kết "Xem bình luận").

## Hiệu ứng và trợ năng áp dụng chung

- Mọi hiệu ứng hover theo `style.md`; chỉ trong `@media (hover: hover)`; giảm chuyển động chỉ đổi màu.
- Mọi bảng có `caption` ẩn (cho trình đọc màn hình), tiêu đề cột `scope="col"`; sắp xếp có `aria-sort`.
- Thứ tự Tab: điều hướng → bộ lọc → bảng → phân trang; focus có vòng Cyan + viền `edge`.
- Mọi trạng thái (đúng/sai/đang chấm) có icon và nhãn chữ.
- Dark mode theo `style.md`; kiểm tra lại các bảng ở nền Espresso/Cocoa.

## Việc cần bạn duyệt

1. Bố cục từng trang ở trên (đặc biệt: bộ lọc đề, bảng bài nộp, kết quả theo nhóm test).
2. Đợt 1 chỉ đọc: nộp bài/bình luận vẫn dẫn sang Django cho tới khi có endpoint ghi.
3. Cập nhật trực tiếp danh sách bài nộp giữ daemon `wsevent` hiện tại.
4. Copy tiếng Việt (bản nháp).

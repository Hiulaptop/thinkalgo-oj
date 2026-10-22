# frontend-plan.md — Thiết kế lại frontend ThinkAlgo OJ

> Trạng thái: **bản nháp kế hoạch**, chưa phải spec. Theo quy trình dự án, mỗi giai đoạn cần change OpenSpec, bản vẽ UI được approve rồi mới làm.
> Tên thư viện, cấu hình và cú pháp trong file này viết từ kiến thức chung, **chưa tra tài liệu chính thức** (Context7 không kết nối được). Phải xác nhận trong spec và ghi nguồn + ngày tra.
> Liên quan: `plan.md` (chiến lược chuyển Django → Next.js, kiến trúc, hạ tầng).

## 1. Mục tiêu

- Thiết kế lại toàn bộ giao diện OJ trên **Next.js 15 (App Router) + shadcn/ui + Zustand**, phong cách **Playful Friendly**.
- Mọi component có **hiệu ứng hover rõ, to, bắt mắt**.
- Chuyển dần từng trang theo `plan.md`: trang chưa chuyển vẫn chạy bằng Jinja.

## 2. Xung đột cần quyết định trước: `style.md`

`CLAUDE.md` của repo bắt buộc mọi thay đổi UI phải theo `style.md`. Hiện `style.md` mô tả một design system khác (nền kem, xanh rừng `#1a3300`, vàng highlighter, Bricolage Grotesque, góc bo 6px, ít bóng) và **mâu thuẫn** với palette và phong cách mới.

Đề xuất: change đầu tiên thay thế `style.md` bằng design system mới (xem mục 4–6), được bạn approve. Chưa sửa `style.md` cho đến lúc đó, và cập nhật luôn dòng quy tắc trong `CLAUDE.md` nếu cần.

## 3. Công nghệ

| Vai trò | Lựa chọn | Ghi chú cần xác nhận |
|---|---|---|
| Framework | Next.js 15 (App Router), React 19, TypeScript strict | Server Components là mặc định |
| Style | Tailwind CSS v4 | Token khai báo bằng `@theme` |
| Component | shadcn/ui (mã nguồn copy vào repo, dựa trên Radix) | Xác nhận hỗ trợ Tailwind v4 + React 19 và quy trình `init` |
| State phía client | Zustand | Xem 3.1 |
| Dữ liệu server | Server Components gọi API Django (xem `plan.md`) | Xác nhận có cần thêm thư viện fetch/cache phía client không |
| Icon | lucide-react (đi kèm shadcn) | |
| Font | Tiêu đề bo tròn thân thiện + nội dung dễ đọc, có subset `vietnamese`; code dùng monospace | Ví dụ Baloo 2 + Nunito (đã dùng ở dự án khác), cần chốt |
| Toast | sonner (qua shadcn) | |

### 3.1 Ranh giới của Zustand

Zustand chỉ giữ **state giao diện phía client**, không giữ dữ liệu server.

Nên đặt trong store:
- Theme (sáng/tối), sidebar/menu mobile đóng mở, bộ lọc và sắp xếp đang chọn của danh sách.
- Cài đặt trình soạn code: ngôn ngữ đã chọn, cỡ chữ, bản nháp code theo từng bài (dùng middleware `persist`).
- Trạng thái chấm bài đang theo dõi qua WebSocket (tạm thời, để UI cập nhật tức thì).

Không đặt trong store:
- Danh sách đề, bài nộp, bảng xếp hạng, hồ sơ. Những thứ này lấy ở Server Component hoặc từ API; đặt vào Zustand sẽ sinh bản sao dữ liệu dễ lệch.

Lưu ý với App Router: store phải **tạo theo từng request/provider**, không dùng singleton ở module, để tránh rò state giữa người dùng khi render trên server và lỗi hydration với `persist`. Cần đối chiếu mẫu "Next.js" trong tài liệu Zustand.

## 4. Design tokens

### 4.1 Bảng màu (hex do bạn cung cấp)

| Tên | Hex | Vai trò đề xuất |
|---|---|---|
| Cream | `#FFF1D1` | Nền trang, nền card |
| Sand | `#F9E6A8` | Nền khối phụ, hàng bảng xen kẽ, badge nhẹ |
| Amber | `#F2A900` | **Màu chủ đạo**: nút chính, nhấn |
| Orange | `#FF9100` | Trạng thái hover/active của nút chính, highlight |
| Copper | `#CC6F00` | Viền nhấn, icon, tiêu đề phụ cỡ lớn |
| Cocoa | `#4D2A00` | **Chữ chính**, viền dày, bóng đổ cứng |
| Red | `#DF301C` | Lỗi, nguy hiểm, trạng thái sai |
| Cyan | `#00B7CD` | Thông tin, liên kết/nhấn phụ, trạng thái đang chạy |

### 4.2 Kiểm tra tương phản (tính theo WCAG, tỉ lệ 4.5:1 cho chữ thường, 3:1 cho chữ ≥18px đậm và thành phần UI)

| Chữ trên nền | Tỉ lệ | Kết luận |
|---|---|---|
| Cocoa / Cream | 11.4 | Tốt, dùng cho mọi chữ |
| Cocoa / Sand | 10.3 | Tốt |
| Cocoa / Amber | 6.4 | Tốt: chữ trên nút chính |
| Cocoa / Orange | 5.7 | Tốt: chữ trên nút hover |
| Cocoa / Cyan | 5.3 | Tốt: chữ trên nền cyan |
| White / Red | 4.6 | Đạt: chữ trên nút nguy hiểm |
| Red / Cream | 4.1 | **Chỉ cho chữ lớn/đậm** hoặc icon |
| Copper / Cream | 3.2 | **Không dùng cho chữ thường**; chỉ chữ lớn, icon, viền |
| Cyan / Cream | 2.2 | **Không dùng làm màu chữ** |
| Amber / Cream | 1.8 | **Không dùng làm chữ hay viền duy nhất**; luôn đi cùng viền Cocoa |
| Orange / Cream | 2.0 | Tương tự Amber |

Quy tắc rút ra:
1. Chữ nội dung luôn là **Cocoa** (hoặc White trên Red/Cocoa).
2. Amber, Orange, Cyan chỉ làm **nền** có chữ Cocoa, không làm màu chữ trên nền sáng.
3. Liên kết: Cocoa, gạch chân dày màu Amber; hover đổ nền Amber.
4. Mọi nút/ô nhập có **viền Cocoa 2–3px**, nên ranh giới luôn đủ tương phản dù nền gần màu nhau.
5. Không chỉ dựa vào màu để truyền đạt trạng thái: luôn kèm icon và nhãn chữ.

### 4.3 Lỗ hổng palette: màu "đúng/AC"
Palette không có màu xanh lá, mà online judge cần phân biệt rõ AC / WA / TLE / MLE / RE / CE / đang chấm. Gợi ý ánh xạ và chờ bạn chốt:

| Verdict | Đề xuất | Ghi chú |
|---|---|---|
| AC | Cyan + icon dấu tích | Khác quy ước xanh lá của OJ, người dùng quen DMOJ có thể lạ |
| WA | Red + icon X | |
| TLE / MLE | Orange + icon đồng hồ / bộ nhớ | |
| RE / IR | Copper + icon cảnh báo | |
| CE | Sand + viền Cocoa + icon | |
| Đang chấm | Amber + animation xoay | |

Phương án khác: thêm **một màu xanh lá riêng cho AC** ngoài palette. Cần bạn quyết định (mục 9).

### 4.4 Ánh xạ sang token của shadcn (ý tưởng)
Biến CSS của shadcn (`--background`, `--foreground`, `--primary`, `--accent`, `--destructive`, `--ring`, `--border`...) ánh xạ về palette: `background=Cream`, `foreground=Cocoa`, `primary=Amber` (chữ `Cocoa`), `accent=Sand`, `destructive=Red`, `ring=Cyan`, `border=Cocoa`. Tên biến chính xác phải đối chiếu theo phiên bản shadcn thực tế.

### 4.5 Chế độ tối
Site cũ có theme. Gợi ý: nền **Cocoa** `#4D2A00` với chữ **Cream** (tỉ lệ 11.4), Amber/Orange giữ vai trò nhấn. Làm sau bản sáng, không nằm trong lần chuyển đầu.

## 5. Phong cách Playful Friendly

- **Hình khối:** góc bo lớn (`rounded-2xl` đến `rounded-3xl`), viền Cocoa 2–3px, **bóng đổ cứng lệch** (ví dụ `4px 4px 0 Cocoa`, không làm mờ) giúp cảm giác như sticker/đồ chơi.
- **Chữ:** tiêu đề to, đậm, bo tròn; nội dung dễ đọc; số liệu và code dùng monospace.
- **Minh hoạ:** mascot hoặc hình khối đơn giản cho trạng thái rỗng, lỗi 404/500, màn hình chờ chấm, ăn mừng khi AC.
- **Giọng văn:** thân thiện, ngắn, có biểu cảm (copy tiếng Việt do bạn duyệt trong bản vẽ).
- **Mật độ:** OJ có nhiều bảng dữ liệu, nên playful nằm ở viền, màu và hiệu ứng, không phải khoảng trắng quá rộng. Bảng phải vẫn đọc được 50 dòng trên một màn hình.

## 6. Hiệu ứng hover (đặc tả)

Mục tiêu: rõ, to, bắt mắt, nhưng không làm hỏng khả năng đọc.

| Component | Hover | Active (nhấn) |
|---|---|---|
| Button chính | Nâng lên (`translateY(-3px)`), đổi nền Amber → Orange, bóng cứng dài ra, phóng to ~1.05 | Hạ xuống, bóng cứng biến mất, như nhấn nút vật lý |
| Button phụ/ghost | Đổ nền Sand, viền Cocoa dày hơn, nghiêng nhẹ ±1° | Như trên |
| Card (đề bài, contest, blog) | Nâng ~4–6px, bóng cứng to hơn, viền đổi sang Copper, icon trong card nảy nhẹ | Hạ xuống |
| Hàng bảng (danh sách đề, bài nộp, ranking) | Đổ nền Sand, thanh nhấn Amber dày bên trái, chữ tên đề nhích phải vài px | |
| Badge/verdict | Phóng to 1.1, xoay nhẹ, hiện tooltip giải thích | |
| Liên kết | Nền Amber chạy từ trái sang phải sau chữ | |
| Input/Select | Viền chuyển Copper, bóng cứng xuất hiện | Focus: vòng Cyan + Cocoa dày 3px |
| Navbar item | Nền Sand dạng viên thuốc, icon nảy | Mục đang chọn: nền Amber + viền Cocoa |
| Avatar/Logo | Lắc nhẹ hoặc xoay | |
| Tab, Dropdown item, Pagination | Cùng ngôn ngữ: nền Sand → Amber, nâng/nghiêng | |

Ràng buộc kỹ thuật và trải nghiệm:
- Bọc hover trong `@media (hover: hover)` để thiết bị cảm ứng không bị kẹt trạng thái hover.
- `prefers-reduced-motion`: bỏ chuyển động nâng/xoay/nảy, chỉ giữ đổi màu và viền.
- Chỉ animate `transform` và `opacity` nhiều nhất có thể; với bảng 50+ dòng tránh animate `box-shadow` cho từng dòng (dùng nền + thanh nhấn).
- Thời lượng ngắn (khoảng 150–250ms), easing nảy nhẹ cho card/button; thống nhất bằng token motion.
- Mọi trạng thái hover có tương đương `:focus-visible` cho bàn phím.

## 7. Bản đồ trang và component

### 7.1 Trang (theo thứ tự chuyển dự kiến, thấp rủi ro trước)
Blog → danh sách đề / chi tiết đề (có nộp bài) → ranking người dùng → danh sách bài nộp / chi tiết bài nộp (cập nhật trực tiếp) → contest (danh sách, chi tiết, bảng điểm trực tiếp) → hồ sơ người dùng (biểu đồ rating) → tổ chức, ticket, thông báo → đăng nhập/đăng ký/2FA/cài đặt.
Trang chủ, 404/500 làm cùng đợt đầu để khẳng định phong cách.

### 7.2 Component cần có (khung shadcn + biến thể Playful)
Button, Input, Textarea, Select/Combobox (thay select2), Checkbox/Radio/Switch, Tabs, Card, Badge/VerdictBadge, Table/DataTable (lọc, sắp xếp, phân trang), Pagination, Dialog/Sheet, Dropdown/Popover, Tooltip, Toast, Skeleton, Avatar, Navbar + menu mobile, Footer, Markdown renderer (kèm KaTeX), khung trình soạn code, biểu đồ rating, trạng thái rỗng/lỗi có minh hoạ.

Trình soạn code: **đã chốt Monaco, tự host** (xem `docs/migration/page-migration.md` mục 7.3; đã thử chạy được, cần cắt gọn dung lượng). Thư viện biểu đồ cần quyết định riêng bằng change và tra tài liệu, vì ảnh hưởng dung lượng bundle.

## 8. Lộ trình

| Giai đoạn | Nội dung | Đầu ra cần approve |
|---|---|---|
| 0. Nền tảng thiết kế | Design system mới thay `style.md`: token, hover, verdict, quy tắc tương phản. Bản vẽ (wireframe/mockup) cho: trang chủ, danh sách đề, chi tiết đề + nộp bài, danh sách bài nộp, bảng điểm contest, hồ sơ, mobile | Design system + bản vẽ |
| 1. Bootstrap | `web/` Next.js 15, Tailwind v4, shadcn init, token, font, provider Zustand, layout (navbar/footer) giống bản Jinja trong thời gian cùng tồn tại | Spec |
| 2. Thư viện component | Biến thể Playful cho mọi component ở 7.2; trang gallery nội bộ (ví dụ `/dev/components`) để xem mọi trạng thái hover/focus. Không thêm Storybook trừ khi bạn muốn | Ảnh chụp đối chiếu bản vẽ |
| 3. Chuyển trang | Mỗi trang một change: API (nếu chưa có) → bản vẽ → dựng → đối chiếu → chuyển route nginx | Mỗi trang một lần |
| 4. Hoàn thiện | Chế độ tối, i18n, a11y, hiệu năng, bỏ dần template Jinja | |

Quy trình mỗi trang: spec → bản vẽ → approve → triển khai đúng bản vẽ → chụp màn hình đối chiếu (Playwright/Chromium) → báo kết quả. Chưa viết test tự động nếu chưa được duyệt kịch bản.

## 9. Câu hỏi mở

1. Thay `style.md` bằng design system mới: bạn đồng ý? (mục 2)
2. Màu AC: dùng Cyan, hay thêm một màu xanh lá ngoài palette? (4.3)
3. Font tiêu đề/nội dung: giữ cặp bo tròn ví dụ ở mục 3, hay có font khác?
4. Chế độ tối: cần ngay hay sau? (4.5)
5. Trình soạn code (Monaco/CodeMirror) và thư viện biểu đồ: quyết ở change riêng, bạn có ưu tiên nào không?
6. Dữ liệu phía client: chỉ Server Components + Zustand, hay thêm thư viện fetch phía client (cho cập nhật trực tiếp/phân trang)? (mục 3)
7. Công cụ vẽ bản vẽ: HTML/ASCII trong `docs/design/` hay Figma? (Figma MCP đang không kết nối trong phiên này.)

## 10. Tiêu chí hoàn thành (cho giai đoạn 0–2)

- Design system được approve và thay `style.md`.
- Mọi cặp chữ/nền trong token đạt WCAG AA theo bảng 4.2; không có chữ Amber/Orange/Cyan trên nền sáng.
- Mỗi component trong 7.2 có hover/active/focus-visible đúng bảng mục 6, có biến thể giảm chuyển động và cảm ứng.
- Gallery hiển thị đủ trạng thái, ảnh chụp đối chiếu khớp bản vẽ đã duyệt.

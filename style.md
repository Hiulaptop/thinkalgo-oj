# ThinkAlgo OJ — Style Reference
> playful friendly sticker-book: warm cream paper, thick cocoa outlines, hard offset shadows, and big bouncy hover effects

**Theme:** light mặc định + chế độ tối (xem "Dark mode")

> Trạng thái: **đã được chủ dự án chốt** màu xanh lá (Leaf), font, kích thước và chế độ tối; thay thế design system "Say Briefly" cũ. Palette gốc do chủ dự án cung cấp; **Leaf `#6CC24A` và Espresso `#331B00` là hai màu bổ sung** (xem bên dưới). Cú pháp CSS/Tailwind/shadcn chưa tra tài liệu chính thức; xác nhận trong spec của change bootstrap.

ThinkAlgo OJ nói bằng ngôn ngữ của một cuốn sổ sticker cho dân lập trình: nền giấy kem ấm, mọi thứ được viền bằng nét nâu cacao dày, bóng đổ là khối nâu **cứng, lệch, không mờ** như sticker dán nổi lên trang giấy. Amber là màu hành động; Orange, Sand và Cyan là các màu vui tươi để phản hồi và nhấn. Giao diện phải thân thiện và nghịch ngợm nhưng vẫn là công cụ làm việc: bảng đề, bài nộp, bảng điểm đọc rõ ở mật độ cao.

Quy tắc xuyên suốt: **mọi thứ bấm được đều phản hồi hover thật rõ, thật to** (nâng lên, phóng to, đổi màu, bóng đổ dài ra), và **không bao giờ chỉ dựa vào màu** để truyền đạt trạng thái.

## Tokens — Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Cream | `#FFF1D1` | `--color-cream` | Nền trang, nền card, nền input |
| Sand | `#F9E6A8` | `--color-sand` | Nền khối phụ, hàng bảng xen kẽ/hover, badge nhẹ, nền nút phụ khi hover |
| Amber | `#F2A900` | `--color-amber` | **Màu chủ đạo**: nền nút chính, mục đang chọn, nhấn nổi bật. Chữ trên nền này luôn là Cocoa |
| Orange | `#FF9100` | `--color-orange` | Trạng thái hover/active của nút chính, highlight, cảnh báo nhẹ (TLE/MLE). Chữ trên nền này luôn là Cocoa |
| Copper | `#CC6F00` | `--color-copper` | Viền nhấn khi hover, icon, tiêu đề phụ cỡ lớn (≥24px). **Không dùng làm chữ thường** |
| Cocoa | `#4D2A00` | `--color-cocoa` | **Chữ chính**, viền dày, bóng đổ cứng, icon. Màu "mực" của toàn hệ thống |
| Red | `#DF301C` | `--color-red` | Lỗi, nguy hiểm, WA. Nền nút nguy hiểm với chữ trắng |
| Leaf | `#6CC24A` | `--color-leaf` | **Màu bổ sung**: thành công / AC / đúng. Xanh lá ấm (hue ~103°, bão hoà vừa) cho hợp với tông kem–nâu. Chữ trên nền này luôn là Cocoa; **không dùng làm màu chữ trên nền sáng** |
| Cyan | `#00B7CD` | `--color-cyan` | Thông tin, vòng focus, trạng thái đang xử lý. Chữ trên nền này luôn là Cocoa; **không dùng làm màu chữ trên nền sáng** |
| Espresso | `#331B00` | `--color-espresso` | **Màu bổ sung, chỉ cho chế độ tối**: nền trang tối (Cocoa dùng cho card/khối nổi) |
| White | `#FFFFFF` | `--color-white` | Chỉ cho chữ trên nền Red/Cocoa và vùng cần nổi tuyệt đối (ví dụ khung soạn code) |

### Kiểm tra tương phản (WCAG; chữ thường cần ≥4.5, chữ ≥18px đậm và thành phần UI cần ≥3)

| Chữ trên nền | Tỉ lệ | Dùng |
|---|---|---|
| Cocoa / Cream | 11.4 | Mọi chữ nội dung |
| Cocoa / Sand | 10.3 | Chữ trong khối phụ, hàng hover |
| Cocoa / Amber | 6.4 | Chữ trên nút chính |
| Cocoa / Orange | 5.7 | Chữ trên nút hover/active |
| Cocoa / Leaf | 5.7 | Chữ trên badge AC/thành công |
| Cocoa / Cyan | 5.3 | Chữ trên badge/nền thông tin |
| White / Red | 4.6 | Chữ trên nút nguy hiểm |
| Red / Cream | 4.1 | **Chỉ chữ lớn/đậm hoặc icon**, không dùng cho chữ thường |
| Copper / Cream | 3.2 | **Chỉ chữ ≥24px, icon, viền** |
| Cyan / Cream | 2.2 | **Cấm làm chữ** |
| Leaf / Cream | 2.0 | **Cấm làm chữ**; khi làm nền phải có viền Cocoa |
| Amber / Cream | 1.8 | **Cấm làm chữ**; khi làm nền phải có viền Cocoa |
| Orange / Cream | 2.0 | **Cấm làm chữ**; khi làm nền phải có viền Cocoa |

### Màu trạng thái chấm bài (verdict)

AC dùng **Leaf** (xanh lá), đúng quy ước quen thuộc của online judge. Leaf, Cyan, Amber và Orange có độ sáng gần nhau (tương phản giữa chúng chỉ 1.0–1.3), nên màu **không đủ** để phân biệt, đặc biệt với người mù màu đỏ–lục (Leaf/Red/Orange). Mỗi verdict **luôn** có icon + nhãn chữ. RE/IR dùng nền Cocoa vì Copper với chữ trắng chỉ đạt 3.6:1 (không đủ AA cho chữ nhỏ).

| Verdict | Nền | Chữ | Icon |
|---|---|---|---|
| AC | Leaf | Cocoa | dấu tích |
| WA | Red | White | dấu X |
| TLE / MLE / OLE | Orange | Cocoa | đồng hồ / bộ nhớ |
| RE / IR | Cocoa | Cream (icon Amber) | cảnh báo |
| CE | Sand + viền Cocoa | Cocoa | dấu ngoặc lỗi |
| Đang chấm / Đang chờ | Amber | Cocoa | vòng quay (animation) |
| Partial | Sand + viền Leaf 3px | Cocoa | nửa tròn |

## Tokens — Typography

### Baloo 2 — Tiêu đề và số liệu nổi bật · `--font-heading`
- **Nguồn:** `@fontsource/baloo-2` có subset `vietnamese` (kiểm tra qua npm registry, 2026-10-22)
- **Substitute:** Fredoka, Nunito 800
- **Weights:** 600, 700, 800
- **Role:** Mọi heading (h1–h4), tên trang, số lớn (điểm, rank). Bo tròn, thân thiện, hỗ trợ subset `vietnamese`. Không dùng cho đoạn văn dài.

### Nunito — Nội dung và giao diện · `--font-body`
- **Nguồn:** `@fontsource/nunito` có subset `vietnamese` (kiểm tra qua npm registry, 2026-10-22)
- **Substitute:** system-ui, Segoe UI
- **Weights:** 400, 600, 700, 800
- **Role:** Đoạn văn, đề bài, nhãn, nút, bảng. Hỗ trợ `vietnamese`.

### JetBrains Mono — Code và dữ liệu kỹ thuật · `--font-mono`
- **Nguồn:** `@fontsource/jetbrains-mono` có subset `vietnamese` (kiểm tra qua npm registry, 2026-10-22), nên comment code tiếng Việt hiển thị đúng
- **Substitute:** Roboto Mono, ui-monospace
- **Weights:** 400, 600
- **Role:** Code, input/output mẫu, mã đề, thời gian/bộ nhớ, diff.

### Type Scale

| Role | Family | Weight | Size | Line Height | Token |
|---|---|---|---|---|---|
| micro | body | 700 | 12px | 1.3 | `--text-micro` |
| caption | body | 600 | 14px | 1.5 | `--text-caption` |
| body | body | 400 | 16px | 1.6 | `--text-body` |
| body-lg | body | 400 | 18px | 1.6 | `--text-body-lg` |
| subheading | heading | 700 | 24px | 1.3 | `--text-subheading` |
| heading-sm | heading | 700 | 32px | 1.2 | `--text-heading-sm` |
| heading | heading | 800 | 40px | 1.1 | `--text-heading` |
| display | heading | 800 | 56px | 1.05 | `--text-display` |

Bảng dữ liệu dày dùng `caption` (14px); nội dung đề bài dùng `body` hoặc `body-lg`. Không có letter-spacing đặc biệt.

## Tokens — Spacing & Shapes

**Base unit:** 8px · **Density:** comfortable cho trang nội dung, compact cho bảng.

### Spacing Scale

| Name | Value | Token |
|------|-------|-------|
| 4 | 4px | `--spacing-4` |
| 8 | 8px | `--spacing-8` |
| 12 | 12px | `--spacing-12` |
| 16 | 16px | `--spacing-16` |
| 24 | 24px | `--spacing-24` |
| 32 | 32px | `--spacing-32` |
| 48 | 48px | `--spacing-48` |
| 64 | 64px | `--spacing-64` |

### Border Radius (lớn, tròn trịa)

| Element | Value |
|---------|-------|
| navbar | 9999px (viên thuốc) |
| buttons | 16px |
| inputs | 14px |
| cards | 24px |
| dialogs | 28px |
| tags / badges | 9999px |
| avatar | 9999px |

### Viền

- **Viền chuẩn:** 2px Cocoa cho nút, input, badge, hàng nổi.
- **Viền đậm:** 3px Cocoa cho card, dialog, navbar.
- Không dùng viền xám nhạt. Ranh giới luôn là Cocoa.

### Shadows (bóng đổ cứng, lệch, không mờ)

| Name | Value | Token |
|------|-------|-------|
| hard-sm | `2px 2px 0 0 #4D2A00` | `--shadow-hard-sm` |
| hard-md | `4px 4px 0 0 #4D2A00` | `--shadow-hard-md` |
| hard-lg | `6px 6px 0 0 #4D2A00` | `--shadow-hard-lg` |
| hard-xl | `8px 8px 0 0 #4D2A00` | `--shadow-hard-xl` |
| focus | dải Cyan `0 0 0 3px #00B7CD` kèm viền ngoài 3px màu `edge` (offset 3px) | `--shadow-focus` |

### Motion

| Name | Value | Token |
|------|-------|-------|
| fast | 120ms | `--duration-fast` |
| base | 200ms | `--duration-base` |
| slow | 320ms | `--duration-slow` |
| bounce | `cubic-bezier(0.34, 1.56, 0.64, 1)` | `--ease-bounce` |
| smooth | `cubic-bezier(0.2, 0, 0, 1)` | `--ease-smooth` |

### Layout

- **Page max-width:** 1280px (bảng dữ liệu có thể rộng hơn qua cuộn ngang trên mobile)
- **Section gap:** 48px
- **Card padding:** 24px
- **Element gap:** 16px

## Hover, Active, Focus — quy tắc chung

Mọi phần tử bấm được (nút, link, card, hàng bảng, tab, mục menu, badge, avatar, mục phân trang) **bắt buộc** có hover rõ ràng. Mức hiệu ứng:

- **Lớn (card, nút chính, nút phụ):** nâng lên 3–6px (`translateY`), bóng cứng tăng một bậc (md → lg), phóng to 1.03–1.05, đổi màu nền (Amber → Orange, Cream → Sand), có thể nghiêng ±1°.
- **Trung (mục nav, tab, dropdown, pagination):** nền Sand → Amber dạng viên thuốc, nâng 2px, icon nảy nhẹ.
- **Nhỏ (hàng bảng, link, badge):** hàng bảng đổ Sand + thanh nhấn Amber 6px bên trái + tên nhích phải 4px; link có nền Amber chạy từ trái sang phải sau chữ; badge phóng to 1.1 và xoay nhẹ.
- **Active (đang nhấn):** hạ xuống, bóng cứng về 0, như nhấn nút vật lý.
- **Focus-visible (bàn phím):** mọi hiệu ứng hover có tương đương, cộng vòng focus: dải Cyan 3px bao quanh bởi viền ngoài 3px màu `edge` (Cyan một mình chỉ đạt 2.2:1 trên Cream nên không đủ độ tương phản cho chỉ báo focus).

Bắt buộc:
- Bọc hiệu ứng hover vào `@media (hover: hover)` để thiết bị cảm ứng không bị kẹt trạng thái.
- `@media (prefers-reduced-motion: reduce)`: bỏ nâng/xoay/phóng/nảy, chỉ giữ đổi màu nền và viền đậm hơn.
- Chỉ animate `transform` và `opacity` khi có thể. Với bảng dài (hơn ~30 dòng) không animate `box-shadow` từng dòng; dùng nền + thanh nhấn.
- Thời lượng `--duration-base`; card và nút dùng `--ease-bounce`, phần còn lại `--ease-smooth`.

## Components

### Primary Button
**Role:** Hành động chính (Nộp bài, Đăng nhập, Tham gia contest)

Nền Amber, chữ Cocoa, viền 2px Cocoa, radius 16px, padding 12px 24px (compact 8px 16px), Nunito 800 16px, bóng `--shadow-hard-md`.
- Hover: nền Orange, `translateY(-3px) scale(1.05)`, bóng `--shadow-hard-lg`, `--ease-bounce`.
- Active: `translateY(2px)`, bóng 0.
- Disabled: nền Sand, chữ Cocoa 50%, không bóng, không hover.

### Secondary Button
**Role:** Hành động phụ

Nền Cream, chữ Cocoa, viền 2px Cocoa, bóng `--shadow-hard-sm`.
- Hover: nền Sand, `translateY(-3px)`, `rotate(-1deg)`, bóng `--shadow-hard-md`, viền không đổi (vẫn Cocoa để giữ tương phản).

### Ghost Button
**Role:** Hành động nhẹ trong thanh công cụ

Trong suốt, chữ Cocoa, không viền khi nghỉ.
- Hover: nền Sand, viền 2px Cocoa xuất hiện, bóng `--shadow-hard-sm`, nâng 2px.

### Danger Button
**Role:** Xoá, huỷ, thao tác không hoàn tác

Nền Red, chữ White, viền 2px Cocoa, bóng `--shadow-hard-md`.
- Hover: nâng 3px, phóng 1.05, bóng `--shadow-hard-lg`, rung nhẹ 1 lần (shake) khi reduced-motion tắt.

### Text Link
**Role:** Liên kết trong nội dung

Chữ Cocoa, gạch chân 3px Amber (offset 2px). Không dùng Cyan/Copper làm chữ link.
- Hover: nền Amber lấp đầy sau chữ từ trái sang phải, gạch chân biến mất.

### Input / Select / Textarea
**Role:** Nhập liệu

Nền Cream, chữ Cocoa, viền 2px Cocoa, radius 14px, padding 10px 14px, placeholder Cocoa 60%. Label Nunito 700 14px phía trên.
- Hover: bóng `--shadow-hard-sm`, nền hơi Sand.
- Focus: vòng focus (dải Cyan + viền ngoài `edge` 3px), viền input giữ nguyên.
- Lỗi: viền Red 3px (chế độ tối: viền Orange 3px, vì Red trên Cocoa chỉ đạt 2.8:1), icon + thông báo chữ bên dưới (không chỉ màu).

### Card
**Role:** Đề bài, contest, bài blog, khối thống kê

Nền Cream (hoặc Sand cho khối phụ), viền 3px Cocoa, radius 24px, padding 24px, bóng `--shadow-hard-md`.
- Hover: `translateY(-6px)` và `rotate(-0.5deg)` (xen kẽ ±), bóng `--shadow-hard-xl`, viền chuyển Copper, icon trong card nảy nhẹ.
- Active: hạ về bóng `--shadow-hard-sm`.

### Data Table
**Role:** Danh sách đề, bài nộp, ranking, bảng điểm contest

Header nền Amber, chữ Cocoa Nunito 800 14px, viền dưới 3px Cocoa. Hàng nền Cream, xen kẽ Sand, đường kẻ 2px Cocoa 15% giữa hàng. Chữ 14px, padding 10px 16px. Số, mã đề, thời gian dùng `--font-mono`.
- Hover hàng: nền Sand đậm hơn (Sand → Amber 35%), thanh Amber 6px bên trái, tên đề nhích phải 4px, con trỏ pointer. Không animate bóng từng hàng.
- Sắp xếp: mũi tên + nhãn; cột đang sắp xếp nền Orange.

### Verdict Badge
**Role:** Trạng thái bài nộp (xem bảng verdict)

Pill (9999px), viền 2px Cocoa, Nunito 800 12–14px, icon trước nhãn. Nền/chữ theo bảng verdict.
- Hover: phóng 1.1, xoay ±3°, tooltip giải thích (ví dụ "Quá thời gian trên test 7").
- "Đang chấm": icon quay liên tục; reduced-motion: thay bằng ba chấm tĩnh.

### Navbar
**Role:** Điều hướng chính

Viên thuốc nổi (radius 9999px) nền Cream, viền 3px Cocoa, bóng `--shadow-hard-md`, logo trái, mục giữa, nút đăng nhập/avatar phải. Trên mobile thành menu trượt (Sheet).
- Hover mục: nền Sand dạng viên thuốc, nâng 2px, icon nảy.
- Mục đang chọn: nền Amber, viền 2px Cocoa.

### Tabs
**Role:** Chuyển nội dung (Đề bài / Bài nộp / Thống kê)

Tab dạng viên thuốc, viền 2px Cocoa; tab đang chọn nền Amber, tab khác nền Cream.
- Hover tab: nền Sand, nâng 2px, `rotate(-1deg)`.

### Pagination
**Role:** Phân trang

Ô tròn/bo tròn 40px, viền 2px Cocoa; trang hiện tại nền Amber.
- Hover: nền Sand, phóng 1.15, bóng `--shadow-hard-sm`.

### Dialog / Sheet
**Role:** Hộp thoại, menu mobile

Nền Cream, viền 3px Cocoa, radius 28px, bóng `--shadow-hard-xl`, lớp phủ Cocoa 50%. Xuất hiện với scale từ 0.95 + `--ease-bounce` (reduced-motion: mờ dần). Nút đóng có hover xoay 90°.

### Toast
**Role:** Thông báo ngắn

Nền Cream (thông tin có thanh Cyan, lỗi có thanh Red, thành công có thanh Leaf + dấu tích), viền 3px Cocoa, bóng `--shadow-hard-md`. Luôn có icon và chữ.
- Hover: dừng đếm ngược, nâng 2px.

### Avatar / Logo
**Role:** Nhận diện

Avatar tròn, viền 3px Cocoa. Logo nền Amber với viền Cocoa dày, chữ Baloo 2.
- Hover: lắc nhẹ hoặc xoay ±8° kèm phóng 1.1.

### Code Editor Frame
**Role:** Khung nộp bài

Khung viền 3px Cocoa, radius 24px, thanh trên nền Sand (chọn ngôn ngữ, cỡ chữ, nút Nộp bài), vùng soạn nền White hoặc Cream (theme editor chốt riêng). Chọn thư viện editor ở change riêng.
- Hover thanh công cụ: các nút theo quy tắc Ghost/Primary.

### Empty / Error State
**Role:** Trạng thái rỗng, 404, 500, chờ chấm

Hình minh hoạ đơn giản (mascot hoặc khối hình học bo tròn) trên nền Sand, tiêu đề Baloo 2, một câu thân thiện và một Primary Button. Có thể thêm hiệu ứng nảy khi hover vào hình.

## Do's and Don'ts

### Do
- Dùng **Cocoa cho mọi chữ nội dung** và mọi viền. Chữ trên Red hoặc Cocoa dùng White.
- Dùng Amber làm màu hành động chính; Orange chỉ cho hover/active và trạng thái nhấn.
- Cho mọi phần tử bấm được hiệu ứng hover rõ theo mức ở phần "Hover, Active, Focus".
- Dùng bóng đổ **cứng** lệch từ palette (`--shadow-hard-*`) để tạo chiều sâu.
- Dùng góc bo lớn (16–28px) và viền Cocoa 2–3px nhất quán.
- Kèm **icon và nhãn chữ** cho mọi trạng thái màu (verdict, lỗi, thành công).
- Giữ bảng dữ liệu gọn (14px) và dễ quét; playful nằm ở viền, màu và phản hồi, không làm bảng loãng.
- Hỗ trợ bàn phím: mọi hover có `:focus-visible` tương đương.

### Don't
- Không dùng Amber, Orange, Leaf, Cyan, Copper làm màu chữ thường trên nền Cream/Sand (không đạt tương phản).
- Không dùng bóng mờ (blur) hay đen/xám trung tính. Không dùng viền xám nhạt.
- Không dùng màu đỏ để truyền đạt lỗi mà không có icon/nhãn; không dùng Leaf/Red phân biệt AC/WA mà không có icon.
- Không để hiệu ứng hover làm dịch bố cục (layout shift): chỉ `transform`, không đổi `width`/`height`/`padding`.
- Không bật hover trên thiết bị cảm ứng; không bỏ `prefers-reduced-motion`.
- Không animate `box-shadow` từng dòng trong bảng dài.
- Không thêm màu chủ đạo thứ hai ngoài Amber; không đưa màu mới vào palette mà không cập nhật file này.
- Không dùng Baloo 2 cho đoạn văn dài hoặc bảng.

## Surfaces

| Level | Name | Value | Purpose |
|-------|------|-------|---------|
| 1 | Cream | `#FFF1D1` | Nền trang, card, input |
| 2 | Sand | `#F9E6A8` | Khối phụ, hàng xen kẽ, thanh công cụ |
| 3 | Amber | `#F2A900` | Header bảng, mục đang chọn, nút chính |
| 4 | Cocoa | `#4D2A00` | Thanh nhấn mạnh, footer; khối nổi trong chế độ tối |
| 5 | Espresso | `#331B00` | Nền trang chế độ tối |

## Elevation

Chiều sâu bằng **bóng đổ cứng**, không bằng blur.

- **Mặc định:** nút `--shadow-hard-md`, card `--shadow-hard-md`, input không bóng.
- **Hover:** tăng một bậc (md → lg, card → xl) kèm nâng lên cùng khoảng.
- **Active:** về `0` hoặc `--shadow-hard-sm` kèm hạ xuống.
- **Dialog/Navbar nổi:** `--shadow-hard-xl` hoặc `--shadow-hard-md`.

## Imagery

Hình ảnh vui, đơn giản, bo tròn: mascot và khối hình học (tròn, tam giác, sao) tô phẳng bằng palette, có viền Cocoa dày cho cảm giác sticker. Dùng cho trạng thái rỗng, lỗi 404/500, màn hình chờ chấm, ăn mừng khi AC (confetti bằng màu palette; reduced-motion: ảnh tĩnh). Không dùng ảnh stock hay 3D render. Icon dạng nét tròn đầu (lucide-react, nét 2px, màu Cocoa), nhãn chữ đi kèm khi mang nghĩa.

## Layout

Trang rộng tối đa 1280px, căn giữa, lề hai bên ≥16px trên mobile. Trang nội dung (đề bài, blog) một cột đọc ~720–800px kèm cột phụ (thông tin, tab). Trang danh sách (đề, bài nộp, ranking) dùng Data Table rộng toàn khổ với bộ lọc dạng thẻ phía trên. Navbar viên thuốc nổi ở đầu trang; footer nền Cocoa chữ Cream. Khoảng cách giữa các khối 48px, trong khối 16–24px. Trên mobile: bảng cuộn ngang hoặc chuyển thành danh sách thẻ, navbar thành menu trượt, vùng chạm ≥44px.

## Dark mode

Chế độ tối được chốt. **Mặc định luôn là chế độ sáng**, không theo `prefers-color-scheme`; chỉ vào chế độ tối khi người dùng chủ động chọn (lưu trong store giao diện và `localStorage`).

| Vai trò | Sáng | Tối |
|---|---|---|
| Nền trang | Cream `#FFF1D1` | Espresso `#331B00` |
| Khối nổi (card, dialog, navbar, input) | Cream | Cocoa `#4D2A00` |
| Khối phụ / hàng xen kẽ | Sand `#F9E6A8` | Espresso đậm hơn nền khoảng 8% hoặc Cocoa 60% |
| Chữ | Cocoa | Cream |
| Viền | Cocoa | Cream (2–3px) |
| Bóng đổ cứng | Cocoa | `#1F1000` (tối hơn nền); viền Cream giữ vai trò tách khối |
| Nút chính | Amber, chữ Cocoa | Giữ nguyên (Amber, chữ Cocoa) |
| Hover nút chính | Orange | Orange (giữ nguyên) |
| Hover hàng/mục nav | Sand | Cocoa sáng hơn: Amber 18% trên Cocoa |
| Vòng focus | Cyan ngoài viền Cream | Cyan ngoài viền Espresso |

Tương phản đã kiểm tra trong chế độ tối (chữ thường cần ≥4.5):

| Chữ trên nền | Trên Espresso | Trên Cocoa | Dùng |
|---|---|---|---|
| Cream | 14.5 | 11.4 | Chữ nội dung |
| Sand | 13.0 | 10.3 | Chữ phụ nhấn |
| Amber | 8.1 | 6.4 | **Được phép** làm màu chữ/link trong chế độ tối |
| Orange | 7.2 | 5.7 | Được phép |
| Leaf | 7.3 | 5.7 | Được phép (chữ thành công/AC) |
| Cyan | 6.7 | 5.3 | Được phép (link thông tin) |
| Copper | 4.5 | 3.6 | Chỉ icon và chữ lớn |
| Red | 3.5 | 2.8 | **Chỉ chữ lớn/đậm hoặc icon**; thông báo lỗi dùng chữ Cream kèm icon/thanh Red |

Quy tắc riêng cho chế độ tối:
- Link: Cream gạch chân 3px Amber (hoặc Amber nếu cần nổi), hover đổ nền Amber chữ Cocoa.
- Nút nguy hiểm vẫn nền Red chữ White, viền Cream.
- Badge verdict giữ nền và chữ như chế độ sáng (đã đạt tương phản), thêm viền Cream 2px.
- Hiệu ứng hover giữ nguyên, nhưng "nâng" thể hiện bằng viền Cream và bóng `#1F1000` kèm đổi sáng nền, vì bóng tối trên nền tối khó thấy.
- Mọi component phải được kiểm tra lại ở cả hai chế độ trước khi coi là hoàn thành.

## Agent Prompt Guide

**Quick Color Reference**
- text: #4D2A00 (Cocoa)
- background: #FFF1D1 (Cream)
- surface phụ: #F9E6A8 (Sand)
- primary action: #F2A900 (Amber), hover #FF9100 (Orange)
- border: #4D2A00 (Cocoa)
- danger: #DF301C (Red), chữ trắng
- success/AC: #6CC24A (Leaf)
- info/focus ring: #00B7CD (Cyan)
- nền tối: #331B00 (Espresso), khối nổi trong chế độ tối #4D2A00 (Cocoa)
- accent icon/large text: #CC6F00 (Copper)

**Example Component Prompts**

1. Primary button: nền #F2A900, chữ #4D2A00 Nunito 800 16px, viền 2px #4D2A00, radius 16px, padding 12px 24px, bóng `4px 4px 0 0 #4D2A00`. Hover (trong `@media (hover:hover)`): nền #FF9100, `transform: translateY(-3px) scale(1.05)`, bóng `6px 6px 0 0 #4D2A00`, transition 200ms `cubic-bezier(0.34,1.56,0.64,1)`. Active: `translateY(2px)`, bóng none. Reduced motion: chỉ đổi màu nền.

2. Problem card: nền #FFF1D1, viền 3px #4D2A00, radius 24px, padding 24px, bóng `4px 4px 0 0 #4D2A00`. Mã đề JetBrains Mono 14px, tên đề Baloo 2 700 24px, badge độ khó pill. Hover: `translateY(-6px) rotate(-0.5deg)`, bóng `8px 8px 0 0 #4D2A00`, viền #CC6F00.

3. Verdict badge AC: pill, nền #6CC24A, chữ #4D2A00 Nunito 800 14px, viền 2px #4D2A00, icon dấu tích trước chữ "AC". Hover: scale 1.1, rotate 3°, tooltip.

4. Data table row: nền #FFF1D1 (xen kẽ #F9E6A8), chữ 14px Nunito, mã đề mono. Hover: nền #F9E6A8 đậm hơn, thanh #F2A900 rộng 6px bên trái, tên nhích phải 4px, không animate shadow.

5. Navbar: viên thuốc nổi, nền #FFF1D1, viền 3px #4D2A00, bóng `4px 4px 0 0 #4D2A00`. Mục đang chọn nền #F2A900 viền 2px #4D2A00; hover mục nền #F9E6A8, nâng 2px.

## Quick Start

### CSS Custom Properties

```css
:root {
  /* Colors */
  --color-cream: #FFF1D1;
  --color-sand: #F9E6A8;
  --color-amber: #F2A900;
  --color-orange: #FF9100;
  --color-copper: #CC6F00;
  --color-cocoa: #4D2A00;
  --color-red: #DF301C;
  --color-leaf: #6CC24A;
  --color-cyan: #00B7CD;
  --color-espresso: #331B00;
  --color-white: #FFFFFF;

  /* Typography — Families */
  --font-heading: 'Baloo 2', ui-rounded, system-ui, sans-serif;
  --font-body: 'Nunito', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  /* Typography — Scale */
  --text-micro: 12px;
  --text-caption: 14px;
  --text-body: 16px;
  --text-body-lg: 18px;
  --text-subheading: 24px;
  --text-heading-sm: 32px;
  --text-heading: 40px;
  --text-display: 56px;

  /* Spacing */
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-24: 24px;
  --spacing-32: 32px;
  --spacing-48: 48px;
  --spacing-64: 64px;

  /* Layout */
  --page-max-width: 1280px;
  --section-gap: 48px;
  --card-padding: 24px;
  --element-gap: 16px;

  /* Border Radius */
  --radius-button: 16px;
  --radius-input: 14px;
  --radius-card: 24px;
  --radius-dialog: 28px;
  --radius-full: 9999px;

  /* Borders */
  --border-width: 2px;
  --border-width-thick: 3px;

  /* Shadows (hard offset); --shadow-color đổi ở chế độ tối */
  --shadow-color: #4D2A00;
  --shadow-hard-sm: 2px 2px 0 0 var(--shadow-color, #4D2A00);
  --shadow-hard-md: 4px 4px 0 0 var(--shadow-color, #4D2A00);
  --shadow-hard-lg: 6px 6px 0 0 var(--shadow-color, #4D2A00);
  --shadow-hard-xl: 8px 8px 0 0 var(--shadow-color, #4D2A00);
  --shadow-focus: 0 0 0 3px #00B7CD; /* dùng cùng outline 3px var(--edge), offset 3px */

  /* Motion */
  --duration-fast: 120ms;
  --duration-base: 200ms;
  --duration-slow: 320ms;
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-smooth: cubic-bezier(0.2, 0, 0, 1);
}

/* Chế độ tối: ghi đè token ngữ nghĩa (tên biến cần đối chiếu với shadcn) */
:root[data-theme="dark"] {
  --background: var(--color-espresso);
  --surface: var(--color-cocoa);
  --foreground: var(--color-cream);
  --border-color: var(--color-cream);
  --shadow-color: #1F1000;
}

/* Mẫu hover: chỉ trên thiết bị có hover, và tôn trọng giảm chuyển động */
.btn-primary { transition: transform var(--duration-base) var(--ease-bounce),
                           box-shadow var(--duration-base) var(--ease-bounce),
                           background-color var(--duration-base) var(--ease-smooth); }
@media (hover: hover) {
  .btn-primary:hover { background-color: var(--color-orange); box-shadow: var(--shadow-hard-lg); }
}
@media (hover: hover) and (prefers-reduced-motion: no-preference) {
  .btn-primary:hover { transform: translateY(-3px) scale(1.05); }
  .btn-primary:active { transform: translateY(2px); box-shadow: none; }
}
```

### Tailwind v4

```css
@theme {
  /* Colors */
  --color-cream: #FFF1D1;
  --color-sand: #F9E6A8;
  --color-amber: #F2A900;
  --color-orange: #FF9100;
  --color-copper: #CC6F00;
  --color-cocoa: #4D2A00;
  --color-red: #DF301C;
  --color-leaf: #6CC24A;
  --color-cyan: #00B7CD;
  --color-espresso: #331B00;

  /* Typography */
  --font-heading: 'Baloo 2', ui-rounded, system-ui, sans-serif;
  --font-body: 'Nunito', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  /* Border Radius */
  --radius-button: 16px;
  --radius-input: 14px;
  --radius-card: 24px;
  --radius-dialog: 28px;

  /* Shadows */
  --shadow-hard-sm: 2px 2px 0 0 var(--shadow-color, #4D2A00);
  --shadow-hard-md: 4px 4px 0 0 var(--shadow-color, #4D2A00);
  --shadow-hard-lg: 6px 6px 0 0 var(--shadow-color, #4D2A00);
  --shadow-hard-xl: 8px 8px 0 0 var(--shadow-color, #4D2A00);
  --shadow-focus: 0 0 0 3px #00B7CD; /* dùng cùng outline 3px var(--edge), offset 3px */

  /* Motion */
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-smooth: cubic-bezier(0.2, 0, 0, 1);
}
```

Ánh xạ sang biến của shadcn/ui (tên biến chính xác phải đối chiếu theo phiên bản shadcn dùng): `background=Cream`, `foreground=Cocoa`, `primary=Amber` (chữ `primary-foreground=Cocoa`), `secondary=Sand`, `accent=Sand`, `destructive=Red` (chữ White), `border=Cocoa`, `input=Cocoa`, `ring=Cyan`. Chế độ tối: `background=Espresso`, `card/popover=Cocoa`, `foreground=Cream`, `border=Cream`, `primary` giữ Amber (chữ Cocoa).

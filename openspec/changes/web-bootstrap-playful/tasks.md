# Tasks

## 1. Khởi tạo ứng dụng web

- [x] 1.1 Tạo `web/` (Next.js 15.5, React 19, TypeScript 5 strict, Tailwind v4, ESLint) và xác nhận `npm run build` chạy được với trang trống
- [x] 1.2 Thêm dependency: zustand, lucide-react, class-variance-authority, clsx, tailwind-merge, `@radix-ui/react-slot`, `-tabs`, `-label`, `@fontsource-variable/{nunito,baloo-2,jetbrains-mono}`; xác nhận `npm ls` không lỗi peer
- [x] 1.3 Thêm `components.json`, alias `@/*`, hàm `cn`; xác nhận `tsc --noEmit` sạch

## 2. Design tokens và chế độ màu

- [x] 2.1 Hiện thực token từ `style.md` (màu, font, bo góc, bóng đổ cứng, motion) trong `globals.css` với `@theme` và biến ngữ nghĩa; xác nhận bằng ảnh chụp trang gallery thấy đúng màu hex
- [x] 2.2 Nạp font Vietnamese (latin, latin-ext, vietnamese) và xác nhận chữ có dấu hiển thị đúng bằng ảnh chụp
- [x] 2.3 Thêm script chặn chọn chế độ và store Zustand tạo theo provider (theme, menu mobile); xác nhận không có cảnh báo hydration ở console và không nhấp nháy khi tải ở chế độ tối
- [x] 2.4 Viết script kiểm tra tương phản WCAG cho mọi cặp chữ/nền ở hai chế độ (đặt ngoài repo, chạy một lần); xác nhận mọi cặp dùng cho chữ thường ≥4.5

## 3. Component nền tảng

- [x] 3.1 Button (primary, secondary, ghost, danger; vô hiệu) với hover/active/focus theo `style.md`; xác nhận bằng gallery và ảnh chụp trạng thái hover
- [x] 3.2 Card, Badge, Input, Label, Table, Tabs theo `style.md` (hàng bảng hover: nền + thanh nhấn, không animate bóng); xác nhận bằng gallery
- [x] 3.3 VerdictBadge với đủ trạng thái, icon + nhãn chữ, trạng thái không rõ; xác nhận bằng gallery
- [x] 3.4 Lớp tiện ích hover bọc `@media (hover: hover)` và `prefers-reduced-motion`; xác nhận bằng ảnh chụp với `reducedMotion` bật và thiết bị cảm ứng giả lập

## 4. Vỏ ứng dụng và trang

- [x] 4.1 Navbar viên thuốc (desktop + menu mobile bàn phím được, mục đang chọn `aria-current`) và Footer; xác nhận bằng ảnh chụp 1280px và 375px, không cuộn ngang
- [x] 4.2 Nút chuyển chế độ sáng/tối có nhãn trợ năng; xác nhận đổi chế độ và khôi phục sau tải lại
- [x] 4.3 Trang chủ tạm (render server) và trang 404; xác nhận nội dung chính có trong HTML tải về khi không chạy JS
- [x] 4.4 Trang `/dev/components` ẩn ở production; xác nhận `next build && next start` trả 404 cho đường dẫn này

## 5. Đối chiếu và hoàn tất

- [x] 5.1 Chạy `npm run lint`, `npx tsc --noEmit`, `npm run build` trong `web/` và xác nhận không lỗi
- [x] 5.2 Chụp ảnh gallery và vỏ ứng dụng (sáng/tối, desktop/mobile) đối chiếu `style.md`, ghi kết quả vào `web/README.md` cùng hướng dẫn chạy
- [x] 5.3 Kiểm tra đối chiếu tài liệu: ghi rõ trong `web/README.md` những phần chưa được xác nhận bằng tài liệu chính thức (shadcn, Zustand)

## Workflow follow-up

- Review và approve; sau đó lưu trữ change (`/opsx:archive`).
- Change tiếp theo: `monorepo-compose-layout`, `api-foundation` (xem `plan.md`).

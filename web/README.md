# ThinkAlgo OJ — web (Next.js)

Frontend mới của ThinkAlgo OJ, chạy **cạnh** Django và chuyển dần từng trang (xem `../plan.md`, `../frontend-plan.md`).
Hiện mới có nền tảng: design system, component, vỏ ứng dụng. **Chưa** gọi API Django, chưa nhận traffic.

Design system: [`../style.md`](../style.md) (nguồn sự thật cho màu, font, hover, chế độ tối).
Change OpenSpec: `../openspec/changes/web-bootstrap-playful/`.

## Chạy

```bash
cd web
npm install
npm run dev        # http://localhost:3000, thư viện component ở /dev/components
npm run lint
npx tsc --noEmit
npm run build && npm start
```

`/dev/components` chỉ có ở môi trường phát triển; ở bản production trả 404.

## Cấu trúc

- `src/app/` route, `globals.css` (token từ `style.md`, chế độ sáng/tối)
- `src/components/ui/` component nền tảng (theo mô hình shadcn/ui: mã nguồn thuộc repo)
- `src/components/shell/` Navbar, Footer, nút chuyển chế độ
- `src/stores/ui-store.ts` + `components/providers/ui-store-provider.tsx` state giao diện (Zustand, tạo theo provider)

## Kết quả đối chiếu với `style.md` (2026-10-22)

Kiểm bằng Chromium (Playwright) trên dev server, ảnh chụp ở sáng/tối × desktop 1280px / mobile 375px:

- Không có cuộn ngang ở cả 12 tổ hợp (gallery, trang chủ, 404 × sáng/tối × desktop/mobile).
- Hover nút chính: nâng 3px, phóng 1.05, nền Orange, bóng 6px; nhấn: hạ 2px, bóng về 0. Card tương tác: nâng 6px, nghiêng -0.5°, bóng 8px, viền Copper. VerdictBadge: phóng 1.1, xoay 3°. Hàng bảng: nền đổi + thanh Amber 6px.
- `prefers-reduced-motion`: không còn dịch chuyển/xoay/phóng; vẫn đổi màu nền và bóng. Spinner "đang chấm" đứng yên.
- Thiết bị cảm ứng: `(hover: hover)` là false nên hiệu ứng hover không áp dụng.
- Focus bàn phím: viền ngoài 3px màu `edge` + dải Cyan 3px.
- Chế độ tối theo hệ điều hành: `data-theme="dark"` đã được đặt trước khi vẽ (không nhấp nháy); đổi tay được lưu qua `localStorage`.
- Tắt JavaScript: tiêu đề và liên kết điều hướng vẫn có trong HTML.
- Font có subset `vietnamese` được tải thật (Nunito, Baloo 2, JetBrains Mono).
- Tương phản: mọi cặp chữ/nền được dùng đạt ≥4.5:1 (chữ) hoặc ≥3:1 (thành phần UI) ở cả hai chế độ, sau khi sửa ba điểm lệch so với `style.md` ban đầu (xem bên dưới).

### Điểm lệch so với `style.md` ban đầu đã sửa trong `style.md`
1. Vòng focus: Cyan trên Cream chỉ 2.2:1, nên thêm viền ngoài 3px màu `edge`.
2. Verdict RE/IR: Copper + chữ trắng chỉ 3.6:1, đổi sang nền Cocoa chữ Cream.
3. Viền ô nhập lỗi ở chế độ tối: Red trên Cocoa 2.8:1, đổi sang Orange (vẫn có icon + nhãn chữ).

## Chưa được xác nhận bằng tài liệu chính thức

Trong phiên làm việc, `ui.shadcn.com` và tài liệu Zustand bị proxy chặn, Context7 không kết nối. Vì vậy:
- Component shadcn được viết tay theo mô hình đã biết (không chạy `shadcn init`/`add`); cần đối chiếu với tài liệu/registry khi truy cập được.
- Zustand: chữ ký `createStore` (`zustand/vanilla`) và `useStore` được kiểm tra từ type của gói đã cài (5.0.16), không từ tài liệu; mẫu "store theo provider" cho Next.js chưa đối chiếu tài liệu.
- Tailwind v4: cú pháp `@theme`, `@theme inline`, `@utility` kiểm tra bằng build thật (4.3.3), chưa đối chiếu tài liệu.

## Việc chưa làm
- First Load JS khoảng 340 kB cho trang chủ (chưa phân tích nguyên nhân); xem xét sau.
- Không có file test tự động (theo cách làm việc của dự án); kiểm chứng bằng lint, tsc, build và ảnh chụp.
- Docker/compose/nginx/CI cho `web/` thuộc change `monorepo-compose-layout`.

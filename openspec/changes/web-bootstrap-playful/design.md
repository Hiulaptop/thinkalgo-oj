# Design

## Context

Xem `proposal.md` cho lý do. Hiện trạng liên quan:
- Repo là Django (VNOJ/DMOJ fork) ở thư mục gốc; chưa có mã Node cho frontend (chỉ `package.json` của `websocket/` và build SCSS).
- `style.md` đã được thay bằng design system Playful Friendly (token, hover, verdict, chế độ tối) và là nguồn sự thật duy nhất cho UI (`CLAUDE.md`).
- `plan.md` quyết định: Next.js chạy cạnh Django, chuyển dần; hạ tầng (compose, nginx, CI) thuộc change khác.
- Môi trường phát triển hiện tại không truy cập được `ui.shadcn.com` và tài liệu Zustand (proxy chặn), Context7 không kết nối. Chỉ npm registry dùng được.

## Goals / Non-Goals

**Goals:**
- Một ứng dụng Next.js chạy được độc lập (`npm run dev/build/start` trong `web/`), đúng `style.md` ở cả hai chế độ.
- Bộ component nền tảng đủ để dựng các trang đầu (danh sách đề, chi tiết đề, bài nộp) ở change sau.
- Có thể đối chiếu bản vẽ bằng ảnh chụp từ `/dev/components`.

**Non-Goals:**
- Không gọi API Django, không auth, không i18n, không trang OJ thật.
- Không đụng Dockerfile, compose, nginx, CI (change `monorepo-compose-layout`).
- Không chọn trình soạn code (Monaco/CodeMirror) hay thư viện biểu đồ.
- Không viết file test tự động (xem Decisions).

## Decisions

1. **`web/` là package độc lập**, có `package.json` và lockfile riêng, chưa dùng npm workspaces. Lý do: repo gốc là Django với `package.json` riêng cho websocket; workspaces sẽ buộc đổi cả hai. Thay thế: monorepo workspaces ngay (để dành khi có `packages/ui` dùng chung).

2. **Next.js 15.5.x (pin `^15.5`), React 19, TypeScript 5 (pin `^5`), Tailwind CSS v4 qua `@tailwindcss/postcss`.** TypeScript 7 đã phát hành nhưng chưa được xác nhận tương thích Next 15.5, nên pin 5.x. Version xác nhận qua npm registry ngày 2026-10-22.

3. **shadcn/ui theo mô hình "mã nguồn thuộc repo"**: component viết trong `web/src/components/ui/`, hàm `cn` (clsx + tailwind-merge), biến thể bằng class-variance-authority, nền Radix (`@radix-ui/react-slot`, `-tabs`, `-label`). Có `components.json` để sau này có thể dùng CLI `shadcn`. Vì không truy cập được registry/tài liệu, component được viết tay theo mô hình đã biết, **chưa đối chiếu tài liệu chính thức**; phải đối chiếu khi có mạng tới tài liệu hoặc Context7. Thay thế: chạy `shadcn init` (bị chặn), thư viện UI khác (mất mô hình sở hữu mã).

4. **Token ở `globals.css`**: khối `@theme` cho token tĩnh (màu palette, font, bo góc, motion), biến ngữ nghĩa (`--background`, `--foreground`, `--surface`, `--border-color`, `--shadow-color`...) đổi giá trị theo `[data-theme="dark"]`. Component dùng biến ngữ nghĩa nên không cần `dark:` ở từng nơi. Tên token và giá trị lấy nguyên từ `style.md`.

5. **Font bằng `@fontsource-variable/*`** (Nunito, Baloo 2, JetBrains Mono), import đúng subset `latin`, `latin-ext`, `vietnamese`. Không dùng `next/font/google` vì cần tải từ Google lúc build. Kiểm tra gói có subset vietnamese qua npm registry (2026-10-22).

6. **Chế độ sáng/tối**: script nội tuyến chặn trong `<head>` đọc `localStorage` (khoá `thinkalgo-theme`) hoặc `prefers-color-scheme` và đặt `data-theme` trước khi vẽ, tránh nhấp nháy; `<html>` có `suppressHydrationWarning`. Store Zustand giữ giá trị `theme` (`system|light|dark`) và khi đổi thì ghi `localStorage` + `data-theme`. Thay thế: `next-themes` (thêm dependency, che giấu logic); chọn tự viết vì ngắn và store Zustand vẫn cần là nguồn state.

7. **Zustand 5 theo mẫu tạo store theo từng provider/request**: `createStore` (vanilla) trong factory, đặt vào React context ở client provider, hook `useUiStore(selector)` dùng `useStore`. Không singleton ở module (tránh rò state khi SSR). Store chỉ chứa state giao diện. API `createStore`/`useStore` sẽ được xác nhận bằng cách kiểm tra gói đã cài (README/types) vì tài liệu web bị chặn.

8. **Hiệu ứng hover bằng CSS thuần/Tailwind** theo `style.md`, bọc trong `@media (hover: hover)` và `@media (prefers-reduced-motion: no-preference)` qua các class tiện ích dùng chung (ví dụ `.lift`, `.press`). Chỉ animate `transform`, `opacity`, màu; bóng đổ chuyển bằng đổi giá trị bóng của phần tử đơn lẻ, không áp cho từng hàng bảng.

9. **Cổng production cho `/dev/components`**: route gọi `notFound()` khi `process.env.NODE_ENV === 'production'`.

10. **Không viết test tự động trong change này**, theo cách làm việc của chủ dự án (chỉ test khi được yêu cầu và duyệt kịch bản). Kiểm chứng bằng: `eslint`, `tsc --noEmit`, `next build`, kiểm tra tương phản bằng script tính WCAG, và ảnh chụp Playwright/Chromium (script tạm ngoài repo) ở hai chế độ, desktop và mobile.

## Risks / Trade-offs

- [Component viết tay lệch so với shadcn chính thức] → Giữ cấu trúc/tên chuẩn (`ui/`, `cn`, `components.json`), đối chiếu tài liệu khi truy cập được, ghi rõ trong tasks.
- [Zustand/Next API sai vì chưa đọc tài liệu web] → Kiểm tra type/README của gói đã cài, `tsc` và `next build` bắt lỗi chữ ký API; chạy thật bằng dev server.
- [Nhấp nháy chế độ màu / hydration mismatch] → Script chặn trước khi vẽ + `suppressHydrationWarning`; kiểm tra bằng ảnh chụp lúc tải ở chế độ tối.
- [Palette: hover bằng bóng đổ gây nặng khi bảng dài] → Hàng bảng chỉ đổi nền và thanh nhấn (không animate bóng).
- [Màu chữ không đạt tương phản ở một chế độ] → Script kiểm tra mọi cặp chữ/nền dùng trong token ở cả hai chế độ, chạy trong lúc triển khai.
- [Hai package.json trong repo (gốc và `web/`) gây nhầm lẫn] → Ghi rõ trong `web/README.md`; xem xét workspaces ở change hạ tầng.

## Migration Plan

Chỉ thêm thư mục mới, không ảnh hưởng production. Rollback: xoá `web/`. Chưa triển khai (không compose/nginx).

## Open Questions

- Logo/mascot: dùng chữ + biểu tượng tạm; thiết kế thật do chủ dự án cung cấp sau.
- Copy tiếng Việt của trang chủ tạm và 404 là nội dung tạm, cần chủ dự án duyệt khi làm trang thật.

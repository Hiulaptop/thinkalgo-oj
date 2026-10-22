# Proposal

## Why

Frontend hiện tại là 238 template Jinja2 cùng SCSS/JS rời rạc, khó bảo trì và không thể dùng chung component. Theo `plan.md` và `frontend-plan.md`, cần một frontend Next.js mới chạy song song, chuyển dần từng trang. Trước khi chuyển bất kỳ trang nào phải có nền tảng: ứng dụng Next.js, design system Playful Friendly (`style.md`) ở dạng token và component, và một vỏ ứng dụng (navbar, footer, chế độ sáng/tối).

## What Changes

- Thêm ứng dụng `web/` (Next.js 15, App Router, TypeScript strict, Tailwind CSS v4) nằm cạnh Django, **chưa nhận traffic**.
- Hiện thực token màu, font, bo góc, bóng đổ cứng và motion của `style.md` thành CSS variables và theme Tailwind v4, có cả chế độ sáng và tối.
- Thêm bộ component nền tảng theo mô hình shadcn/ui (mã nguồn nằm trong repo): Button, Card, Badge, VerdictBadge, Input, Label, Table, Tabs, kèm hiệu ứng hover/active/focus theo `style.md`.
- Thêm vỏ ứng dụng: Navbar viên thuốc, Footer, nút chuyển chế độ sáng/tối, trang chủ tạm và trang 404.
- Thêm store Zustand cho state giao diện (theme, menu mobile) theo mẫu tạo store theo từng request.
- Thêm trang thư viện nội bộ `/dev/components` để xem mọi component ở mọi trạng thái, dùng cho việc đối chiếu bản vẽ.
- Không thay đổi Django, nginx, compose, CI hay bất kỳ trang OJ nào.

## Capabilities

### New Capabilities
- `web-design-system`: token thiết kế, chế độ sáng/tối, hành vi tương tác (hover/active/focus, giảm chuyển động, cảm ứng), tương phản và hiển thị trạng thái chấm bài (verdict) của các component dùng chung.
- `web-app-shell`: vỏ ứng dụng frontend mới (điều hướng, chân trang, chuyển chế độ, trang lỗi) và state giao diện phía client.

### Modified Capabilities

(không có)

## Impact

- Thư mục mới `web/` (mã nguồn Next.js, cấu hình, font, component). Không đụng mã Django.
- Dependency mới trong `web/package.json`: Next.js 15.5, React 19, Tailwind CSS v4, Zustand, lucide-react, class-variance-authority, clsx, tailwind-merge, Radix primitives (slot, tabs, label).
- Phụ thuộc `style.md` (đã thay bằng design system Playful Friendly) và `CLAUDE.md` (mọi UI đi qua `style.md`).
- Chưa có thay đổi hạ tầng: Dockerfile, compose, nginx và CI cho `web/` thuộc change riêng (`monorepo-compose-layout` trong `plan.md`).

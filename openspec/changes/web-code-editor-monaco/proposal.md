# Proposal

## Why

Trang nộp bài hiện dùng Ace (`AceWidget`, `ACE_URL`, `templates/problem/submit-js.html`), gắn chặt với Jinja và jQuery. Khi chuyển trang sang Next.js cần một trình soạn mã tái sử dụng được ở nhiều nơi (nộp bài, xem mã nguồn, ticket, bình luận, hồ sơ). Quyết định đã chốt: dùng **Monaco** (tự host) để về sau có thể chạy thử mã kiểu LeetCode. Change này chỉ làm thành phần trình soạn thảo và cách chọn ngôn ngữ/chủ đề; chưa làm trang nộp bài và chưa làm chạy thử mã.

## What Changes

- Thêm thành phần `CodeEditor` (soạn) và `CodeViewer` (chỉ đọc, dùng cho xem mã nguồn bài nộp) bọc Monaco, tải bằng `next/dynamic` với `ssr: false` trong wrapper client.
- **Tự host** Monaco (không tải từ CDN): worker và tài nguyên phục vụ từ `/_next/static` của `web`, chỉ gồm các ngôn ngữ cần thiết để giảm kích thước.
- Ánh xạ ngôn ngữ chấm bài sang ngôn ngữ Monaco, dựa trên trường `Language.ace` và `Language.key` đã có; API ngôn ngữ trả thêm dữ liệu cần (mẫu mã `template`, `extension`, `file_only`, giới hạn file).
- Chủ đề soạn mã theo giao diện sáng/tối của `ui-store` (Zustand) và nhớ lựa chọn của người dùng; thay cho `ace_theme` của Jinja ở phía Next.js.
- Bản nháp mã theo (bài, ngôn ngữ) lưu cục bộ trong trình duyệt bằng Zustand + localStorage, không gửi lên server.
- Tuân thủ truy cập: điều khiển bằng bàn phím, thoát khỏi trình soạn bằng bàn phím, nhãn cho trình đọc màn hình, tôn trọng `prefers-reduced-motion`.

## Capabilities

### New Capabilities
- `web-code-editor`: thành phần soạn và xem mã nguồn dùng Monaco tự host, ánh xạ ngôn ngữ, chủ đề và bản nháp cục bộ.

### Modified Capabilities

(Không có; `openspec/specs/` chưa có spec nào.)

## Impact

- `web/`: dependency `monaco-editor` và `@monaco-editor/react` (đã ghim ở bước trước: 0.57.0 / 4.7.0, cần xác nhận lại bằng tài liệu), cấu hình webpack/Turbopack cho worker, component `src/components/code/*`, store bản nháp.
- Django: bổ sung trường vào API ngôn ngữ (`/api/v1/problem-filters` hoặc endpoint ngôn ngữ riêng, chi tiết ở design); không đổi model.
- Kích thước tải: Monaco nặng; chỉ tải khi trang có trình soạn, và có ngân sách kích thước ghi trong design.
- Ngoài phạm vi: trang nộp bài (nằm trong change của trang đề bài), chạy thử mã, tự động hoàn thành/LSP, Scratch (ngôn ngữ chỉ nhận file).

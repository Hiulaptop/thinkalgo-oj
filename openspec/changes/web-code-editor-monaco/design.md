# Design

## Context

Xem `proposal.md` - Why. Hiện trạng đã đọc:

- `ProblemSubmitForm.source` dùng `AceWidget(theme='twilight', no_ace_media=True)`; `templates/problem/submit-js.html` đặt mode theo `data-ace` của lựa chọn ngôn ngữ, nạp `template`, đo chiều cao theo cửa sổ, nạp file vào editor.
- `Language` có `ace` (tên mode Ace), `pygments`, `template`, `extension`, `file_only`, `file_size_limit`, `key`.
- `Profile.ace_theme` (có `auto`) và `resolved_ace_theme`; phía Next.js dùng `ui-store` (sáng mặc định, tối chọn tay).
- `web/` đã có Zustand 5 (`createStore` từ `zustand/vanilla`, store theo provider), Monaco 0.57.0 và `@monaco-editor/react` 4.7.0 đã cài ở `web-bootstrap-playful`, chưa dùng.

## Goals / Non-Goals

**Goals:** thành phần soạn/xem tái sử dụng, tự host, tải lười, truy cập được.

**Non-Goals:** chạy thử mã, LSP/autocomplete nâng cao, đồng bộ nháp lên server, hỗ trợ Scratch trong trình soạn.

## Decisions

1. **Tự host Monaco bằng gói `monaco-editor` và cấu hình loader.** `@monaco-editor/react` mặc định tải từ CDN; phải cấu hình `loader.config({ monaco })` với bản đóng gói cục bộ (cách cấu hình và worker trong Next 15.5/Turbopack **chưa tra tài liệu**, task 1.1). Lý do: không phụ thuộc CDN, kiểm soát CSP và phiên bản, chạy được khi mạng bị giới hạn.
   - Phương án khác: để mặc định CDN - đơn giản nhưng phụ thuộc bên thứ ba, bị loại; Ace tiếp tục - không hỗ trợ tốt hướng chạy thử và hệ sinh thái React.
2. **Cắt Monaco theo nhu cầu.** Không nạp toàn bộ ngôn ngữ; chỉ nạp mode ứng với các `Language.ace` đang bật cộng `plaintext`. Mục tiêu ngân sách: phần JS khởi tạo trình soạn ≤ 1 MB gzip (con số đo ở task 3.x, nếu vượt thì ghi lại và quyết định lại).
3. **Ánh xạ ngôn ngữ qua bảng dữ liệu một chỗ.** `ace` mode → id Monaco (ví dụ `c_cpp`→`cpp`, `python`→`python`, `java`→`java`...). Bảng nằm trong `web/src/lib/code/language-map.ts`; thiếu thì `plaintext`. Bảng đầy đủ lập khi thực hiện bằng cách liệt kê `Language.ace` thực trong DB demo/production.
4. **Dữ liệu ngôn ngữ từ API.** Mở rộng `problem-filters` hoặc thêm `GET /api/v1/languages` (chọn khi viết task 2.1 dựa trên dữ liệu nộp bài cần: key, name, ace, template, extension, file_only, file_size_limit, và ngôn ngữ nào được phép cho từng đề). Danh sách cho từng đề nằm ở API chi tiết đề.
5. **Chủ đề.** Hai chủ đề tự định nghĩa bằng token trong `style.md` (nền Cream/Espresso, chữ đủ tương phản), đăng ký qua `defineTheme`; chọn theo `ui-store.theme`. `Profile.ace_theme` không được dùng ở Next.js trong đợt này; nếu người dùng cần chủ đề riêng sẽ làm ở trang cài đặt hồ sơ.
6. **Bản nháp.** Store Zustand `drafts` với khoá `${problemCode}:${languageKey}`, ghi localStorage có `try/catch`, ghi trễ (debounce) để không ghi mỗi phím. Giới hạn kích thước mỗi nháp theo giới hạn `source` của form (65536 ký tự) và số nháp tối đa để không đầy localStorage.
7. **`CodeViewer`.** Chế độ chỉ đọc, dùng chung ánh xạ ngôn ngữ; cho phép sao chép; chiều cao theo nội dung có giới hạn.
8. **Truy cập.** Monaco giữ phím Tab; cung cấp phím thoát có công bố (Ctrl/Cmd+M bật/tắt "Tab di chuyển tiêu điểm" của Monaco) và nhãn `aria-label` cho vùng soạn. Cần xác nhận hành vi trong tài liệu Monaco hiện hành.

## Risks / Trade-offs

- [Kích thước và thời gian tải trên VPS/băng thông thấp] → tải lười, cắt ngôn ngữ, đo thực tế; đặt ngân sách.
- [Worker không chạy được với bundler] → thử sớm ở task 3.1 trước khi làm phần còn lại.
- [CSP hoặc `Cache-Control` làm tệp worker bị chặn/cache sai] → các tệp trong `/_next/static` đã `immutable`; kiểm khi triển khai.
- [Chủ đề Ace cũ của người dùng mất] → chấp nhận ở đợt này, ghi trong trang cài đặt hồ sơ về sau.
- [Monaco kém ở màn hình cảm ứng/điện thoại] → cung cấp `textarea` dự phòng khi màn hình hẹp hoặc Monaco không tải được; người dùng vẫn nộp được bài.

## Migration Plan

1. Thêm thành phần và trang `/dev/editor` (chỉ chạy ở dev) để xem trước.
2. Trang nộp bài và xem mã nguồn (change của trang đề bài/bài nộp) dùng thành phần.
3. Rollback: bỏ thành phần khỏi trang; không đụng dữ liệu.

## Open Questions

- Danh sách mode Monaco cần nạp (sau khi liệt kê `Language.ace` thực tế). Không đổi spec hay task.

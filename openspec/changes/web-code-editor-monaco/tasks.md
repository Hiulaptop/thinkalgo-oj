# Tasks

## 1. Tra cứu

- [ ] 1.1 Tra tài liệu chính thức của `monaco-editor` 0.57 và `@monaco-editor/react` 4.7 (tự host, worker với Next 15.5/Turbopack, `defineTheme`, phím thoát tiêu điểm). Ghi URL và ngày tra vào mục "Nguồn" cuối `design.md`. Xong khi mục "Nguồn" đủ URL.
- [ ] 1.2 Liệt kê `Language.ace`, `key`, `extension`, `file_only` thật từ DB demo hoặc `judge/fixtures/language_small.json`. Xong khi bảng ánh xạ ban đầu nằm trong `design.md`.

## 2. API ngôn ngữ

- [ ] 2.1 Cung cấp dữ liệu ngôn ngữ qua API (endpoint hoặc mở rộng hiện có theo quyết định 4), cập nhật `schema.yml` và `schema.d.ts`. Xong khi `tsc --noEmit` qua và phản hồi có đủ trường theo spec.

## 3. Thành phần

- [ ] 3.1 Dựng `CodeEditor` tự host với worker chạy được ở `next dev` và `next build` + `next start`. Xong khi không có request ra domain ngoài (kiểm bằng Playwright ghi log network) và tô màu cú pháp hiển thị.
- [ ] 3.2 Bảng ánh xạ ngôn ngữ, nạp mẫu mã không ghi đè bài đang viết, ngôn ngữ `file_only` ẩn trình soạn. Xong khi từng kịch bản của spec đúng khi chạy tay trên `/dev/editor`.
- [ ] 3.3 Chủ đề sáng/tối theo `ui-store`, đổi nóng không mất nội dung. Xong khi chụp ảnh hai chủ đề và đo tương phản ≥ 4.5:1 (hàm trong `src/lib/colors.ts`).
- [ ] 3.4 Store bản nháp Zustand + localStorage có `try/catch`, debounce, giới hạn số nháp. Xong khi khôi phục sau tải lại và vẫn chạy khi localStorage ném lỗi.
- [ ] 3.5 `CodeViewer` chỉ đọc và `textarea` dự phòng. Xong khi xem được mã và nộp được bằng textarea khi chặn tải Monaco.
- [ ] 3.6 Truy cập bàn phím và nhãn. Xong khi thoát được trình soạn chỉ bằng bàn phím và axe không báo lỗi nghiêm trọng trên `/dev/editor`.
- [ ] 3.7 Đo kích thước JS tải cho trình soạn. Xong khi số đo được ghi vào `design.md` và so với ngân sách (vượt thì ghi lý do và quyết định).

## 4. Kiểm tra

- [ ] 4.1 Trình bày kịch bản kiểm thử (ngôn ngữ, mẫu mã, nháp, chủ đề, bàn phím, mạng) cho người dùng duyệt; sau đó chạy một lần ngoài repo. Xong khi người dùng approve và kết quả ghi vào `design.md`. Không viết file `*.test.*`.
- [ ] 4.2 `npm run lint`, `tsc --noEmit`, `npm run build`, `/dev/editor` trả 404 ở production. Xong khi tất cả đạt.

## Workflow follow-up

- Trang nộp bài và xem mã nguồn dùng thành phần ở change của trang đề bài/bài nộp, sau đó `/opsx:archive`.

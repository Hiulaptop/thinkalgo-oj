# Tasks

## 1. Tra cứu và đọc kỹ

- [ ] 1.1 Tra tài liệu chính thức (DRF 3.17: parser multipart, `SessionAuthentication`/CSRF; Django 4.2: cache API, `select_for_update`). Ghi URL và ngày tra vào mục "Nguồn" cuối `design.md`. Xong khi mục "Nguồn" đủ URL.
- [ ] 1.2 Đọc `ProblemSubmit.form_valid`, `submission_abort`, `rejudge_submission`, các view AJAX của comment/blog và ghi các luật nghiệp vụ, điều kiện quyền, sự kiện phát ra vào `design.md`. Xong khi bảng luật được thêm vào `design.md`.
- [ ] 1.3 Xác nhận `CACHES` và `client_max_body_size` thực tế trên dev compose/production baseline. Xong khi giá trị được ghi vào `design.md`.

## 2. Khuôn chung

- [ ] 2.1 Bộ chuyển `form.errors` → `fields` dùng chung (`judge/api/v1/forms.py`), CSRF bắt buộc cho view ghi, mã lỗi `csrf_failed`. Xong khi một endpoint thử trả đúng 403 `csrf_failed` khi thiếu token.
- [ ] 2.2 Cơ chế `Idempotency-Key` (lưu cache theo user+key, TTL). Xong khi gửi hai lần cùng khoá chỉ tạo một bản ghi.

## 3. Thao tác ghi

- [ ] 3.1 Trích logic tạo bài nộp dùng chung, thêm `POST /api/v1/problems/<code>/submissions` (JSON + multipart). Xong khi đối chiếu với trang nộp cũ cho cùng đầu vào cho cùng kết quả ở các ca: mã hợp lệ, cả mã và file, sai phần mở rộng, quá cỡ, file-only, ngôn ngữ bị giới hạn, đang trong contest.
- [ ] 3.2 Bình luận: tạo, sửa, ẩn, lịch sử, danh sách phiếu. Xong khi đối chiếu hành vi với view AJAX cũ ở các ca quyền khác nhau.
- [ ] 3.3 Bỏ phiếu bình luận và blog. Xong khi các ca: bỏ phiếu mới, đổi phiếu, bỏ phiếu, tự bỏ phiếu, chưa đăng nhập cho kết quả như cũ.
- [ ] 3.4 Huỷ và chấm lại bài nộp. Xong khi quyền đúng ở các vai trò (thường, tác giả, người chấm, superuser).
- [ ] 3.5 Cập nhật `schema.yml`, `schema.d.ts` và client ghi dùng chung trong `web/src/lib/api`. Xong khi `npm run api:types` và `tsc --noEmit` qua.

## 4. Kiểm tra

- [ ] 4.1 Trình bày kịch bản kiểm thử chi tiết (ma trận vai trò × thao tác, dữ liệu, kết quả mong đợi, đối chiếu view cũ) để người dùng duyệt; sau đó chạy một lần ngoài repo và quét rò rỉ dữ liệu. Xong khi người dùng approve và kết quả ghi vào `design.md`. Không viết file `*.test.*`.
- [ ] 4.2 `flake8`, `python manage.py check`, `npm run lint`, `tsc --noEmit`. Xong khi tất cả qua.

## Workflow follow-up

- Các trang đề bài, bài nộp, blog dùng API ghi trong change của từng trang; sau đó `/opsx:archive`.

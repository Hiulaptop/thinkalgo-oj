# Design

## Context

Xem `proposal.md` - Why. Hiện trạng đã đọc:

- Nộp bài: `ProblemSubmit` (`judge/views/problem.py:819`) dùng `ProblemSubmitForm` (`judge/forms.py:374`, `source` ≤ 65536 ký tự, `submission_file`, `judge`), kiểm file-only/phần mở rộng/kích thước và riêng cho `SCRATCH`; route `/problem/<code>/submit` và `/resubmit/<id>`.
- AJAX hiện có: `comments/upvote|downvote|hide`, `comment/<id>/edit/ajax`, `history/ajax`, `votes/ajax`, `posts/upvote|downvote`, `submission/<id>/abort`, `submission/rejudge`, `language template ajax`.
- `api-foundation` đã có: `ApiError`, handler lỗi, phân trang, middleware chặn 2FA/đổi mật khẩu cho `/api/v1/`.
- `web-auth-session-api` (đã đề xuất) định nghĩa CSRF + phiên cho trình duyệt; change này dùng lại.

## Goals / Non-Goals

**Goals:** một khuôn thao tác ghi dùng chung, nộp bài đúng luật cũ, bình luận/bỏ phiếu đúng luật cũ, hợp đồng OpenAPI.

**Non-Goals:** không đổi luật nghiệp vụ, không tối ưu hàng chấm, không thêm thao tác của trang chưa làm, không thêm rate limit mới ngoài những gì view cũ đã có.

## Decisions

1. **Tách logic nghiệp vụ khỏi view, không bọc view.** Với mỗi thao tác, trích hàm dùng chung (ví dụ `create_submission(user, problem, language, source|file, contest)`) từ `form_valid`/AJAX hiện có, rồi view Jinja và view API cùng gọi. Lý do: bọc `View.post` bằng request giả dễ sai và khó kiểm; sao chép luật thì lệch. Đổi sẽ nhỏ, từng thao tác một, có thể revert độc lập.
   - Phương án khác: gọi nội bộ view cũ qua `RequestFactory` - giòn, trả HTML; để Next gửi form tới URL cũ - cần trả HTML, không có hợp đồng.
2. **Lỗi biểu mẫu.** Dùng chung bộ chuyển `form.errors` → `fields` với `web-auth-session-api` (đặt ở `judge/api/v1/forms.py`), thông điệp được Django dịch theo ngôn ngữ request.
3. **Idempotency cho nộp bài.** Header `Idempotency-Key` (UUID do client sinh khi mở trang nộp). Lưu khoá theo (user, key) với TTL ngắn (ví dụ 10 phút) trong cache của Django; nếu có thì trả lại `id` đã tạo. Chọn cache thay bảng mới để không phải migration; chấp nhận mất khoá khi cache bị xoá (rủi ro trùng bài nộp rất thấp và vẫn bị chặn bởi giới hạn nộp liên tiếp hiện có). Cần xác nhận cache hiện dùng backend nào ở production (`CACHES` rỗng ở `settings.py`, đặt trong `local_settings`).
4. **Tải file.** `multipart/form-data` cho nộp file, JSON cho nộp mã; cùng endpoint, phân biệt theo `Content-Type`. Giới hạn kích thước ở nginx (`client_max_body_size`) phải ≥ giới hạn lớn nhất của ngôn ngữ; kiểm tra khi triển khai.
5. **Bỏ phiếu và bình luận.** Giữ ngữ nghĩa của view AJAX cũ (một phiếu mỗi người, đổi phiếu, giới hạn điểm). API trả trạng thái mới (điểm, phiếu của người dùng) để giao diện cập nhật mà không phải tải lại.
6. **Quyền.** Kiểm trước khi ghi bằng `Problem.is_accessible_by`, `Submission.can_see_detail` và các hàm tương ứng; ẩn đối tượng không được thấy bằng 404.
7. **Sự kiện thời gian thực.** Nộp bài đã phát sự kiện qua cơ chế hiện có (`event_poster`/`wsevent`); API gọi cùng đường đó nên WebSocket không đổi.

## Risks / Trade-offs

- [Trích logic làm hỏng view Jinja đang chạy] → làm từng thao tác, đối chiếu hành vi view cũ trước và sau trên dev compose (giống cách đối chiếu API đọc).
- [Nộp trùng khi mạng chập chờn] → `Idempotency-Key` + giới hạn hiện có.
- [Bỏ phiếu bị đua (race)] → dùng đúng cách khoá/giao dịch của view cũ; thêm `select_for_update` nếu view cũ có; ghi lại khác biệt nếu có.
- [CSRF khi trang cache] → trang ghi dùng `Cache-Control: private, no-cache` đã đặt ở `web/`.
- [Tải file lớn qua nginx/Cloudflare bị cắt] → kiểm giới hạn và thời gian chờ khi triển khai.

## Migration Plan

1. Trích logic dùng chung, giữ view Jinja hoạt động như cũ.
2. Thêm view API, schema, type; chưa mở cho người dùng.
3. Trang Next.js (change của từng trang) dùng API; mở route theo `deploy/nginx`.
4. Rollback: chỉ cần chuyển route trang về Django; API ghi vô hại khi không ai gọi.

## Open Questions

- Backend cache production (ảnh hưởng độ bền của khoá idempotency). Không đổi spec hay task.

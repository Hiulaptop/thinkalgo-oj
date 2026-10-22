# Proposal

## Why

`api-foundation` mới có API **đọc**. Các trang Next.js ở đợt 2 cần thao tác ghi: nộp bài, bình luận, bỏ phiếu, huỷ/chấm lại bài nộp. Hiện chúng là view Jinja gửi form hoặc khoảng 15 endpoint AJAX (`comments/upvote|downvote|hide`, `comment/edit/ajax`, `posts/upvote|downvote`, `submission/abort`, `submission/rejudge`, ...) không có hợp đồng thống nhất. Cần một cơ chế ghi chung (CSRF, phiên, lỗi, quyền, chống gửi trùng) và các thao tác ghi đầu tiên mà trang đề bài, bài nộp và blog cần, thay vì mỗi trang tự nghĩ ra một kiểu.

## What Changes

- Quy ước ghi cho `/api/v1/`: xác thực bằng phiên Django, CSRF qua `X-CSRFToken` (như `web-auth-session-api`), định dạng lỗi `{code, detail, fields?}`, mã trạng thái, và `Idempotency-Key` cho thao tác tạo (nộp bài).
- Lớp adapter dùng lại form/logic của view hiện có (không sao chép luật nghiệp vụ); quyền kiểm bằng các hàm của model như API đọc.
- Thao tác ghi đợt này: **nộp bài** (mã nguồn hoặc file, kèm kiểm giới hạn hiện có), **bình luận** (tạo, sửa, ẩn, bỏ phiếu lên/xuống), **bỏ phiếu bài blog**, **huỷ** và **chấm lại** bài nộp, kèm lịch sử/phiếu bầu chỉ đọc cần cho giao diện bình luận.
- Các thao tác ghi khác (ticket, đăng ký contest, tổ chức, hồ sơ, đề xuất đề) thuộc change của từng trang và dùng lại quy ước này.
- Cập nhật `schema.yml` và type TypeScript sinh ra; client ghi trong `web/` dùng chung cho mọi trang.

## Capabilities

### New Capabilities
- `api-write-actions`: quy ước API ghi (CSRF, lỗi, idempotency, quyền) và các thao tác nộp bài, bình luận, bỏ phiếu, huỷ/chấm lại bài nộp.

### Modified Capabilities

(Không có; `openspec/specs/` chưa có spec nào.)

## Impact

- Django: `judge/api/v1/views/` thêm view ghi, `adapters.py` mở rộng; có thể thêm một bảng nhỏ hoặc dùng cache cho khoá idempotency (quyết định ở design); không đổi model đã có.
- `web/`: client ghi dùng chung, hook gọi API từ trình duyệt kèm CSRF.
- Ngoài phạm vi: hàng đợi chấm bài và `bridged` không đổi; WebSocket sự kiện không đổi.

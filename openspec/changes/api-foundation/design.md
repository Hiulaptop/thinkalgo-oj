# Design

## Context

Xem `proposal.md` cho lý do. Hiện trạng (đọc từ `dmoj/urls.py`, `judge/views/*`, `judge/models/*`):

- `api/v2/sync/...` (4 endpoint, `judge/views/api/api_v2.py`, 212 dòng) tự cài `APIMixin`/`APIKeyRequiredMixin` với API key; không có schema. `api/token/generate|remove/` cấp token cho người dùng. Hai nhóm này không phục vụ frontend và giữ nguyên.
- Quyền xem nằm trong **phương thức của model**: `Problem.is_accessible_by(user)` (xét kỳ thi hiện tại `user.profile.current_contest`, đề công khai/riêng của tổ chức, `see_private_problem`, người sửa, tester), `Problem.get_visible_problems(user)`, `Contest.is_accessible_by`, `Contest.get_visible_contests(user)`. View trả 404 khi không có quyền (`ProblemMixin.get_object`), trang riêng khi đề đã xoá.
- Logic danh sách nằm trong view dạng lớp, trộn session: `ProblemList` có `GET_with_session(request, 'hide_solved' | 'show_types' | 'full_text')` (lưu lựa chọn trong session), sắp xếp bằng `QueryStringSortMixin` (`sql_sort`, `manual_sort`), phân trang `InfinitePaginationMixin` (không đếm tổng), sắp xếp theo "đã giải" làm ở Python.
- `Django>=4.2,<5`, Python 3.11 (Docker) / 3.12 (CI).

### Kiểm chứng về phụ thuộc (PyPI, 2026-10-22)
- `djangorestframework` 3.18.x yêu cầu Django ≥ 5.2 (siêu dữ liệu 3.18.0); 3.17.2 và 3.16.1 yêu cầu Django ≥ 4.2. Cài thẳng bản mới nhất sẽ **xung đột với Django 4.2** của repo, nên phải ghim `>=3.16,<3.18`.
- `drf-spectacular` 0.30.0 hỗ trợ Django 4.2 (`Django>=2.2`, `djangorestframework>=3.10.3`).
- `django-ninja` 1.7.1 hỗ trợ Django 4.2 (đã xem metadata) nhưng kéo thêm Pydantic 2.
- Chưa tra tài liệu chính thức của các thư viện này (Context7 bị chặn trong phiên).

## Goals / Non-Goals

**Goals:**
- API đọc đợt 1 đúng quyền, đúng thứ tự so với trang Jinja, có schema OpenAPI và type TS.
- Không đổi hành vi của view Jinja hay API hiện có.

**Non-Goals:**
- Endpoint ghi (nộp bài, bình luận, đăng nhập, chỉnh hồ sơ): thuộc change sau (cần CSRF, rate limit, quyền ghi).
- Contest, tổ chức, ticket, thông báo: đợt sau.
- Token/OAuth cho client bên thứ ba.
- Cache phía server (tối ưu khi có số liệu tải thật).

## Decisions

1. **Django REST framework (ghim `>=3.16,<3.18`) + drf-spectacular.** Lý do: hệ sinh thái lớn, serializer/permission quen thuộc, sinh OpenAPI hoàn chỉnh. Thay thế: (a) django-ninja (gọn, type-first, nhưng thêm Pydantic 2 và là mô hình khác với phần còn lại của repo); (b) tiếp tục kiểu `APIMixin` tự viết (không thêm phụ thuộc nhưng phải tự làm schema, phân trang, lỗi). Quyết định này phụ thuộc vào ghim phiên bản; nếu sau này nâng Django ≥ 5.2 thì bỏ ghim.

2. **Lớp dịch vụ truy vấn mỏng `judge/api/services/`, không sửa view Jinja.** Mỗi tài nguyên có hàm dựng queryset từ `(user, params)` dựa trên **các phương thức quyền của model**, không tự viết lại điều kiện quyền. Lý do: view Jinja phụ thuộc request/session/template, refactor 1 000+ dòng mỗi file làm tăng rủi ro hồi quy lên trang đang chạy. Đánh đổi: có hai nơi giữ logic lọc/sắp xếp cho tới khi bỏ Jinja → bù bằng yêu cầu "tương đương với bản Jinja" và kiểm tra song song (xem "Kiểm thử đề xuất"). Thay thế: trích xuất logic dùng chung từ view (đẹp hơn dài hạn nhưng rủi ro cao ở giai đoạn này).

3. **Tham số tường minh thay cho session.** `hide_solved`, `show_types`, `full_text`, `category`, `type` (lặp), `point_start`, `point_end`, `search`, `order`, `page`, `page_size`. Frontend giữ tuỳ chọn người dùng trong store phía client (Zustand) và luôn gửi lên. Sắp xếp theo "đã giải" (Python) giữ nguyên hành vi nhưng giới hạn trong trang.

4. **Phân trang bằng `page`/`page_size` (tối đa 100) và `has_next`, không `count`.** Lấy `page_size + 1` bản ghi để biết còn trang sau. Khớp với `InfinitePaginationMixin` hiện có; tránh `COUNT(*)` trên bảng bài nộp lớn.

5. **Lỗi JSON thống nhất** `{ "code": "...", "detail": "..." }`, `code` ổn định và không dịch; `detail` có thể theo ngôn ngữ yêu cầu. 404 cho cả "không tồn tại" và "không có quyền" (như view Jinja).

6. **Serializer là danh sách trường tường minh (allow-list)**, không `fields = '__all__'`; kiểm tra trường nhạy cảm (email, `Profile.ip`, `ip_auth`, API token, 2FA) bị loại. Nội dung đề/blog là HTML đã render an toàn qua đúng pipeline Jinja dùng (cần xác định hàm render sẵn có và tái sử dụng, không tự `mark_safe`).

7. **Xác thực mặc định là session (SessionAuthentication) và quyền mặc định là cho phép đọc ẩn danh**; mỗi tài nguyên tự lọc theo `request.user`. Không bật Token/Basic cho `/api/v1/`. CSRF chỉ có ý nghĩa khi có endpoint ghi (sau này, theo cơ chế của DRF SessionAuthentication).

8. **Next.js gọi Django phía server**, không qua trình duyệt, tới `http://127.0.0.1:8000` với `Host: oj.thinkcode.vn`, chuyển tiếp `Cookie` và `X-Real-IP` (cần cho `LogUserAccessMiddleware` và giới hạn theo IP; xem `monorepo-compose-layout`). Trình duyệt không gọi trực tiếp `/api/v1/` ở đợt 1 (tránh lộ chi tiết, giảm bề mặt CORS); các tính năng tương tác phía client sau này sẽ gọi cùng tên miền.

9. **Type TypeScript** sinh bằng `openapi-typescript` (7.13.0) từ schema, kèm client `openapi-fetch` (0.17.0); hai gói chưa tra tài liệu chính thức. Schema được xuất thành tệp lúc build/CI và kiểm tra khác biệt để API đổi mà `web/` không đổi theo thì lỗi.

## Kiểm thử đề xuất (chờ duyệt, chưa viết)

Theo cách làm việc của dự án, không tự viết test. Vì sai quyền là rủi ro lớn nhất của change này, đề xuất kịch bản sau; **chỉ viết khi bạn duyệt**.

**Ma trận quyền (đề bài, bài nộp, blog)**: vai trò × trạng thái tài nguyên.

| Vai trò | Đề công khai | Đề riêng (chưa public) | Đề riêng của tổ chức | Đề trong kỳ thi đang diễn ra | Đề đã xoá |
|---|---|---|---|---|---|
| Ẩn danh | thấy | 404 | 404 | 404 | 404/đã xoá theo Jinja |
| Người dùng thường | thấy | 404 | 404 | 404 (nếu không tham gia) | theo Jinja |
| Thành viên tổ chức | thấy | 404 | thấy | — | — |
| Đang tham gia kỳ thi chứa đề | chỉ đề của kỳ thi | — | — | thấy | — |
| Tác giả/người sửa | thấy | thấy | thấy | thấy | theo Jinja |
| Tester | thấy | thấy | — | — | — |
| Có `see_private_problem` | thấy | thấy | thấy | thấy | — |

Bài nộp: chủ bài nộp, người có quyền xem mã nguồn, ban tổ chức kỳ thi, người dùng khác; bài nộp thường và bài nộp trong kỳ thi đang diễn ra/đã kết thúc; ẩn mã nguồn khi không có quyền.

**Tương đương với Jinja**: với một bộ dữ liệu mẫu và từng vai trò, so sánh danh sách đề (cùng bộ lọc) giữa `/problems` và `/api/v1/problems` (cùng tập, cùng thứ tự), đo cả khi có `hide_solved`, `search`, `type`, sắp xếp theo từng khoá.

**Bảo mật**: quét serializer đảm bảo không có trường nhạy cảm; `page_size` > 100 bị từ chối; không có truy vấn đếm toàn bảng trên danh sách bài nộp (kiểm tra bằng số truy vấn).

## Risks / Trade-offs

- [Sai quyền làm lộ đề/bài nộp] → Dùng phương thức quyền của model; ma trận kiểm thử được duyệt; review bắt buộc cho từng serializer; 404 cho mọi từ chối.
- [Hai nơi giữ logic lọc/sắp xếp] → Yêu cầu tương đương và so sánh song song; bỏ Jinja ở change cuối.
- [Xung đột phiên bản DRF với Django 4.2] → Ghim `<3.18`; `pip check` trong CI/Docker build.
- [Truy vấn N+1/nặng ở danh sách bài nộp, xếp hạng] → `select_related/prefetch_related`, phân trang không đếm; đo số truy vấn; thêm cache sau khi có số liệu.
- [Sắp xếp "đã giải" làm trong Python] → Chỉ trong trang; ghi nhận giới hạn, cải thiện ở change sau nếu chậm.
- [Rò thông tin qua thông báo lỗi/`detail` theo ngôn ngữ] → `code` ổn định, `detail` không chứa dữ liệu nội bộ.
- [Chi tiết đề dạng HTML: XSS] → Chỉ dùng pipeline render đã dùng cho Jinja; Next.js hiển thị trong vùng riêng, không thêm tuỳ biến HTML mới.

## Migration Plan

Chỉ thêm mới (`/api/v1/`), không đổi hành vi hiện có. Triển khai cùng backend như thường lệ; frontend chưa gọi cho tới change trang đầu tiên. Hoàn tác: gỡ include `/api/v1/` khỏi `urls.py` và bỏ phụ thuộc.

## Open Questions

- Có bật OpenAPI UI (Swagger/Redoc) trên production hay chỉ xuất schema tĩnh?
- Hàm render nội dung đề/blog sẵn có cần tái sử dụng chính xác là gì (cần đọc `judge/utils/` khi apply)?
- Có cần endpoint danh mục (types/groups/categories) tách riêng hay nhúng vào danh sách đề?

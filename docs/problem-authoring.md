# Trình soạn bài chung

**Trạng thái triển khai: chưa đủ điều kiện bật rollout.** Tài liệu này mô tả luồng đã xây dựng và các điều kiện bàn giao còn thiếu, không phải thông báo tính năng đã hoàn tất. Mặc định `PROBLEM_AUTHORING_ENABLED=False`. Chưa triển khai production.

## Dành cho người ra đề

Khi được bật, đường tạo/sửa bài hiện có và Admin Add mở cùng trình soạn. Người được cấp quyền không cần là staff để dùng trình soạn ngoài site.

1. Nhập mã/tên bài, nhóm/phân loại, TL/ML và điểm. Bộ nhớ hiển thị MB và lưu KB.
2. Soạn đề Markdown hoặc đính kèm PDF theo quyền. PDF không tự xóa Markdown.
3. Nhập editorial tùy chọn, tác giả, lịch và trạng thái công khai riêng.
4. Chọn ZIP test; kiểm tra cặp input/output, thứ tự, trọng số nguyên và pretest trước khi lưu.
5. Nếu cần kiểm chứng, đính kèm nguồn UTF-8 và chọn runtime nằm trong danh sách ngôn ngữ được phép của bài. Nguồn thủ công không bắt buộc là C++.
6. Bấm **Lưu nháp**. Lưu không tự chấm hoặc tự công khai. Bài mới riêng tư; có thể lưu chưa có test nếu metadata model hợp lệ.
7. Chờ dữ liệu sẵn sàng rồi chọn **Chấm lời giải chuẩn đã lưu** nếu cần. Mã nguồn chỉ được chạy qua sandbox judge hiện có.
8. **Công khai phiên bản đã lưu** là thao tác riêng, cần quyền và dữ liệu sẵn sàng. Nếu chưa có AC của phiên bản hiện tại, phải xác nhận cảnh báo. AC không tự công khai đề hoặc editorial.

Chấm/công khai dùng bản đã lưu, không dùng nội dung đang nhập. Khi hai tab sửa cùng bài, revision cũ bị từ chối thay vì ghi đè; sao chép phần chưa lưu trước khi tải lại. Upload đã nhận được giữ bằng tham chiếu server-side khi form lỗi, không dựa vào việc trình duyệt giữ file input.

### Định dạng ZIP

Test-only:

```text
tests.zip
  1.in
  1.out
  2.in
  2.out
  10.in
  10.out
```

Có thể đặt toàn bộ cặp ở root, `tests/`, một thư mục bao, hoặc `wrapper/tests/`; không trộn nhiều gốc. Thứ tự tự nhiên là 1, 2, 10. Chỉ hỗ trợ `.in`/`.out`, không tự đoán `.inp`/`.ans`. Thiếu cặp hoặc file lạ sẽ bị từ chối.

ZIP trọn gói, ở root hoặc một thư mục bao:

```text
statement.md        # bắt buộc, UTF-8, không rỗng
editorial.md        # tùy chọn
solution.cpp        # tùy chọn; chọn runtime trên form
 tests/1.in         # tùy chọn; nếu có phải đủ cặp
 tests/1.out
```

Các dòng `tests/` trên minh họa cùng cấp với `statement.md`, không có khoảng trắng đầu tên. ZIP trọn gói có thể chỉ chứa `statement.md`. Dùng **Xem trước ZIP**, chọn rõ phần muốn thay, rồi xác nhận áp dụng. Nội dung không được chọn giữ nguyên. Không hỗ trợ ảnh/tài nguyên Markdown tương đối hoặc nhiều bài trong một ZIP. TL/ML/tiêu đề đọc từ Markdown chỉ là gợi ý có thể sửa trên form.

Không upload `init.yml` để cấu hình luồng nhanh. Bài có custom checker/grader, generator, batch/subtask hoặc cấu hình đặc biệt dùng **Dữ liệu nâng cao**; thay ZIP đơn giản sẽ bị từ chối nếu làm mất cấu hình này. Sửa riêng đề/editorial vẫn được phép trong khi chuẩn bị hoặc kiểm chứng.

### Quyền

| Thao tác | Điều kiện chính |
|---|---|
| Tạo global | `add_problem` và `edit_own_problem` |
| Tạo trong tổ chức | `create_organization_problem`, quyền quản trị đúng tổ chức và `edit_own_problem` |
| Sửa | `Problem.is_editable_by`, đúng phạm vi và bài chưa xóa |
| ZIP test-only | Quyền tạo/sửa, không cần quyền import gói |
| ZIP trọn gói | Thêm `import_problem_package` |
| PDF | Thêm `upload_file_statement` |
| Nhiều test vượt hard limit thường | `create_mass_testcases`, vẫn chịu trần kỹ thuật |
| Công khai đề/editorial | `change_public_visibility` và quyền/phạm vi tương ứng |

Upload chưa consume chỉ owner dùng được; upload đã gắn bài có thể tải bởi người được phép sửa bài đó, tùy quyền loại upload. Test/source tải qua endpoint kiểm tra quyền với `private, no-store`, không qua CDN media công khai. PDF theo chính sách media hiện có nên không dùng để lưu lời giải bí mật hoặc test.

### Trạng thái và khôi phục

- **MISSING:** chưa có dữ liệu sẵn sàng; có thể tiếp tục soạn/lưu. Không được nộp/chèn contest/công khai.
- **PENDING / INSTALLING / PUBLISHING:** operation đã được lưu bền, đang chuẩn bị/đồng bộ. Broker lỗi không làm mất bản nháp.
- **WAITING:** đang chờ submission cũ kết thúc trước khi thay dữ liệu. Không sửa file bên dưới một bài đang chấm.
- **READY:** dữ liệu đã kích hoạt. Nếu dùng R2, pointer release đã được cập nhật trong bước kích hoạt.
- **FAILED dữ liệu:** giữ operation/artifact để thử lại. Không xóa thư mục hoặc sửa DB bằng tay. Hiện chưa có hủy/supersede an toàn cho operation thất bại; đây là blocker rollout.
- **PENDING / DISPATCHING / JUDGING kiểm chứng:** source/runtime và grading configuration bị khóa; đề/editorial không bị khóa.
- **FINISHED:** xem result; không đồng nghĩa AC hoặc đã công khai. Grading revision thay đổi làm kết quả cũ stale.
- **FAILED kiểm chứng:** có thể retry hạ tầng cùng submission nếu nó còn tồn tại. Nếu submission đã bị xóa, bắt đầu lượt kiểm chứng mới; hệ thống không tự tạo lại lượt đã mất.

Polling chỉ đọc, không sửa form hoặc hidden revision. Dừng khi hết việc, tạm dừng tab ẩn, timeout request 10 giây, backoff lỗi và dừng sau 5 lỗi liên tiếp. Nếu trạng thái không cập nhật, giữ nội dung đang nhập và kiểm tra lại bằng tải trang sau khi sao chép/lưu nội dung cần giữ.

## Dành cho operator

### Lưu trữ và tiến trình

- `PROBLEM_AUTHORING_ROOT` là staging riêng tư, dùng chung site/Celery; Docker example mặc định `/private-problem-imports/authoring`.
- `DMOJ_PROBLEM_DATA_ROOT/.authoring/<operation UUID>/` chứa snapshot/prepared/backup và lock/journal; không public-serve thư mục này.
- Active data tiếp tục ở thư mục problem hiện có. Test/source không đưa vào public media.
- Worker/reconciler cần Linux filesystem hỗ trợ `flock`, directory `fsync` và rename trong cùng filesystem. Không khẳng định hỗ trợ filesystem không có các semantics này hoặc chạy worker native Windows.
- DB, filesystem và R2 không có transaction chung. Giữ DB operation cùng snapshot/journal để retry/đối soát, không giả rollback cả ba.
- Celery task recovery chạy mỗi 60 giây khi beat đang chạy. Compose production có service `authoring-beat` thuộc profile `authoring`; tránh chạy thêm scheduler nếu đã có beat đang xử lý cùng schedule.

### Giới hạn mặc định

| Giới hạn | Giá trị / setting |
|---|---|
| ZIP nén | 100 MiB / `PROBLEM_AUTHORING_UPLOAD_LIMIT` |
| Tổng giải nén | 1 GiB / `PROBLEM_AUTHORING_EXPANDED_LIMIT` |
| Entry ZIP | 10.000 / `PROBLEM_AUTHORING_ENTRY_LIMIT` |
| Tài liệu trong ZIP | 5 MiB / `PROBLEM_AUTHORING_TEXT_LIMIT` |
| Mỗi file test | 256 MiB / `PROBLEM_AUTHORING_TEST_FILE_LIMIT` |
| Nguồn thủ công | 5 MiB |
| PDF | `PDF_STATEMENT_MAX_FILE_SIZE`, fallback 5 MiB |
| Upload chưa consume | Hết hạn 24 giờ |
| Dung lượng giữ theo owner | 200 MiB / `PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT` |
| Replacement budget tổ chức | 100 MiB / `PROBLEM_AUTHORING_REPLACEMENT_BUDGET` |
| Trần test kỹ thuật | 4.998 |
| Tên file testcase | 100 ký tự |
| Retention artifact operation READY | 86.400 giây / `PROBLEM_AUTHORING_ARTIFACT_RETENTION` |
| Số field request | 31.000 / `DATA_UPLOAD_MAX_NUMBER_FIELDS` |

Quota hiện tính upload retained và reservation snapshot/workspace; có thể từ chối ZIP nhỏ nhưng giải nén lớn. Retention thành công giải phóng reservation chỉ sau khi xóa snapshot/prepared/backup. Operation FAILED và upload lịch sử đã consume chưa có đầy đủ chính sách thu hồi; không xem cap hiện tại là giải pháp lifecycle hoàn chỉnh. Các giới hạn ngoài flag/root chưa được expose thành biến môi trường Docker example.

### Đối soát

Chạy trong môi trường ứng dụng được cấu hình, không dùng settings test vào production:

```sh
python3 manage.py reconcile_problem_authoring --legacy-check
```

Lệnh trên **chỉ đọc** số lượng legacy import theo state.

Các lệnh sau có thay đổi dữ liệu/files và chỉ chạy theo quy trình vận hành được phê duyệt:

```sh
python3 manage.py reconcile_problem_authoring --limit 100
python3 manage.py reconcile_problem_authoring --adopt-legacy-finished --limit 100
```

Lệnh mặc định phục hồi operation/kiểm chứng, cập nhật legacy terminal status và cleanup đủ điều kiện. Nó không phụ thuộc người dùng mở editor. Chế độ adoption explicit không tự rerun nguồn hoặc đánh dấu legacy AC thành verification của grading revision mới.

Không chạy legacy `publish_problem_release` để thay pointer của bài đã authoring-owned: helper từ chối để tránh ghi đè pointer operation. Khôi phục bằng operation/reconciler tương ứng; không gỡ authoring state để lách guard.

### Thứ tự rollout dự kiến — chưa được phép thực hiện

1. Hoàn thành blocker bên dưới và independent review; sao lưu và xác nhận phương án rollback tương thích.
2. Áp dụng migration additive `0235_problem_authoring` trong đợt triển khai được ủy quyền; không bulk adoption/mở lại nguồn trong migration.
3. Triển khai worker/site tương thích với cả legacy và shared flow, flag vẫn False. Kiểm tra private mounts, quyền filesystem, capacity và scheduler.
4. Dùng legacy check; để job cũ drain, xác nhận recovery, quota, lock và readiness.
5. Chỉ bật shared routes khi có phê duyệt riêng và toàn bộ gate an toàn đạt. Bật flag không thay thế bước xác minh browser/R2/storage.
6. Không xóa schema/artifact khi rollback UI. Job đã commit vẫn cần code xử lý tương thích; tắt flag không hủy operation hoặc kiểm chứng đang chạy.

### Blocker bàn giao còn mở

- Kiểm tra đủ completion contract của 12 task và một review độc lập toàn diff thực thi; chưa có reviewer report.
- Outer transaction của caller khi lưu PDF hoặc staging nâng cao/Polygon; orphan sau rollback và tombstone/lock-unlink lifecycle.
- Chính sách cancel/supersede/retention FAILED operation, lịch sử upload consumed và capacity/quota đầy đủ; tránh khóa người ra đề vĩnh viễn.
- Khóa/guard mọi đường bulk/direct mutation và parity metadata advanced/admin/Polygon; tác động reference run lên thống kê/listing.
- Admission/activation, worker takeover và cleanup/consume race cần bổ sung evidence theo contract, không suy từ test tuần tự.
- Recovery P/G dài hạn phải đối soát bridge; không tự reset submission đang thực sự chạy chỉ vì timeout.
- UI chỉnh testcase đã lưu không cần upload lại, thao tác thêm/xóa language limits, capability parity và mobile/keyboard smoke.
- R2 partial upload/orphan remote; package cũ hiện được đọc streaming, kiểm tra kích thước/SHA256 trước reuse bằng test mock, nhưng chưa thử network R2 hoặc production thật.
- Full suite chưa xanh do baseline `judge.jinja2.markdown.test_markdown.TestMarkdown.test_bleach`; 2 skips. Migration check còn drift `Profile.timezone`; repo lint còn lỗi có sẵn ngoài phạm vi mới. Xem log test cục bộ, không dùng tài liệu này làm bằng chứng review code.

Không commit/push/migrate/deploy, đổi secrets hoặc bật flag chỉ vì có tài liệu này.

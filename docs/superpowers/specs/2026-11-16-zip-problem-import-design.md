# Thiết kế import bài tập từ ZIP

Ngày: 2026-11-16. Trạng thái: người dùng đã duyệt thiết kế và bản đặc tả trong hội thoại.

## 1. Mục tiêu và phạm vi

Người quản lý upload một ZIP để tạo bài mới gồm đề Markdown, bộ test, editorial và code lời giải chuẩn. Sau khi phát hành dữ liệu test, hệ thống tạo submission để kiểm chứng code chuẩn bằng judge hiện có.

Các quyết định đã duyệt:

- Mỗi ZIP chứa một bài. Phiên bản đầu chỉ tạo mới; mã bài trùng là lỗi.
- Người dùng nhập metadata qua form sau upload. Bộ đọc điền sẵn thông tin nhận diện được từ đề.
- Import cả editorial và code chuẩn riêng; tự gửi code chuẩn để chấm thử.
- Tạo bài và editorial ở trạng thái ẩn. Người quản lý quyết định công khai sau đó.
- Xây luồng ZIP riêng, dùng lại cơ chế lưu bài, sinh cấu hình test và phát hành dữ liệu hiện có.
- Giữ ZIP nguồn riêng tư. Không chạy generator hoặc validator trong gói.

Phiên bản đầu hỗ trợ bài standard input/output, checker standard, các test có trọng số bằng nhau. Subtask, interactive, custom checker, nhiều bài trong ZIP và cập nhật bài có sẵn nằm ngoài phạm vi.

## 2. Căn cứ từ repository và gói mẫu

Đã khảo sát thư mục `/home/hlt/Documents/example/package/`, không suy đoán cấu trúc từ tên ZIP:

```text
package/
  statement.md
  editorial.md
  solution.cpp
  complexity.md
  test_plan.md
  tests/
    01.in
    01.out
    ...
    20.in
    20.out
  gen/
    gen.cpp
    validator.cpp
    commands.txt
```

`statement.md` chứa tên “Các số phân biệt”, thời gian 1 giây, bộ nhớ 512 MB. Có 20 cặp test. `test_plan.md` mô tả test đầu là sample và không có subtask. `editorial.md` đã chứa code C++; importer giữ nguyên nội dung, không nối thêm `solution.cpp`.

Các điểm tích hợp hiện có:

- `judge/views/problem.py`: luồng tạo/sửa bài và import Polygon.
- `judge/forms.py`: form bài tập và form import Polygon.
- `judge/models/problem.py`: `Problem`, `Solution`. `Solution.content` là editorial.
- `judge/models/problem_data.py`: `ProblemData`, `ProblemTestCase`.
- `judge/views/problem_data.py`: gọi `ProblemDataCompiler.generate` và tác vụ phát hành test.
- `judge/utils/problem_releases.py`, `judge/tasks/problem.py`: phát hành dữ liệu cho judge.
- `judge/management/commands/submit_polygon_solutions.py`: ví dụ tạo `Submission`, `SubmissionSource` và gửi chấm.

## 3. Hợp đồng ZIP

### 3.1. Gốc gói và file bắt buộc

Chấp nhận file ở gốc ZIP hoặc dưới đúng một thư mục bọc, ví dụ `package/`. Sau khi chuẩn hóa gốc, yêu cầu:

- `statement.md`: văn bản UTF-8, đề bài.
- `editorial.md`: văn bản UTF-8, hướng dẫn giải.
- `solution.cpp`: văn bản UTF-8, code chuẩn C++.
- `tests/`: ít nhất một cặp `<tên>.in` và `<tên>.out`.

Cho phép UTF-8 BOM. Nội dung bắt buộc không được rỗng. Input/output có thể rỗng và được giữ nguyên byte. Tên file phân biệt chữ hoa/thường; phần mở rộng test là `.in` và `.out`. Không chọn tùy ý một gốc khi ZIP chứa nhiều gói hợp lệ.

Ghép input/output bằng toàn bộ tên trước phần mở rộng, trong thư mục `tests/` trực tiếp. Thiếu một phía là lỗi, kèm tên file. Sắp xếp tự nhiên theo phần số, với tên đầy đủ làm khóa phụ để kết quả ổn định. Mỗi test có trọng số 1, không tự nhận diện pretest từ văn bản `test_plan.md`.

### 3.2. Tài liệu đi kèm

Giữ `complexity.md`, `test_plan.md`, `gen/` và các file bổ sung trong ZIP nguồn riêng tư. Trang xem trước phân biệt file dùng để import và file chỉ lưu trong gói nguồn. Không đưa ZIP nguồn hoặc code chuẩn vào bản phát hành test cho judge.

### 3.3. Kiểm tra đầu vào

Bộ đọc kiểm tra cấu trúc trước khi tạo bài: đường dẫn tuyệt đối, `..`, ký tự NUL, đường dẫn dùng dấu phân cách gây nhập nhằng, entry trùng sau chuẩn hóa, symlink, ZIP mã hóa hoặc hỏng đều là lỗi. Không dùng giải nén không giới hạn vào thư mục bài.

Giới hạn triển khai mặc định: ZIP upload 100 MiB; tổng dữ liệu giải nén 1 GiB; tối đa 10.000 file; mỗi file bắt buộc dạng văn bản tối đa 5 MiB; mỗi file test tối đa 256 MiB. Các giới hạn là cấu hình triển khai, áp dụng cả lúc đọc stream thay vì chỉ tin kích thước khai báo trong ZIP. Cấu hình proxy phải cho phép mức upload tương ứng. Thông báo lỗi nêu giới hạn bị vượt.

## 4. Trải nghiệm người dùng

### Bước 1: Upload

Người dùng mở trang “Import bài từ ZIP” bằng quyền import mới. Server nhận và kiểm tra ZIP trong vùng tạm riêng tư, sau đó tạo bản ghi chờ xác nhận. ZIP không hợp lệ không tạo `Problem`.

### Bước 2: Xem trước và xác nhận

Form hiển thị đề, editorial, số test, file đã nhận diện và các trường:

- Mã bài, theo validator hiện có; bắt buộc và chưa tồn tại.
- Tên bài, tự điền từ tiêu đề H1 đầu tiên.
- Thời gian (giây), bộ nhớ (MB), tự điền từ dòng nhãn tương ứng trong đề mẫu nếu nhận diện chắc chắn.
- Nhóm bài, loại bài, điểm bài.
- Ngôn ngữ C++ dùng cho code chuẩn, chọn từ ngôn ngữ được bật trong hệ thống.

Thiếu hoặc không nhận diện được metadata thì để trống và yêu cầu nhập, không đoán từ tên thư mục. Người dùng sửa được thông tin đã điền. Giữ nguyên Markdown gốc; các trường cấu hình chấm lấy giá trị người dùng xác nhận. Bộ nhớ chuyển MB sang KiB theo hệ thống hiện có: 512 MB thành 524288 KiB.

Điểm mặc định đề xuất 100, cho phép sửa theo validator hiện có. Bật điểm thành phần để điểm bài phân bổ theo trọng số test bằng nhau. Dùng tập ngôn ngữ mặc định của luồng tạo bài hiện tại và bảo đảm có ngôn ngữ code chuẩn đã chọn; người quản lý chỉnh danh sách sau trong trang quản lý bài.

Giao diện tuân thủ `style.md`. Nội dung xem trước dùng cùng cơ chế render và lọc Markdown của ứng dụng, không bật full markup cho gói upload.

### Bước 3: Kết quả import

Sau xác nhận, chuyển đến trang trạng thái có liên kết bài, submission và chức năng tải nguồn dành cho người có quyền. Hiển thị riêng:

- Tình trạng tạo bài và phát hành test.
- Tình trạng gửi/chờ chấm.
- Verdict và điểm từ submission, gồm cả AC, WA, TLE, RE hoặc CE.

AC không tự công khai bài. Verdict không AC không phải lỗi import. Chưa có judge phù hợp thì hiển thị chờ judge, không báo AC hoặc lỗi cấu trúc gói.

## 5. Dữ liệu và ranh giới thành phần

### 5.1. Dữ liệu bài hiện có

- `Problem`: đề, metadata đã xác nhận, người upload là tác giả, `is_public=False`.
- `Solution`: editorial nguyên bản, người upload là tác giả, `is_public=False`; gán `publish_on` hợp lệ nhưng không tự công khai.
- `ProblemData`: archive chỉ chứa test cần chấm, checker/grader standard.
- `ProblemTestCase`: thứ tự, đường dẫn input/output, trọng số 1, `is_pretest=False`.
- Sinh `init.yml` bằng compiler hiện có.

### 5.2. Bản ghi import mới

Thêm model `ProblemPackageImport` để lưu:

- ID, người upload, thời điểm tạo/cập nhật.
- ZIP nguồn ở storage riêng tư và checksum SHA-256.
- Metadata xác nhận, bản tóm tắt kết quả kiểm tra, phiên bản bộ đọc.
- Code chuẩn riêng cùng ngôn ngữ `Language` đã chọn.
- Liên kết bài đã tạo và submission kiểm chứng; cho phép null trước các bước tương ứng.
- Trạng thái, bước bị lỗi, thông báo lỗi đã lọc thông tin nội bộ.
- Phiên bản/checksum release dùng cho lần kiểm chứng.
- Thông tin claim tác vụ để kiểm soát retry và tác vụ trùng.

Code chuẩn có thể lưu dưới dạng TextField giới hạn bởi kích thước kiểm tra đầu vào; endpoint tải xuống trả tên `solution.cpp`. ZIP dùng private filesystem/shared volume mà site và worker cùng truy cập; không dùng mặc định public media storage/CDN. Bản ghi đã tạo bài giữ nguồn theo vòng đời bài. Bản nháp chưa xác nhận hết hạn sau 24 giờ; tác vụ dọn xóa nguồn của bản nháp hết hạn. Việc xóa bài phải dọn nguồn liên quan sau khi transaction thành công.

### 5.3. Các thành phần

- Bộ đọc gói: kiểm tra ZIP, đọc Markdown/code, lập manifest test, gợi ý metadata; không tạo model bài.
- Dịch vụ import: kiểm tra quyền và metadata, tạo bài và dữ liệu, quản lý trạng thái và tính idempotent.
- Tác vụ nền: phát hành release, tạo/gửi submission kiểm chứng và ghi nhận trạng thái.
- View/form/template: upload, preview, xác nhận, trạng thái, retry và tải file có kiểm tra quyền.

Không đưa quy tắc định dạng mới vào `PolygonImporter`.

## 6. Trạng thái và tác vụ nền

Luồng thành công:

```text
AWAITING_CONFIRMATION → CREATING → PUBLISHING → SUBMITTING → JUDGING → FINISHED
```

Lưu lỗi vận hành bằng trạng thái `FAILED` kèm `failed_stage`. Verdict thuộc submission, không thay thế trạng thái lỗi vận hành. Bản nháp hết hạn chuyển `EXPIRED`.

1. Khi xác nhận, khóa bản ghi import và kiểm tra lại quyền, trạng thái, mã bài, ngôn ngữ và checksum nguồn.
2. Dịch vụ chuẩn bị test trong staging riêng cho import, sinh và kiểm tra cấu hình trước khi công bố đường dẫn dữ liệu bài.
3. Tạo các model liên quan trong transaction; dùng ràng buộc duy nhất của mã bài để xử lý hai import cạnh tranh. Nếu thất bại, rollback DB và dọn file thuộc lần import đó.
4. Sau commit mới enqueue phát hành test. Lưu trạng thái bền vững để phục hồi khi enqueue thất bại; tác vụ phục hồi các bước đang chờ phải idempotent.
5. Worker gọi cơ chế release hiện có và ghi version/checksum. Chỉ chuyển sang gửi chấm sau khi release hợp lệ và đường dispatch của judge sử dụng được release này. Với cấu hình dữ liệu local, phải xác minh đường chia sẻ dữ liệu hiện có trước khi gửi.
6. Tạo duy nhất một `Submission` và `SubmissionSource` trong transaction, dưới tài khoản người upload. Lưu liên kết submission trước khi gửi chấm.
7. Gửi qua cơ chế judge hiện có. Worker đối chiếu trạng thái submission trước khi retry; dùng lại cùng submission nếu cần phục hồi dispatch. Không hứa exactly-once qua biên mạng; mục tiêu là không tạo submission trùng và không gửi lại khi hệ thống đã ghi nhận đang chấm hoặc đã kết thúc.
8. Trang trạng thái lấy verdict hiện tại từ submission. Chuyển `FINISHED` khi submission kết thúc, kể cả không AC.

Giữ bài ở trạng thái ẩn trong toàn bộ luồng. Chặn thay dữ liệu test/đổi mã bài trong giai đoạn tạo, phát hành và kiểm chứng để submission dùng đúng release; vẫn cho phép xem trạng thái. Sau khi kết thúc hoặc lỗi đã dừng tác vụ, người quản lý có thể sửa bài. Nếu sửa test sau lần kiểm chứng thì đánh dấu kết quả cũ thuộc release trước, không trình bày như kiểm chứng dữ liệu mới.

## 7. Hoàn tác, retry và quyền truy cập

### Hoàn tác và retry

- Lỗi kiểm tra ZIP: báo tại upload, không tạo bài.
- Mã bài trùng: báo tại form; kiểm tra lại ở commit để xử lý race.
- Lỗi tạo bài: rollback model; dọn staging và file vừa tạo theo quyền sở hữu import, không xóa thư mục của bài đã tồn tại.
- Lỗi sau commit: giữ bài ẩn; retry từ bước thất bại, không tạo bài lần nữa.
- Lỗi phát hành: không tạo submission kiểm chứng trước khi phát hành thành công.
- Lỗi gửi chấm: giữ và dùng lại submission đã tạo.
- Worker chết: phục hồi bằng trạng thái bền vững và claim có thời hạn; tiến trình dọn xử lý staging mồ côi.
- Bấm xác nhận/retry nhiều lần: khóa bản ghi và kiểm tra trạng thái; trả về cùng trang trạng thái.

### Quyền

Thêm permission `judge.import_problem_package`, chỉ cấp theo chính sách quản trị. Mỗi bước xác nhận/retry kiểm tra quyền import và quyền tạo/quản lý bài tương ứng của hệ thống hiện tại.

Trước khi tạo bài, người upload và quản trị viên có quyền phù hợp được xem bản nháp. Sau khi tạo, quyền quản lý bài quyết định quyền xem trạng thái chi tiết, tải ZIP và code chuẩn. Kiểm tra quyền trên từng request, không dùng URL storage công khai.

Code chuẩn và ZIP không xuất hiện trong public media hoặc release test. Submission kiểm chứng dùng chính sách nguồn riêng tư; lúc triển khai phải kiểm tra đường xem source của submission để quyền mặc định sau khi công khai bài không làm lộ code chuẩn. Người dùng chỉ đọc editorial khi quy tắc hiển thị `Solution` cho phép.

## 8. Kiểm thử và tiêu chí nghiệm thu

### Bộ đọc và metadata

- Gói có thư mục bọc và gói ở gốc đều tạo cùng manifest.
- Gói mẫu nhận diện đúng tên, 1 giây, 512 MB và 20 cặp test.
- Ghép test đúng, sắp xếp 2 trước 10, giữ nguyên byte input/output.
- Báo lỗi thiếu file, input/output lẻ, gốc nhập nhằng, UTF-8 không hợp lệ, file trùng, ZIP hỏng, đường dẫn không hợp lệ và vượt giới hạn thực tế khi đọc.
- Metadata không nhận diện được phải nhập; giá trị người dùng sửa là giá trị cấu hình cuối cùng.

### Tạo bài và quyền

- Tạo đúng model, bài/editorial ẩn, tác giả là người upload, code chuẩn riêng và không nhân đôi code trong editorial.
- Kiểm tra 512 MB chuyển thành 524288 KiB; 20 test có trọng số bằng nhau.
- Sinh cấu hình hợp lệ và release chỉ chứa dữ liệu chấm.
- Từ chối người thiếu quyền và người truy cập bản nháp/file của người khác.
- Nguồn submission kiểm chứng vẫn riêng tư khi bài được công khai sau này.

### Lỗi và cạnh tranh

- Trùng mã giữa hai import không ghi đè dữ liệu.
- Double-confirm, retry và worker chạy lặp không tạo bài hoặc submission trùng.
- Lỗi file/DB dọn đúng dữ liệu của import; lỗi sau commit giữ bài ẩn.
- Giả lập lỗi enqueue, phát hành, dispatch và worker chết ở ranh giới commit; phục hồi từ trạng thái đã lưu.
- Chặn thay test trong lúc kiểm chứng và hiển thị release gắn với kết quả cũ sau khi sửa.
- Dọn bản nháp hết hạn và nguồn của bài đã xóa không tác động import còn dùng.

### Tích hợp judge

Upload gói mẫu, xác nhận form, phát hành test và chấm `solution.cpp` trên judge có runtime C++ đã chọn. Nghiệm thu khi có đúng một bài, một submission kiểm chứng và verdict AC trên 20 test. Thử lời giải sai để xác nhận trạng thái “import thành công, lời giải không AC”. Thử thiếu judge để xác nhận trạng thái chờ đúng.

Unit/integration test với mock không thay thế kiểm thử judge thật. Nếu môi trường chưa có worker, storage hoặc judge phù hợp, báo rõ bước chưa xác minh.

## 9. Trình tự tiếp theo

Người dùng duyệt bản đặc tả này trước khi lập kế hoạch triển khai. Kế hoạch sẽ kiểm tra các điểm tích hợp dispatch, chính sách nguồn submission, publish local/R2 và quyền tạo bài thực tế; sau đó chia công việc theo bộ đọc, dữ liệu, tác vụ, giao diện và kiểm thử.

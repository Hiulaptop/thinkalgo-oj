# Thiết kế trình soạn bài chung

Ngày: 2026-11-19
Trạng thái: Người dùng đã duyệt thiết kế ngày 2026-11-19. Bước tiếp theo là lập và duyệt kế hoạch triển khai; chưa triển khai production.

## 1. Mục đích và quyết định đã có

Người ra đề cần nhập đề bài, editorial và bộ test trong cùng một lần tạo, không phải lưu bài trước rồi tìm trang dữ liệu để upload test. Người có quyền trên site chính phải làm được việc này mà không cần quyền vào Django admin.

Người dùng đã chọn hướng 1: một trình soạn bài chung, dùng từ cả admin và site chính; admin tiếp tục cung cấp các chức năng quản trị nâng cao. Sau khi đọc phần bàn giao thiết kế, người dùng đã duyệt thiết kế bằng phản hồi “Duyệt” ngày 2026-11-19. Kế hoạch triển khai cần được bàn giao tiếp theo trước khi bắt đầu sửa code.

Các chi tiết chưa được người dùng chỉ định được ghi rõ là đề xuất của người thiết kế.

## 2. Các phương án

1. **Trình soạn chung (đã chọn):** nút thêm bài trong admin mở trình soạn trên site; các đường tạo thông thường và tạo trong tổ chức dùng cùng giao diện và nghiệp vụ. Ít logic trùng lặp và không yêu cầu staff cho người ra đề.
2. **Hai giao diện, một bộ xử lý (không chọn):** thêm upload test vào admin và duy trì form ngoài site riêng. Giữ trải nghiệm admin cũ nhưng phải duy trì hai giao diện.

Không xây đường tạo bài đặc biệt cho ZIP. ZIP chỉ là nguồn dữ liệu cho cùng bản nháp.

## 3. Phạm vi bản đầu — đề xuất

Có:
- Tạo bài mới từ nhập trực tiếp hoặc ZIP trọn gói.
- Soạn đề Markdown hoặc đính kèm PDF theo quyền hiện có; editorial Markdown là tùy chọn.
- Upload ZIP chỉ chứa test ngay khi tạo, tự ghép cặp input/output và xem cấu hình trước khi lưu.
- Đính kèm mã nguồn lời giải chuẩn và chọn runtime để kiểm chứng theo yêu cầu, không bắt buộc có mã nguồn để tạo bài.
- Lưu nháp, quay lại chỉnh sửa, thay bộ test từ cùng trình soạn.
- Dùng trình soạn chung cho phần thông thường khi sửa bài; cung cấp liên kết tới quản trị và cấu hình dữ liệu nâng cao.
- Giữ phân loại, điểm, partial scoring, visibility, người thử bài và giới hạn ngôn ngữ hiện có; không làm mất trường khi chuyển giao diện.
- Trạng thái lưu, đồng bộ test, kiểm chứng và công khai tách biệt.

Không có trong bản đầu:
- Import nhiều bài trong một ZIP; tự sinh output bằng chạy mã trên web server.
- Tự động hỗ trợ mọi cấu trúc thư mục, .inp/.ans hoặc tài nguyên ảnh tương đối trong Markdown.
- Soạn cấu hình interactive/custom grader/custom checker/subtask phức tạp trong luồng tạo nhanh. Những cấu hình đã có tiếp tục được quản lý bằng trang dữ liệu nâng cao; không được làm hỏng khi mở trình soạn chung.
- Thay thế toàn bộ admin, thay đổi định dạng Polygon, triển khai production hoặc chuyển đổi định dạng test của mọi bài cũ.
- Autosave mỗi lần gõ. Bản đầu lưu nháp rõ ràng bằng nút; có cảnh báo khi rời trang còn thay đổi chưa lưu.

## 4. Trải nghiệm tạo bài

Đề xuất một trang gồm các phần, không bắt người dùng đi qua wizard nhiều bước:

- **Thông tin:** mã bài, tên, phạm vi global/tổ chức (theo quyền), nhóm/tags, điểm, thời gian, bộ nhớ. Hiển thị MB, chuyển đổi đúng sang KB đang lưu.
- **Đề bài:** soạn/xem trước Markdown, PDF nếu có quyền. Nếu có PDF và Markdown, ghi rõ PDF là tài liệu đính kèm; không âm thầm xóa Markdown.
- **Editorial:** nội dung, tác giả, lịch công khai; mặc định không công khai, độc lập với đề bài.
- **Bộ test:** ZIP, kết quả phân tích, danh sách cặp được nhận, số test và dung lượng, thứ tự, điểm từng test, checker chuẩn. Thao tác áp dụng điểm đồng loạt để không phải sửa từng dòng.
- **Lời giải chuẩn:** file nguồn + runtime tương thích được chọn từ các runtime cấu hình trên hệ thống; không đoán runtime chỉ từ đuôi file. Không thực thi nguồn ngoài sandbox judge.
- **Kiểm tra trước khi dùng:** liệt kê lỗi/thiếu dữ liệu và trạng thái đồng bộ/kiểm chứng.

Hành động chính: **Lưu nháp**. Sau khi có bài và dữ liệu sẵn sàng: **Chấm lời giải chuẩn**, **Xem bài**, và **Công khai** nếu có quyền. Không gộp công khai vào Lưu.

ZIP trọn gói nằm ở đầu trang dưới dạng lối tắt **Điền từ ZIP**. Khi đã có nội dung, hiển thị các phần sẽ được thay thế; yêu cầu xác nhận trước khi áp dụng. Không ghi đè mặc định lên các phần không được chọn. Lỗi đọc ZIP không xóa nội dung hoặc bộ test đã tải trước đó. Upload test riêng chỉ thay phần test sau khi người dùng áp dụng kết quả.

Không hứa giữ lại file trong input của trình duyệt sau POST: upload thành công được giữ bằng mã tham chiếu server-side để không phải chọn lại khi trường khác bị lỗi.

Giao diện dùng template Jinja2, Martor và hệ thống style hiện có theo style.md; không thêm SPA/framework mới. Mobile không có cuộn ngang toàn trang; bảng test được giới hạn/cuộn trong vùng riêng. Thiết kế thị giác cụ thể giao cho bước triển khai, không có mockup được phê duyệt trong tài liệu này.

## 5. Các dạng ZIP

### ZIP bộ test

Chấp nhận cặp `<tên>.in` / `<tên>.out` trực tiếp trong một thư mục test duy nhất: ở gốc, `tests/`, hoặc dưới một thư mục bao ngoài duy nhất. Không trộn nhiều gốc. Sắp xếp tự nhiên: 1, 2, 10. Hiển thị thứ tự trước khi lưu.

Thiếu cặp, đường dẫn trùng/không an toàn, nhiều cấu trúc gốc mơ hồ: báo lỗi cụ thể, không bỏ qua test. ZIP test-only từ chối file không thuộc cặp test, ngoại trừ entry thư mục. Không lấy init.yml hay file thực thi upload làm cấu hình tin cậy.

Mặc định mỗi test có trọng số 1; tổng điểm bài vẫn là điểm ở phần thông tin. Cho phép chỉnh trọng số và chọn checker chuẩn bằng cấu hình hệ thống. Kiểm tra này xác nhận cấu trúc và cấu hình, không khẳng định output đúng.

### ZIP trọn gói

Giữ tương thích với cấu trúc đã triển khai: `statement.md`, `editorial.md`, `solution.cpp`, `tests/*.in`, `tests/*.out`, ở gốc hoặc một thư mục bao ngoài.

Mở rộng: chỉ `statement.md` là phần nội dung bắt buộc của gói; editorial, source và tests có thể thiếu để nhập một bản nháp chưa hoàn chỉnh. Nếu có test thì phải có cặp đầy đủ. Nếu có source thì chọn runtime ở form trước khi chấm. Không bắt buộc C++ cho nguồn đính kèm thủ công.

Giữ cách đọc tiêu đề/TL/ML từ Markdown cũ dưới dạng gợi ý, không yêu cầu đúng câu tiếng Việt để tạo bài. Khi không đọc được, giữ giá trị người dùng đã nhập hoặc yêu cầu nhập trước khi bài sẵn sàng; không tự chọn thời gian/bộ nhớ không được hiển thị. Trường trong form sau khi người dùng xác nhận là dữ liệu có thẩm quyền.

Không hỗ trợ file lạ một cách âm thầm: báo tên file không hỗ trợ và từ chối áp dụng gói để người dùng biết tài nguyên nào chưa được nhập.

## 6. Bản nháp, lưu và độ bền dữ liệu

Phân biệt:
- **Upload tạm:** chưa tạo Problem; owner và phạm vi tổ chức được giữ server-side, có thời hạn 24 giờ và giới hạn dung lượng. Đọc/xóa/chọn lại đều kiểm tra quyền.
- **Bài nháp:** Problem thực sự, is_public=False, lưu bền đề/editorial/cấu hình và tham chiếu upload đã nhận. Có thể mở lại bằng trình soạn. Chưa có test vẫn được lưu nếu metadata bắt buộc của model hợp lệ.
- **Test sẵn sàng:** có bộ dữ liệu hợp lệ đã cài đặt và, khi chế độ R2 được bật, release đã publish thành công.

Không biến một is_public=False có sẵn thành dấu hiệu duy nhất của bản nháp: bài ẩn dùng trong contest vẫn là bài chấm được. Dùng trạng thái authoring/readiness riêng cho các bài đi qua luồng mới; bài cũ không bị đánh dấu thiếu dữ liệu hàng loạt.

Dịch vụ chung kiểm tra và lưu Problem, Solution, cấu hình testcase, quyền tác giả/curator, tổ chức và bản ghi operation. View chỉ bind/validate/render; admin không có đường nghiệp vụ riêng. Không import formset của view vào utility để xử lý danh sách test; có validator nghiệp vụ chung với giới hạn rõ ràng.

Database và filesystem/R2 không phải một transaction. Không hứa rollback xuyên cả ba. Trước khi ghi DB, upload được kiểm tra và lưu staging riêng bất biến. Khi DB commit, ghi nhận cùng transaction một operation bền vững tham chiếu staging. Worker cài bộ test và publish release, có retry và đối soát. Operation pending vẫn tìm lại được nếu enqueue lỗi; lưu nháp không phụ thuộc broker đang khỏe.

Mỗi lần lưu có token chống lặp; double-click hoặc gửi lại request không tạo hai bài. Có revision để từ chối ghi đè bằng form cũ và báo người dùng tải lại, thay vì mất thay đổi của người khác.

Staging của operation đã commit không bị cleanup upload hết hạn. Cleanup chỉ xóa đối tượng không còn tham chiếu; nếu worker chết giữa cài đặt và đánh dấu thành công, retry/đối soát xác định được bộ dữ liệu thuộc operation nào. Các artifact cũ được giữ đến khi phiên bản mới được xác nhận an toàn.

Thay test của bài đã có dùng cùng quy trình staging, giữ bộ cũ cho đến khi bộ mới được kích hoạt nhất quán. Trong khoảng cài đặt/publish, chặn nộp mới theo readiness và không làm mất dữ liệu của bài nộp đang chạy; tích hợp với cơ chế release bất biến hiện tại. Chi tiết lưu trữ/versioning do người triển khai lựa chọn sau khi kiểm tra cả chế độ R2 và non-R2. Nếu không bảo đảm bài đang chấm dùng được phiên bản cũ, phải từ chối kích hoạt cho đến khi chúng kết thúc, không thay file dưới tiến trình đang chạy.

## 7. Trạng thái và kiểm chứng

Ba nhóm độc lập:
- Lưu bài: chưa lưu / đã lưu / xung đột hoặc lỗi lưu.
- Dữ liệu: chưa có / đang chuẩn bị / đang đồng bộ / sẵn sàng / lỗi có thể retry.
- Kiểm chứng: chưa chạy / đang chờ / đang chấm / kết quả / lỗi hạ tầng.

Có thể sửa đề và editorial khi đang đồng bộ/chấm. Thay đổi ảnh hưởng kết quả chấm (test, checker, runtime, source, TL/ML, điểm test, cấu hình grader, mã bài) phải bị khóa trong operation hoặc lượt kiểm chứng liên quan, với lỗi form dễ hiểu, không HTTP 500. Cả admin và trang dữ liệu nâng cao tuân theo guard chung.

Kiểm chứng chỉ chạy sau khi dữ liệu sẵn sàng, do người dùng bấm; không bắt buộc AC để lưu hoặc công khai. Ghi rõ kết quả thuộc revision dữ liệu/cấu hình/source nào; khi chúng đổi thì đánh dấu kết quả cũ, không tiếp tục hiển thị là đã kiểm chứng phiên bản hiện tại. Không auto-submit lại mỗi lần lưu đề bài. Retry hạ tầng và yêu cầu chấm lại có ngữ nghĩa riêng; không tạo submission trùng khi retry cùng một lượt.

Không tự công khai đề/editorial khi AC. Chỉ công khai bài khi có quyền visibility, metadata/đề hợp lệ và dữ liệu sẵn sàng; chưa chạy kiểm chứng hoặc non-AC tạo cảnh báo yêu cầu xác nhận, không giả là đã đạt kiểm chứng. Cũng chặn đưa bản nháp chưa sẵn sàng vào contest/nộp trực tiếp bằng backend, không chỉ ẩn nút trên giao diện.

## 8. Quyền và tổ chức

Tái sử dụng quyền hiện có, không suy quyền từ việc có thể vào admin:
- Global: add_problem cho tạo, is_editable_by cho sửa; cấp quyền vai trò người ra đề gồm add_problem + edit_own_problem để sau khi tạo có thể quay lại chỉnh sửa. Kiểm tra khả năng quay lại này trước khi nhận lưu, báo thiếu quyền rõ ràng thay vì tạo rồi trả 403.
- Tổ chức: create_organization_problem và quyền quản trị tổ chức hiện có; không bắt thêm add_problem global chỉ vì dùng chung trình soạn. Trường hợp chủ thể tạo được nhưng không được quay lại sửa phải được giải quyết rõ bằng quyền vai trò hiện hành, không nới quyền sửa mọi bài.
- ZIP trọn gói: giữ import_problem_package; upload ZIP test-only là một phần quyền tạo/sửa bài thông thường, không đòi quyền import gói.
- PDF: upload_file_statement; testcase vượt hard limit: create_mass_testcases. Luôn có trần an toàn kỹ thuật ngay cả người được phép nhiều test.
- Công khai: change_public_visibility và phạm vi của bài. Người tạo không có quyền này vẫn lưu và chuẩn bị dữ liệu được.

Owner/phạm vi của upload không nhận tin cậy từ hidden field. Mỗi POST kiểm tra lại quyền và tổ chức. Bài tạo từ đường tổ chức luôn giữ organization và is_organization_private; người dùng không sửa organization ID trong POST để chuyển phạm vi.

Quota số bài được tính khi lưu nháp thành Problem, không phải lúc đọc ZIP. Quota storage tính cả upload staging đã giữ và dữ liệu đang hoạt động, có hạn mức tạm riêng cho replacement; không cho upload không giới hạn để lách quota. Kiểm tra/reserve dưới khóa khi commit để hai request không vượt quota. Thông báo tính cả phần upload đang chờ. Giá trị hạn mức kỹ thuật và temporary replacement budget để cấu hình, không hardcode theo UI.

## 9. An toàn upload

Dùng kiểm tra phía server cho path traversal, symlink, entry trùng, ZIP mã hóa, ZIP lỗi, UTF-8 sai, số entry, kích thước nén/giải nén và dung lượng từng file. Xử lý theo luồng có giới hạn, không extractall. Mặc định kế thừa trần đang có: 100 MiB nén, 1 GiB tổng giải nén, 10.000 entry, 5 MiB mỗi tài liệu/source, 256 MiB mỗi file test; cấu hình được và nhất quán giữa hai loại ZIP.

Mã nguồn và test nằm trong storage riêng tư; download kiểm tra quyền, không phát qua public media/CDN. PDF theo chính sách media hiện có; không coi PDF là nơi chứa lời giải chuẩn hay test. Không chạy compiler/checker upload trên web/Celery host; chạy nguồn kiểm chứng trong sandbox judge hiện tại.

CSRF cho mutation, POST cho áp dụng/công khai/retry, lỗi trả về không lộ đường dẫn server hoặc credentials. Không đọc nội dung test/source để đưa vào dịch vụ ngoài.

## 10. Tích hợp và tương thích

- Admin Add problem chuyển tới trình soạn chung; admin change có liên kết nổi bật mở trình soạn, giữ form nâng cao cho metadata đặc biệt. Advanced save tuân theo guards/readiness/visibility chung.
- URL create/edit hiện tại được giữ hoặc redirect tương thích. Đường tạo trong tổ chức giữ nguyên phạm vi.
- Trang dữ liệu nâng cao và Polygon giữ chức năng; khi sửa test/cấu hình phải cập nhật revision/readiness và làm cũ kết quả kiểm chứng. Không âm thầm chuyển cấu hình phức tạp về standard khi lưu nội dung từ trình soạn.
- Giữ dữ liệu Problem/Solution/ProblemData/ProblemTestCase hiện có. Không đọc lại ZIP để ghi đè các nội dung đã sửa.
- Legacy ProblemPackageImport được giữ để tra cứu/download/kết quả. Draft chưa xác nhận còn hạn được mở thành draft của trình soạn; pending jobs cũ được drain hoặc chuyển trạng thái có kiểm soát trước khi bỏ đường xử lý cũ. Không đổi state hàng loạt rồi chạy lại nguồn vô tình.
- Cần migration cho upload/operation/revision/readiness và source kiểm chứng độc lập với ZIP. Tên model/cách tách bảng để người triển khai chọn; không ép ProblemPackageImport gánh mọi loại draft mới.
- Tránh tạo bài qua confirm_import và bỏ qua hook tổ chức. Dùng một dịch vụ authoring với context quyền/tổ chức rõ ràng và các side effect sau commit.

## 11. Tiêu chí chấp nhận

1. Người không phải staff, có quyền phù hợp, tạo bài kèm đề, editorial, test trong cùng trang; không cần vào admin hay tạo xong mới upload test.
2. Admin Add dẫn đến cùng luồng; đường tổ chức không mất phạm vi hay vượt quota.
3. Lưu không có test tạo được nháp; quay lại còn đề, editorial và upload đã nhận. Bản nháp không sẵn sàng không thể được nộp/chèn contest/công khai bằng POST trực tiếp.
4. Test ZIP tự ghép đúng thứ tự, hiển thị lỗi cặp cụ thể; số test lớn hợp lệ không vướng absolute_max ngầm của formset.
5. ZIP trọn gói chỉ điền các phần người dùng xác nhận; ZIP lỗi không xóa chỉnh sửa hoặc test cũ.
6. PDF giữ đúng tham chiếu; thất bại upload không tạo thư mục đích mồ côi chặn retry.
7. Double-click, hai tab sửa đồng thời, worker bị kill, broker/R2 ngừng hoạt động, hết quota và publish lỗi đều có trạng thái rõ và đường phục hồi, không tạo bài/submission trùng hoặc mất bộ test đang hoạt động.
8. Chỉnh metadata/editorial không liên quan không bị lỗi 500 khi chấm; thay đổi ảnh hưởng chấm được chặn hoặc đánh dấu kết quả cũ đúng phiên bản.
9. Test/source không tải được bởi người không có quyền; kiểm thử ZIP độc hại và giới hạn dung lượng.
10. Bài cũ, Polygon và cấu hình dữ liệu nâng cao vẫn dùng được; không reset checker/grader/subtask khi chỉ sửa đề.
11. Có test service, view/quyền, lỗi/retry/concurrency và smoke test giao diện; kiểm tra cả R2 và non-R2, database production-compatible cho các khóa/quota.

## 12. Việc giao cho bước lập kế hoạch

Chọn schema tối thiểu cho upload/draft/operation, chỗ đặt service, chiến lược giữ và kích hoạt dữ liệu phù hợp release hiện có, cơ chế durable enqueue/recovery và tích hợp submission/contest gates. Phân tách migration tương thích trước khi gỡ guards/flow cũ. Không nối thêm một service riêng cho mỗi loại giao diện.

Đây là thay đổi nhiều phần, không phải vá nút ZIP. Ưu tiên triển khai theo lát cắt: tạo/lưu nháp + upload test trong cùng giao diện; tiếp đó ZIP trọn gói và kiểm chứng dùng chung. Tuy nhiên chỉ coi tính năng hoàn tất khi đạt các tiêu chí chấp nhận trên. Chưa commit, triển khai hoặc kết nối VPS nếu chưa được yêu cầu.

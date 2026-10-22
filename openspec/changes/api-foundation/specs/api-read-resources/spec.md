# Spec Delta

## Purpose

Các tài nguyên đọc của API đợt 1 cho frontend, kèm quy tắc quyền truy cập của từng tài nguyên, bảo đảm dữ liệu trả về giống những gì người dùng được thấy trên trang Jinja tương ứng.

## ADDED Requirements

### Requirement: Thông tin người dùng hiện tại
API SHALL có tài nguyên `me` trả thông tin tối thiểu của người dùng đang đăng nhập hoặc trạng thái ẩn danh.

#### Scenario: Ẩn danh
- **WHEN** gọi `me` không đăng nhập
- **THEN** nhận `authenticated: false` mà không lỗi

#### Scenario: Đã đăng nhập
- **WHEN** gọi `me` khi đã đăng nhập
- **THEN** nhận tên đăng nhập, tên hiển thị, avatar và cờ cho biết người dùng có đang tham gia một kỳ thi hay không

### Requirement: Danh sách đề bài theo quyền
API SHALL trả danh sách đề chỉ gồm các đề người dùng được xem, hỗ trợ tìm kiếm, lọc theo nhóm/loại/chủ đề/khoảng điểm, ẩn đề đã giải và sắp xếp theo các khoá mà trang Jinja hỗ trợ.

#### Scenario: Đề riêng tư của tổ chức
- **WHEN** người dùng không thuộc tổ chức yêu cầu danh sách
- **THEN** các đề riêng tư của tổ chức không xuất hiện

#### Scenario: Đang trong kỳ thi
- **WHEN** người dùng đang tham gia một kỳ thi
- **THEN** danh sách tuân theo cùng quy tắc hạn chế như trang Jinja

#### Scenario: Ẩn đề đã giải
- **WHEN** đăng nhập và đặt tham số ẩn đề đã giải
- **THEN** các đề người dùng đã AC không xuất hiện

### Requirement: Chi tiết đề bài
API SHALL trả chi tiết đề (nội dung đề dạng đã render an toàn, giới hạn, ngôn ngữ cho phép, trạng thái đã giải của người xem) chỉ khi người dùng được xem đề đó.

#### Scenario: Đề công khai
- **WHEN** người dùng bất kỳ yêu cầu một đề công khai
- **THEN** nhận chi tiết đề

#### Scenario: Đề đã xoá
- **WHEN** yêu cầu một đề đã bị xoá mà người dùng có quyền xem
- **THEN** nhận phản hồi cho biết đề đã bị xoá, giống như trang Jinja

### Requirement: Danh sách và chi tiết bài nộp theo quyền
API SHALL trả danh sách bài nộp theo cùng quy tắc hiển thị của trang Jinja và chỉ trả mã nguồn và kết quả từng test khi người xem được phép.

#### Scenario: Bài nộp của người khác
- **WHEN** người dùng xem chi tiết bài nộp của người khác mà không có quyền xem mã nguồn
- **THEN** phản hồi không chứa mã nguồn

#### Scenario: Bài nộp trong kỳ thi
- **WHEN** bài nộp thuộc một kỳ thi đang diễn ra và người xem không phải ban tổ chức hay chủ bài nộp
- **THEN** bài nộp không xuất hiện hoặc bị ẩn đúng như trang Jinja

### Requirement: Bảng xếp hạng người dùng
API SHALL trả bảng xếp hạng người dùng công khai gồm hạng, điểm, số đề đã giải và rating, theo cùng cách tính của trang Jinja, và SHALL loại người dùng không công khai.

#### Scenario: Sắp xếp mặc định
- **WHEN** gọi không tham số
- **THEN** thứ tự trùng với trang `/users/`

### Requirement: Blog
API SHALL trả danh sách và chi tiết bài viết blog theo cùng quy tắc hiển thị (đã xuất bản, theo tổ chức) của trang Jinja.

#### Scenario: Bài chưa xuất bản
- **WHEN** người dùng không phải tác giả/quản trị yêu cầu bài chưa xuất bản
- **THEN** nhận 404

### Requirement: Tương đương với bản Jinja
Với cùng người dùng và cùng điều kiện lọc, nội dung và thứ tự của API SHALL trùng với trang Jinja tương ứng.

#### Scenario: So sánh song song
- **WHEN** so sánh danh sách đề của API và trang `/problems` cho cùng người dùng, cùng bộ lọc
- **THEN** cùng tập đề theo cùng thứ tự

# ZIP Import Through Existing Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute inline as previously requested; do not delegate.

**Goal:** Upload ZIP để điền dữ liệu vào trang tạo bài hiện có; chỉ lưu bài, test và editorial khi người dùng bấm Tạo.

**Architecture:** Bộ đọc ZIP cung cấp dữ liệu ban đầu và một tham chiếu upload riêng tư. `ProblemCreate` dùng `ProblemEditForm` và formset editorial để validate/lưu. Phần test dùng chung form, formset, compiler và dịch vụ lưu với trang dữ liệu test hiện tại.

**Tech Stack:** Django 4.2, Jinja2, Martor, Celery và storage hiện có.

**Spec:** Thiết kế điều chỉnh trong hội thoại, được người dùng xác nhận “đúng vậy”: upload chỉ điền dữ liệu; nút Tạo hiện có mới lưu. Kế hoạch này thay thế phần giao diện và tạo bài riêng trong `2026-11-16-zip-problem-import.md`.

## Global Constraints

- Không tạo form metadata hoặc trang preview riêng.
- Dùng `ProblemEditForm`, Martor và Select2 hiện có.
- Dùng `ProposeProblemSolutionFormSet` cho editorial.
- Dùng `ProblemDataForm`, `ProblemCaseFormSet` và `ProblemDataCompiler` cho test.
- Chỉ tạo mới; mã trùng là lỗi tại form hiện có.
- Upload chưa tạo Problem, Solution, ProblemData hoặc submission.
- Dữ liệu người dùng sửa trên form có ưu tiên hơn dữ liệu suy ra từ ZIP.
- Giữ các bài/import đã tồn tại và nguồn riêng tư; không xóa dữ liệu để đổi giao diện.
- Giữ code chuẩn, chấm thử và quyền nguồn riêng tư; chạy sau khi lưu/phát hành thành công.
- Không commit/push hoặc deploy chỉ vì hoàn tất kế hoạch; cần yêu cầu tương ứng.

## 1. Chuẩn bị upload để điền form hiện có

**Files:** `judge/views/problem.py`, `judge/utils/problem_package_import.py`, `templates/problem/create.html`; test mới `judge/tests/test_problem_package_editor.py`.

**Interface:** `get_owned_draft(import_id, user) -> ProblemPackageImport`: kiểm tra owner, quyền import, expiry, checksum và chưa gắn bài. Không chấp nhận đường dẫn filesystem từ client.

- [ ] Viết test POST `action=load_package` với ZIP vào `problem_create`, assert không có bài mới và form trả về là ProblemEditForm.

```python
before = Problem.objects.count()
response = self.client.post(reverse('problem_create'), {
    'action': 'load_package', 'package': self.package_upload,
})
self.assertEqual(response.status_code, 200)
self.assertEqual(Problem.objects.count(), before)
self.assertIsInstance(response.context['form'], ProblemEditForm)
self.assertEqual(response.context['form']['memory_limit'].value(), 524288)
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_editor --noinput`; xác nhận test thất bại vì luồng chưa có.
- [ ] Thêm ô file và nút `name="action" value="load_package"` vào trang create; nút này cho phép bỏ qua required fields của trình duyệt bằng `formnovalidate`. Nút Tạo dùng `action=create`. Server chỉ xử lý nhánh đọc ZIP nếu action đúng.
- [ ] Giữ `create_draft` và parser; chuẩn hóa initial cho form chuẩn:

```python
initial.update({
    'description': manifest['statement'],
    'name': manifest['name'],
    'time_limit': manifest['time_limit'],
    'memory_limit': manifest['memory_mb'] * 1024 if manifest['memory_mb'] is not None else None,
})
```

- [ ] Render lại create template với form unbound có initial, draft UUID hidden và dòng tóm tắt số test. Không đặt initial lên form bound rồi mong nó thay thế POST. Khi load ZIP mới, giữ các trường không được ZIP cung cấp từ POST đã chuẩn hóa; thông báo rõ các trường nội dung vừa thay thế.
- [ ] Kiểm thử ZIP lỗi, quyền sai, draft khác user, upload lại và không nhận diện được metadata; run module đến PASS.

## 2. Dùng editorial formset và đường tạo bài chuẩn

**Files:** `judge/views/problem.py`, `judge/forms.py`, `templates/problem/create.html`, `templates/problem/editor.html`, `judge/utils/problem_package_import.py`; cùng module test task 1.

**Interface:** `attach_package(record, problem, data_form, case_formset) -> None` được định nghĩa ở task 3. Hàm không tự tạo Problem hoặc Solution.

- [ ] Viết test người dùng sửa description/name/editorial sau upload; POST Tạo phải lưu giá trị sửa, còn POST lỗi code giữ nguyên cả ba nội dung và draft UUID.
- [ ] Đọc prefix/management form và phần render editorial hiện tại; trích partial dùng chung nếu cần, không sao chép editor thứ hai. Trên create không có ZIP, giữ hành vi tạo thủ công và cho phép editorial trống.
- [ ] Dùng `ProposeProblemSolutionFormSet(instance=unsaved_problem, initial=...)` với đúng cấu hình extra/min_num hiện có. POST bind lại từ request.POST, không điền lại editorial từ manifest làm mất sửa đổi.
- [ ] Trong một revision transaction, khóa draft, validate tất cả form trước khi gọi save. Giữ tác giả/curator, ngôn ngữ mặc định, date, quyền upload statement và revision của ProblemCreate hiện có. Lưu Solution bằng formset và cưỡng chế is_public=False cho import.

```python
problem = form.save()
solution_formset.instance = problem
solution_formset.save()
attach_package(record, problem, data_form, case_formset)
```

- [ ] Gắn draft với problem trong transaction; on_commit mới enqueue phát hành/kiểm chứng. Confirm lặp trả về cùng bài. Khi lỗi test/file, hoàn tác DB và dọn đúng file của lần tạo này.
- [ ] Run test create thủ công + import sửa dữ liệu + trùng mã + double submit.

## 3. Dùng chung pipeline dữ liệu test

**Files:** `judge/views/problem_data.py`, file mới `judge/utils/problem_data_save.py`, `judge/utils/problem_package_import.py`; test mới `judge/tests/test_problem_package_data.py`.

**Interfaces:**
- `build_package_test_forms(record, problem, user) -> (ProblemDataForm, ProblemCaseFormSet)`: dựng bound forms từ manifest và test archive tạm.
- `save_problem_data(problem, data_form, case_formset, valid_files, *, publish=True) -> ProblemData`: chỉ nhận forms đã valid; lưu data/cases, xử lý deleted_objects, compiler, kiểm tra feedback; enqueue publish sau commit nếu publish=True.
- `attach_package(record, problem, data_form, case_formset) -> None`: gọi hàm lưu chung publish=False, liên kết import rồi enqueue worker sau commit.

- [ ] Test 20 cặp tạo đúng input/output và trọng số, thiếu output bị từ chối, số test/quyền/checker áp dụng như trang test thường.
- [ ] Trích phần validate giới hạn và save từ ProblemDataView để dùng chung; giữ đầy đủ quota tổ chức khi gọi trong context tổ chức. Không thay đổi hành vi save thông thường bằng cách bỏ validation hoặc giới hạn.
- [ ] Chuẩn bị test archive bằng tên đã kiểm tra. Dựng FILES phía server; không cố điền file input trên browser. Đặt management fields đúng prefix và số lượng test, truyền valid_files cho formset.

```python
case_values = {
    'order': index, 'type': 'C', 'input_file': input_name,
    'output_file': output_name, 'points': 1, 'is_pretest': False,
}
```

- [ ] Chạy validation trước tạo bài với unsaved instance khi khả thi; những kiểm tra cần PK chạy trong transaction sau form.save. Lỗi formset trả về trang create và giữ draft.
- [ ] Kiểm tra compiler.feedback thay vì chỉ trông chờ exception, tránh báo thành công khi không có init.yml. Chỉ có một tác vụ phát hành trong luồng import, không enqueue từ cả view lẫn worker.
- [ ] Sau tạo chuyển sang `problem_edit`; trang test hiện có phải hiển thị được toàn bộ archive/cases. Run test pipeline và regression ProblemDataView.

## 4. Code chuẩn và trạng thái trong editor hiện có

**Files:** `judge/views/problem.py`, `templates/problem/editor.html`, `judge/tasks/problem_package.py`, `judge/views/problem_package.py`; test task 1 và worker hiện có.

- [ ] Test editor bài đã import hiển thị link tải code/ZIP, trạng thái phát hành, submission và retry có quyền.
- [ ] Dùng khu vực thông báo/actions của editor hiện có. Giữ lựa chọn runtime C++ cho code chuẩn ở đây hoặc trường bổ sung riêng trong create; không tạo lại bộ trường metadata. Runtime phải thuộc allowed_languages của bài.
- [ ] Chấm bằng submission workflow hiện có sau release thành công; metadata/editorial lưu từ form, source chuẩn lấy từ private draft.
- [ ] Retry dùng cùng bài/submission, có POST+CSRF và kiểm tra quyền. Không khóa việc mở editor chỉ để đọc trạng thái; lỗi guard cần hiển thị thông báo thay vì HTTP 500.
- [ ] Run test private source, retry và verdict non-AC; ghi rõ nếu môi trường không có judge thật.

## 5. Chuyển tiếp route cũ và gỡ form trùng

**Files:** `judge/views/problem_package.py`, `judge/package_urls.py`, `templates/problem/package-upload.html`, `templates/problem/package-detail.html`, `docs/zip-problem-import.md`.

- [ ] Test GET upload cũ redirect về problem_create; draft cũ mở create với initial; import đã tạo bài mở problem_edit. POST cũ không được mất payload do redirect 302 âm thầm: trả thông báo dùng trang mới hoặc chuyển adapter tới đúng handler.
- [ ] Gỡ PackageMetadataForm và template riêng sau khi test điều hướng đạt. Giữ download/retry handlers có quyền và model chứa record lịch sử.
- [ ] Gỡ đường confirm tự tạo Problem/Solution thủ công; giữ helper archive, ownership và cleanup đang dùng.
- [ ] Cập nhật hướng dẫn: chọn ZIP trên create → kiểm tra editor → Tạo → editor/test bình thường. Ghi kế hoạch cũ đã được thay thế về luồng UI.
- [ ] Run toàn bộ test ZIP và test tạo/sửa bài liên quan; `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `git diff --check`.

## Nghiệm thu

- [ ] Upload gói mẫu chưa làm tăng số bài trong DB.
- [ ] Đề xuất hiện trong Martor, editorial trong editor lời giải sẵn có; không còn trang metadata riêng.
- [ ] Bấm Tạo lưu được đề + editorial người dùng sửa, đủ 20 test; lỗi form không làm mất draft.
- [ ] Mở trang dữ liệu test và sửa bằng component hiện có thành công.
- [ ] Bài import trước thay đổi vẫn quản lý được; tải nguồn vẫn private.
- [ ] Test tay luồng tạo bài thủ công, upload lỗi, nhập lại ZIP, refresh và double submit.
- [ ] Báo riêng kết quả publish/judge thật với mock test. Không coi test parser đạt là toàn bộ tính năng hoàn tất.

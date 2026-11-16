# ZIP Problem Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo bài ẩn từ ZIP gồm đề, tests, editorial và code chuẩn, rồi kiểm chứng code bằng judge.

**Architecture:** Bộ đọc ZIP thuần Python tạo manifest; dịch vụ import quản lý DB và staging riêng tư. Worker phát hành dữ liệu, gửi một submission và phục hồi theo trạng thái bền vững. Giao diện upload, preview và trạng thái dùng Jinja2 hiện có.

**Tech Stack:** Python, Django >=4.2,<5, Celery, MariaDB, Jinja2, storage filesystem riêng tư, cơ chế release R2 và bridge hiện có.

**Spec:** `docs/superpowers/specs/2026-11-16-zip-problem-import-design.md`

## Global Constraints

- Mỗi ZIP chứa một bài. Phiên bản đầu chỉ tạo mới; mã bài trùng là lỗi.
- Tạo bài và editorial ở trạng thái ẩn. Người quản lý quyết định công khai sau đó.
- ZIP upload 100 MiB; tổng dữ liệu giải nén 1 GiB; tối đa 10.000 file; mỗi file bắt buộc dạng văn bản tối đa 5 MiB; mỗi file test tối đa 256 MiB.
- Bản nháp chưa xác nhận hết hạn sau 24 giờ.
- Standard input/output, checker standard, mỗi test trọng số 1, điểm mặc định 100, partial=True.
- Không chạy generator/validator, không nối code chuẩn vào editorial, không đưa nguồn vào release test.
- `style.md` là chuẩn giao diện. Không thêm dependency nếu thư viện chuẩn và dependency hiện tại đáp ứng.
- Chỉ commit khi người dùng yêu cầu; các checkpoint dưới đây là điểm review, không phải lệnh tự commit.
- Thực hiện test cạnh tranh trên MariaDB; SQLite không chứng minh tính đúng của khóa hàng.

## Phát hiện ảnh hưởng triển khai

1. `ProblemDataCompiler.generate()` ghi file và nuốt `ProblemDataError` vào feedback. Staging dùng `ProblemDataCompiler(...).make_init()` và `yaml.safe_dump()` để lỗi đi lên trước commit.
2. `judge/bridge/judge_handler.py:get_related_submission_data()` lấy release hiện tại của bài, không pin theo submission. Khóa mutation dữ liệu trong lúc kiểm chứng, gồm cả admin, Polygon update và lệnh publish/purge.
3. `Submission.judge()` không return kết quả `judge_submission`; `judge_submission()` có thể ghi IE và trả False mà không raise. Adapter kiểm chứng phải refresh submission sau dispatch; không coi lời gọi không raise là thành công.
4. `Submission.can_see_detail()` cho phép xem source theo chính sách của bài. Submission chuẩn cần cờ riêng để chặn trước các nhánh ALWAYS/SOLVED/tester.
5. Production compose chưa chạy Beat; chỉ thêm beat_schedule không đủ. Thêm đúng một dịch vụ Beat để phục hồi và dọn bản nháp.
6. Release builder đóng gói thư mục bài. ZIP nguồn phải nằm ngoài `DMOJ_PROBLEM_DATA_ROOT` và public media.

## File map và hợp đồng chung

| File mới | Trách nhiệm |
|---|---|
| `judge/utils/problem_package.py` | Parse, kiểm tra ZIP, manifest và metadata |
| `judge/utils/problem_package_storage.py` | Private storage, staging, checksum và cleanup |
| `judge/models/problem_package.py` | Bản ghi import, trạng thái, quyền |
| `judge/utils/problem_package_import.py` | Confirm, tạo bài và retry |
| `judge/utils/problem_package_guards.py` | Khóa mutation bài và quyền truy cập import |
| `judge/tasks/problem_package.py` | Claim, publish, dispatch, reconcile, cleanup |
| `judge/problem_package_forms.py` | Upload và metadata form |
| `judge/views/problem_package.py` | Upload, preview, confirm, status, download, retry |
| `templates/problem/package-{upload,preview,status}.html` | Giao diện import |
| `judge/tests/problem_package_helpers.py` | Fixture ZIP nhỏ tự tạo, không phụ thuộc `/home/hlt/Documents/example` |

Các model xuất qua `judge/models/__init__.py`; tác vụ xuất qua `judge/tasks/__init__.py`. Migration tiếp theo dự kiến `0234_problem_package_import.py`, phụ thuộc `0233_problemdata_r2_release`; xác minh migration leaf tại lúc triển khai.

Hợp đồng bộ đọc (định nghĩa ở task 1):

```python
@dataclass(frozen=True)
class PackageLimits:
    upload_bytes: int = 100 * 1024**2
    expanded_bytes: int = 1024**3
    entries: int = 10000
    text_bytes: int = 5 * 1024**2
    test_bytes: int = 256 * 1024**2

@dataclass(frozen=True)
class TestPair:
    input_name: str
    output_name: str

@dataclass(frozen=True)
class PackageManifest:
    root: str
    statement: str
    editorial: str
    reference_source: str
    tests: tuple
    metadata: dict
    attachments: tuple
    source_sha256: str
    parser_version: int = 1

class PackageValidationError(ValueError):
    pass

def inspect_package(stream, limits: PackageLimits) -> PackageManifest:
    """Read bounded chunks; stream is binary and seekable. Never extractall()."""
```

Manifest chỉ giữ tên test, không giữ toàn bộ input/output trong RAM. Storage đọc lại entries đã kiểm tra khi tạo test archive và kiểm tra lại checksum trước confirm.

## Task 1: Bộ đọc ZIP và metadata

**Files:** Create `judge/utils/problem_package.py`, `judge/tests/problem_package_helpers.py`, `judge/tests/test_problem_package_parser.py`.

**Consumes:** binary seekable stream. **Produces:** các kiểu và `inspect_package` ở hợp đồng chung.

- [ ] Viết helper `make_package(files=None, wrapper='package/')` trả BytesIO ZIP với đề mẫu rút gọn, editorial, C++ và hai cặp test; files ghi đè/thêm theo mapping. Viết test trước:

```python
def test_natural_order_and_metadata(self):
    stream = make_package(files={
        'tests/10.in': b'1\n9\n', 'tests/10.out': b'1\n',
        'tests/2.in': b'1\n8\n', 'tests/2.out': b'1\n',
    })
    result = inspect_package(stream, PackageLimits())
    self.assertLess([p.input_name for p in result.tests].index('tests/2.in'),
                    [p.input_name for p in result.tests].index('tests/10.in'))
    self.assertEqual(result.metadata['memory_mb'], 512)
    self.assertEqual(result.metadata['time_limit'], 1)
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_parser`; expected failure do import/function chưa tồn tại.
- [ ] Triển khai kiểm tra kích thước upload; duyệt ZipInfo, reject encrypted/symlink/trùng/absolute/parent/backslash/NUL; đọc mọi file bằng chunks để kiểm tra tổng thực tế và CRC. Nhận diện root duy nhất, decode `utf-8-sig` cho ba file văn bản bắt buộc. Metadata chỉ nhận H1 và nhãn thời gian/bộ nhớ mẫu. Natural key dùng `re.split(r'(\d+)', name)` với token có type tag để tránh so int với str. Không suy luận pretest từ Markdown.

```python
def natural_key(name):
    return tuple((1, int(x)) if x.isdigit() else (0, x)
                 for x in re.split(r'(\d+)', name)) + ((0, name),)
```

- [ ] Thêm test root không bọc, thiếu output, file rỗng bắt buộc, test rỗng hợp lệ, invalid UTF-8, duplicate normalized entry, nhiều root, traversal, symlink, ZIP hỏng và giới hạn nhỏ qua `PackageLimits`. Assert tên lỗi và byte test không thay đổi.
- [ ] Run lại module; expected PASS. Review không giải nén hoặc allocate theo tổng declared size.

## Task 2: Model import và private storage

**Files:** Create `judge/models/problem_package.py`, `judge/utils/problem_package_storage.py`, `judge/tests/test_problem_package_storage.py`; modify `judge/models/__init__.py`, `judge/models/submission.py`, `judge/models/problem.py`, `dmoj/settings.py`; create migration `judge/migrations/0234_problem_package_import.py`.

**Consumes:** `PackageManifest`. **Produces:** `ProblemPackageImport`; `private_package_storage`; `store_package(upload, import_id) -> (name, sha256)`; `prepare_test_data(record, manifest) -> pathlib.Path`; `discard_staging(import_id) -> None`.

- [ ] Viết test private storage override sang TemporaryDirectory; assert không dùng default storage, không có public URL và code chuẩn vẫn tồn tại khi không render editorial.

```python
def test_import_defaults_to_private_draft(self):
    record = ProblemPackageImport.objects.create(owner=self.profile)
    self.assertEqual(record.state, 'AWAITING_CONFIRMATION')
    self.assertIsNone(record.problem_id)
    self.assertIsNone(record.submission_id)
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_storage`; expected FAIL trước model/storage.
- [ ] Model dùng UUID primary key; owner FK Profile; problem OneToOne nullable CASCADE; submission OneToOne nullable SET_NULL; source archive private FileField; reference_source TextField; reference_language nullable FK Language PROTECT; metadata/manifest JSONField; checksum/parser_version; timestamps/expires_at; state/failed_stage/error_code/error_message; release_version/release_sha256; lease_token UUID nullable/lease_until nullable; dispatch_started_at/dispatched_at nullable; retry_count. State choices đúng spec. Thêm `Submission.is_reference_verification = BooleanField(default=False)` và permission import vào `Problem.Meta.permissions`.
- [ ] Private storage subclass FileSystemStorage sử dụng `PROBLEM_PACKAGE_ROOT`; `url()` raise NotImplementedError. Settings mặc định root riêng ngoài media/problem_data và các giới hạn đúng spec. File key theo UUID, không theo tên client. Staging ở cùng filesystem với problem_data để atomic rename; marker ghi import UUID, không chứa nguồn chuẩn.

```python
def package_upload_to(instance, filename):
    return '%s/source.zip' % instance.pk

def url(self, name):
    raise NotImplementedError('Private package storage has no public URL')
```

- [ ] Tạo migration bằng `python manage.py makemigrations judge --name problem_package_import`; kiểm tra dependency và migration không kéo thay đổi không liên quan. Run test module và `python manage.py makemigrations --check --dry-run`.

## Task 3: Confirm và tạo bài có hoàn tác

**Files:** Create `judge/utils/problem_package_import.py`, `judge/utils/problem_package_guards.py`, `judge/tests/test_problem_package_import.py`.

**Consumes:** Task 1/2. **Produces:** `create_draft(user, upload) -> ProblemPackageImport`; `confirm_import(import_id, user, metadata) -> ProblemPackageImport`; `retry_import(import_id, user) -> ProblemPackageImport`; `can_access_import(record, user) -> bool`; `assert_problem_package_mutable(problem_id, import_id=None) -> None` (raise ValidationError khi có active import khác).

- [ ] Fixture DB dùng helper hiện có trong `judge/models/tests/util.py` sau khi đọc chữ ký; test duplicate confirm và mã trùng:

```python
def test_confirm_is_idempotent(self):
    record = create_draft(self.user, make_package())
    first = confirm_import(record.pk, self.user, self.metadata)
    second = confirm_import(record.pk, self.user, self.metadata)
    self.assertEqual(first.problem_id, second.problem_id)
    self.assertEqual(Problem.objects.filter(code=self.metadata['code']).count(), 1)
    self.assertFalse(first.problem.is_public)
    self.assertFalse(first.problem.solution.is_public)
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_import`; expected FAIL.
- [ ] `create_draft` enforce `judge.add_problem` + `judge.import_problem_package`, inspect rồi lưu private source; cleanup nếu DB save lỗi. Confirm lấy `select_for_update`, kiểm tra owner/quyền/expiry/checksum và metadata với model validators. Enforce `VNOJ_TESTCASE_HARD_LIMIT` trừ quyền `judge.create_mass_testcases`. Lưu metadata JSON chuẩn (group ID, type IDs, language ID, memory KiB) và chuyển CREATING một lần. Task nền sẽ xử lý phần nặng qua `run_import` ở task 4; confirm không giữ request chờ publish.
- [ ] Thêm `materialize_problem(import_id, lease_token) -> ProblemPackageImport` ở cùng module: chuẩn bị test ZIP, dựng Problem/ProblemData/case objects; gọi `ProblemDataCompiler(...).make_init()`, dump YAML; transaction tạo bài, Solution, cases; atomic rename staging vào code directory chỉ nếu target chưa tồn tại; lưu relative file names; chuyển PUBLISHING. Tác giả là uploader; allowed_languages theo include_in_problem cộng language chuẩn; publish_on/date=now, partial=True.

```python
init = ProblemDataCompiler(problem, data, cases, valid_files).make_init()
if not init:
    raise PackageValidationError('Không tạo được cấu hình test')
yml = yaml.safe_dump(init).encode('utf-8')
```

- [ ] Thêm test compiler exception, rename lỗi, DB IntegrityError sau rename, hai import cùng code, request metadata bị sửa và enqueue lỗi. Chỉ dọn path mang marker UUID hiện tại; đối chiếu DB trước dọn khi commit outcome chưa rõ. Retry CREATING không tạo lại bài đã liên kết.
- [ ] Run module; dùng `captureOnCommitCallbacks(execute=True)` cho test enqueue. MariaDB TransactionTestCase kiểm tra double-confirm riêng; không coi SQLite PASS là xác minh race.

## Task 4: Worker publish và submission kiểm chứng

**Files:** Create `judge/tasks/problem_package.py`, `judge/tests/test_problem_package_tasks.py`; modify `judge/tasks/__init__.py`.

**Consumes:** `materialize_problem`, model và release publisher. **Produces:** shared tasks `run_import(import_id)`, `reconcile_imports()`, `cleanup_imports()`; adapter `dispatch_reference(record) -> bool`.

- [ ] Viết test publish fail không tạo submission, retry không tạo hai submission:

```python
@patch('judge.tasks.problem_package.publish_problem_to_r2')
def test_publish_failure_does_not_submit(self, publish):
    publish.side_effect = OSError('storage unavailable')
    run_import(str(self.record.pk))
    self.record.refresh_from_db()
    self.assertEqual(self.record.failed_stage, 'PUBLISHING')
    self.assertIsNone(self.record.submission_id)
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_tasks`; expected FAIL.
- [ ] Claim bản ghi bằng transaction row lock + lease UUID; không giữ transaction mở qua network. Lease 10 phút, heartbeat giữa các bước, mọi update kiểm tra token; recovery không chiếm lease còn hiệu lực. Khi publish kéo dài dùng heartbeat để lease không hết trong thao tác. `run_import` dispatch theo state CREATING/PUBLISHING/SUBMITTING, ignore JUDGING/FINISHED và active lease khác.
- [ ] R2 mode: version xác định theo import UUID và checksum test; retry reuse version, chỉ coi publish xong khi DB release và manifest đồng nhất. Local mode: kiểm tra init/test ZIP tồn tại trong shared data root và cấu hình `PROBLEM_PACKAGE_LOCAL_JUDGE_SHARED=True`; nếu chưa xác nhận shared path, FAILED/PUBLISHING với hướng dẫn cấu hình. Lưu checksum local để phát hiện stale.
- [ ] Tạo Submission/SubmissionSource và liên kết trong cùng transaction, cờ reference=True. Dispatch chỉ sau release; gọi `judge_submission(submission)` trực tiếp để lấy bool, refresh DB; đánh dấu lỗi nếu False hoặc IE ngay sau gọi. Không dispatch lại P/G/D/CE/AB; QU có dispatched_at thì chờ; QU chưa acknowledgement xử lý bằng retry cùng ID sau lease, không tạo mới. Network ambiguity được ghi nhận, không reset verdict đã hoàn tất. IE trong giai đoạn dispatch là lỗi gửi; IE sau acknowledgement là kết quả cần kiểm tra thủ công, không tự rejudge liên tục.

```python
sent = judge_submission(submission)
submission.refresh_from_db()
if not sent or submission.status == 'IE':
    return False
return True
```

- [ ] `reconcile_imports` phục hồi CREATING/PUBLISHING/SUBMITTING không có lease sống, đồng bộ JUDGING từ status submission (D/CE/AB/IE terminal), không enqueue lại FAILED tự động. Retry có quyền chỉ phục hồi failed_stage và dùng cùng submission; kiểm tra dữ liệu hiện tại khớp release đã lưu, mismatch yêu cầu sửa/chấm thủ công thay vì khẳng định kết quả cũ.
- [ ] Test publisher thành công, local flag, dispatch False không raise, crash sau tạo source, duplicate delivery, lease token cũ, QU đang chờ judge, WA không FAILED, CE terminal. Run module; expected PASS.

## Task 5: Source riêng tư và bảo vệ dữ liệu đang kiểm chứng

**Files:** Modify `judge/models/submission.py`, `judge/views/problem.py`, `judge/views/problem_data.py`, `judge/admin/problem.py`, `judge/utils/problem_releases.py`; create `judge/tests/test_problem_package_permissions.py`; inspect/update source paths in `judge/views/submission.py`, `judge/views/api/` nếu có đường bỏ qua can_see_detail.

**Consumes:** reference flag và `assert_problem_package_mutable`. **Produces:** centralized private-source check; mọi mutation dữ liệu/mã bài tôn trọng khóa import.

- [ ] Test bài public + source ALWAYS nhưng học sinh không thấy source chuẩn; user upload mất quyền quản lý cũng không tải source chuẩn. Test submission thường không đổi hành vi.

```python
def test_reference_source_stays_private_after_publication(self):
    self.problem.is_public = True
    self.problem.submission_source_visibility_mode = SubmissionSourceAccess.ALWAYS
    self.problem.save()
    self.submission.is_reference_verification = True
    self.assertFalse(self.submission.can_see_detail(self.student))
    self.assertTrue(self.submission.can_see_detail(self.editor))
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_permissions`; expected FAIL.
- [ ] Đặt guard reference ngay sau authenticated check, trước owner/source_visibility branches; chỉ cho editor bài hoặc quyền quản trị `view_all_submission`. Kiểm tra raw source, diff, API/export đều qua quyền tương đương. Không dùng ONLY_OWN ở cấp bài vì nó ảnh hưởng toàn bộ submission.
- [ ] Mutation guard chỉ khóa các field ảnh hưởng dispatch: code, time/memory/language limits, allowed languages, test/config/release và xóa bài trong CREATING/PUBLISHING/SUBMITTING/JUDGING. Bọc mutation và kiểm tra guard trong transaction khóa row import để tránh check-then-write race. Bổ sung guard cho admin save/delete, Polygon update, data save, publish/delete/purge CLI qua release utility. Worker truyền import_id vào utility để bypass đúng bản ghi đang claim; mặc định external caller không bypass.

```python
def can_see_reference_source(self, user):
    return user.is_authenticated and (
        self.problem.is_editable_by(user) or user.has_perm('judge.view_all_submission')
    )
```

- [ ] Test direct POST khi giao diện ẩn nút; admin/Polygon/publish CLI bị chặn; FINISHED hoặc FAILED cho phép sửa và trang trạng thái báo stale checksum. Run module và test submission hiện có; expected PASS.

## Task 6: Form, endpoints và giao diện

**Files:** Create `judge/problem_package_forms.py`, `judge/views/problem_package.py`, ba templates trong file map, `judge/tests/test_problem_package_views.py`; modify `dmoj/urls.py`, `templates/problem/list.html` (đọc vị trí nút tạo/import hiện có trước sửa), `locale/vi/LC_MESSAGES/django.po` nếu chuỗi cần gettext.

**Consumes:** services và guard tasks 1–5. **Produces:** routes `problem_package_upload`, `problem_package_preview`, `problem_package_confirm`, `problem_package_status`, `problem_package_retry`, `problem_package_download`.

- [ ] Viết view tests upload→preview, code collision, missing metadata, denied owner, CSRF, retry chỉ POST:

```python
def test_upload_redirects_to_preview(self):
    self.client.force_login(self.user)
    response = self.client.post(reverse('problem_package_upload'), {
        'package': SimpleUploadedFile('package.zip', make_package().getvalue()),
    })
    self.assertEqual(response.status_code, 302)
    record = ProblemPackageImport.objects.get(owner=self.user.profile)
    self.assertEqual(response.url, reverse('problem_package_preview', args=[record.pk]))
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_views`; expected FAIL.
- [ ] Forms dùng model validators cho code/name/time/points/group/types; memory_mb DecimalField đổi KiB, kiểm tra giới hạn model; reference language queryset chỉ C++ được bật, mặc định CPP20 nếu có, không chọn runtime không tồn tại. Upload giới hạn đọc streaming. Preview dữ liệu server-side, không tin hidden manifest từ client.
- [ ] Routes nằm trước matcher problem code; UUID per record. GET download kind chỉ `source`/`solution`; FileResponse attachment, Cache-Control private,no-store. Confirm/retry require POST và CSRF; status JSON dùng cùng access check. HTTP errors rõ 400 validation, 403 quyền hoặc 404 tránh lộ record, 409 conflict.
- [ ] Đọc toàn bộ `style.md` trước sửa markup. Dùng template base/form components hiện có, render Markdown qua cùng filter của đề/editorial. Preview có metadata, số test và attachment list; status có phase/verdict/link/retry. Poll status mỗi 3 giây khi active, dừng terminal, thông báo lỗi mạng mà không reset trạng thái. Không chèn source vào HTML/status JSON cho user thiếu quyền.

```html
<form method="post">
    {{ csrf_input }}
    {{ form.as_p() }}
    <button type="submit">Tạo bài và chấm lời giải chuẩn</button>
</form>
```

Snippet dùng CSRF input của Jinja; đối chiếu context processor và template lân cận trước nối view.
- [ ] Test unknown language, metadata sửa, memory conversion, private download, markdown script injection, status pending judge, WA/CE và stale release. Run module; browser kiểm tra desktop/mobile và keyboard focus bằng skill webapp-testing lúc thực thi.

## Task 7: Cleanup, scheduler và deployment

**Files:** Modify `judge/tasks/problem_package.py`, `judge/signals.py`, `dmoj/celery.py`, `dmoj/local_settings.docker.py.example`, `docker-compose.dev.yml`, `docker-compose.production.yml`, `nginx/vnoj.conf.docker`, `CI-CD.md`; create `judge/tests/test_problem_package_cleanup.py`, `judge/management/commands/reconcile_problem_imports.py`.

**Consumes:** state/lease/storage services. **Produces:** periodic reconcile + expiry, private shared volume, CLI recovery.

- [ ] Test cleanup expired draft nhưng không xóa draft mới/active lease; delete bài chỉ xóa nguồn sau commit:

```python
def test_cleanup_keeps_active_import(self):
    self.record.state = 'PUBLISHING'
    self.record.save(update_fields=['state'])
    cleanup_imports()
    self.assertTrue(private_package_storage.exists(self.record.source_archive.name))
```

- [ ] Run `python manage.py test judge.tests.test_problem_package_cleanup`; expected FAIL.
- [ ] Cleanup expire 24h chỉ AWAITING_CONFIRMATION, dọn source và source text, giữ record EXPIRED tối thiểu phục vụ thông báo. Dọn staging mồ côi quá 24h khi không có live lease, không có problem liên kết sở hữu path; idempotent. post_delete record đăng ký xóa archive bằng on_commit, kiểm tra django-cleanup để không double-delete có hại; không xóa file trong rollback.
- [ ] Beat schedule reconcile mỗi phút, cleanup mỗi giờ; CLI gọi cùng functions và in số bản ghi xử lý. Beat chạy một instance, scheduler state trên volume riêng. Cấu hình private volume `/private-problem-imports` cho site/celery; lặp mount ở production site do YAML list override. Thêm env các giới hạn và shared-local flag (default False).

```python
app.conf.beat_schedule['problem-package-reconcile'] = {
    'task': 'judge.tasks.problem_package.reconcile_imports', 'schedule': 60.0,
}
app.conf.beat_schedule['problem-package-cleanup'] = {
    'task': 'judge.tasks.problem_package.cleanup_imports', 'schedule': 3600.0,
}
```

- [ ] Nginx location upload cho request multipart lớn hơn 100 MiB một chút (ví dụ 110m), application vẫn giới hạn file đúng 100 MiB; không giảm giới hạn upload có sẵn của route khác. CI-CD ghi migration, grant permission, private volume ownership, Beat, recovery command và local judge flag. Kiểm tra workflow deploy có danh sách service cố định thì thêm beat vào đúng danh sách bằng diff tập trung.
- [ ] Run cleanup tests, `python manage.py check`, `docker compose -f docker-compose.dev.yml config --quiet`; production config kiểm tra với env placeholder không secret. Không chạy deploy thực tế trong tác vụ viết code.

## Task 8: Kiểm thử đầu cuối và bàn giao

**Files:** Create `judge/tests/test_problem_package_workflow.py`; update `CI-CD.md` phần smoke test và trạng thái verification thực tế.

**Consumes:** toàn bộ flow. **Produces:** workflow regression và bằng chứng smoke test.

- [ ] Test workflow fixture 20 cặp tự sinh; patch publisher/dispatch tại boundary nhưng assert nội dung init.yml, test ZIP và DB, không chỉ call count:

```python
def test_twenty_case_package_end_to_end(self):
    record = create_draft(self.user, self.twenty_case_package)
    confirm_import(record.pk, self.user, self.metadata)
    run_import(str(record.pk))
    record.refresh_from_db()
    self.assertEqual(record.problem.cases.count(), 20)
    self.assertEqual(record.problem.memory_limit, 524288)
    self.assertEqual(record.problem.solution.content, self.editorial)
    self.assertTrue(record.submission.is_reference_verification)
```

- [ ] Run test mới trước, xác nhận lỗi phản ánh integration còn thiếu; sửa wiring trong file sở hữu trách nhiệm, không bypass service trong test.
- [ ] Run focused modules tasks 1–8, các test release/submission liên quan, `python manage.py makemigrations --check --dry-run`, `python manage.py check`, flake8 trên file Python thay đổi, `git diff --check`. Sau đó chạy `python manage.py test judge urlshortener` nếu dependencies/DB sẵn sàng. Ghi rõ failure do môi trường và failure do code.
- [ ] Với MariaDB thật, chạy hai confirm cạnh tranh cùng record và cùng code khác record; assert một Problem, một Submission, không mất file của winner. TransactionTestCase dùng connection riêng mỗi thread và barrier trước confirm, không dùng sleep làm đồng bộ.
- [ ] Smoke browser: upload `/home/hlt/Documents/example/package.zip` hoặc ZIP tự tạo từ thư mục mẫu nếu archive không khớp; xác nhận 20 test/1s/512MB, nhập mã mới, chọn runtime C++ tồn tại. Chờ release và judge thật: một submission AC, case total 20, bài/editorial vẫn ẩn.
- [ ] Smoke lỗi: lời giải sai phải cho WA và import thành công; ngắt publisher để thấy retry giữ cùng bài; thiếu judge phải chờ; kiểm tra student không tải code/ZIP kể cả khi bài public. Không coi mock PASS là judge smoke PASS.
- [ ] Review coverage map bên dưới, ghi kết quả kiểm tra và đường dẫn file. Dừng ở bàn giao nếu user chưa yêu cầu commit/deploy.

## Coverage và tự rà soát kế hoạch

| Yêu cầu đặc tả | Task |
|---|---|
| ZIP root, UTF-8, pairing, limits, metadata | 1 |
| Model, code riêng, ZIP private | 2 |
| Create-only, hidden, points, permissions create, rollback | 3 |
| Async release, dispatch, lease, retry, exact release | 4, 5 |
| Private submission source, mutation race | 5 |
| Upload/preview/status/download và style | 6 |
| Expiry, orphan cleanup, deletion, Beat, volumes, proxy | 7 |
| Unit, concurrency MariaDB, browser và judge thật | 8 |

Các API trong task sau dùng tên đã định nghĩa ở task trước. Không yêu cầu chạy test trong bước lập kế hoạch. Các giới hạn là settings, không hardcode riêng ở view. Handoff cần người dùng chọn thực thi trực tiếp hoặc dùng subagent; không tự spawn subagent trước lựa chọn đó.

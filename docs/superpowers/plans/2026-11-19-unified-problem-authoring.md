# Unified Problem Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép người có quyền tạo/sửa đề, editorial và bộ test từ một trình soạn chung, vào được từ admin và site chính, với lưu nháp và kiểm chứng độc lập.

**Architecture:** Django forms/Jinja2 dùng chung service authoring, không tạo đường lưu riêng cho ZIP hoặc admin. Upload riêng tư được staging trước; một operation lưu bền trong DB điều phối cài test/publish sau commit. Readiness và revision tách khỏi visibility; lớp policy chung bảo vệ mọi đường chỉnh dữ liệu, nộp bài và công khai.

**Tech Stack:** Django, MariaDB production/SQLite unit tests, Celery + Redis, Martor, Jinja2, SCSS hiện có, filesystem dùng chung site/Celery, R2 release hiện có. Không thêm framework frontend hoặc dịch vụ bên ngoài.

**Spec:** `docs/superpowers/specs/2026-11-19-unified-problem-authoring-design.md` (người dùng đã duyệt).

## Global Constraints

- Một trình soạn chung, dùng từ cả admin và site chính; admin tiếp tục cung cấp các chức năng quản trị nâng cao.
- ZIP chỉ là nguồn dữ liệu cho cùng bản nháp; không có đường tạo bài đặc biệt cho ZIP.
- Bản đầu tập trung bài input/output thông thường; không tự sinh output hoặc chạy mã nguồn trên web/Celery host.
- Lưu nháp rõ ràng bằng nút; không autosave mỗi lần gõ. Không tự chấm sau mỗi lần lưu, không tự công khai khi AC.
- Default giới hạn upload: 100 MiB nén, 1 GiB tổng giải nén, 10.000 entry, 5 MiB mỗi tài liệu/source, 256 MiB mỗi file test; thời hạn upload tạm 24 giờ.
- Tái sử dụng quyền hiện có; ZIP test-only không đòi import_problem_package. PDF vẫn đòi upload_file_statement.
- Bài tổ chức giữ organization/is_organization_private, kiểm tra quota và quyền ở mọi POST, không tin hidden field.
- Test/source lưu riêng tư, download kiểm tra quyền; không gửi nội dung tới dịch vụ ngoài. Không dùng localStorage làm nơi giữ bản nháp.
- Đọc style.md trước khi sửa template/SCSS/JS UI. Dùng Jinja2, Martor và tokens hiện có; mobile không cuộn ngang toàn trang.
- Database/filesystem/R2 không cùng transaction; dùng staging bất biến + operation bền + retry/đối soát. Không xóa artifact còn được tham chiếu.
- Bài cũ, Polygon, contest và cấu hình checker/grader/subtask nâng cao phải tiếp tục dùng được.
- Không commit/push/triển khai VPS nếu chưa được yêu cầu. Các checkpoint bên dưới là điểm review; chỉ commit khi được ủy quyền, với attribution bắt buộc.

## Review Focus

1. Hai tab hoặc người dùng retry request sau timeout: không mất chỉnh sửa, không tạo Problem/operation/submission trùng (Tasks 4, 7).
2. Worker chết sau rename hoặc sau upload R2 nhưng trước DB commit: retry xác định được artifact và phục hồi, không xóa bộ đang hoạt động (Task 5).
3. Submission đã QU hoặc dispatch vừa xảy ra trong lúc thay test: không chạy bằng cấu hình/test khác phiên bản và không treo vĩnh viễn (Tasks 5–7).
4. Form nâng cao/admin/Polygon sửa bài có cấu hình đặc biệt: không bypass khóa/readiness và không reset cấu hình khi chỉ sửa đề (Tasks 6, 10).
5. Quyền bị thu hồi hoặc upload hết hạn giữa preview và save: POST từ chối rõ ràng, không xóa dữ liệu người dùng đang sửa hay nhận upload của người khác (Tasks 3, 4, 8).

---

## Execution preparation

Một kế hoạch duy nhất vì upload, readiness và dispatch phụ thuộc chặt vào nhau; các task là checkpoint kiểm thử, không phát hành UI khi các gate an toàn chưa xong.

- [ ] Dùng skill worktree khi bắt đầu thực thi; repo thật là `D:/thinkalgo/thinkalgo-oj`, không phải `D:/thinkalgo`. Kiểm tra git status trước khi tạo branch/worktree qua công cụ được hỗ trợ. Không lặp yêu cầu worktree nếu môi trường báo không hỗ trợ; báo lại và dùng phương án được người dùng chấp thuận.
- [ ] Xác định môi trường chạy test: Python local hiện thiếu Django (`ModuleNotFoundError`). Kiểm tra `docker version` / môi trường Python có sẵn trước; không coi test là pass nếu chỉ compile. Không cài dependency hoặc sửa settings production trong bước lập kế hoạch.
- [ ] Khi thực thi, dùng `.ci.settings.py` không secrets trong môi trường test riêng; chuẩn bị thêm MariaDB cho kiểm thử lock/concurrency. Không ghi đè `dmoj/local_settings.py` hiện có chưa đọc. Chạy baseline các test package parser/import/release và tổ chức.
- [ ] Tạo helper fixture `judge/tests/authoring_helpers.py`: tạo user global, user org-only, group/type/runtime, ZIP theo bytes, dữ liệu cũ và private storage tạm. Tất cả test filesystem dùng TemporaryDirectory + override_settings; không truy cập R2/VPS thật.

Lệnh phía dưới là `python manage.py test ...` bên trong môi trường đã cấu hình; nếu dùng Docker, bọc bằng `docker compose -f docker-compose.dev.yml exec site python3 manage.py test ...`. Không chạy compose production.

## File map và các quyết định giao tiếp

Các file mới được chia theo trách nhiệm; không dồn toàn bộ logic vào `judge/views/problem.py` hoặc `judge/forms.py`.

| File | Trách nhiệm |
|---|---|
| `judge/models/problem_authoring.py`, `judge/models/__init__.py`, migration sau `0234_problem_package_import` | Schema authoring/upload/operation/reference run |
| `judge/problem_authoring/types.py` | Dataclass payload/result, enums/errors chung |
| `judge/problem_authoring/policy.py` | Quyền, field-level lock, readiness gates |
| `judge/problem_authoring/packages.py` | Parser ZIP test-only và full package có giới hạn |
| `judge/problem_authoring/storage.py` | Staging riêng tư, checksum, journal cài đặt/recovery |
| `judge/problem_authoring/uploads.py`, `quota.py` | Nhận upload, scope/expiry, reserve dung lượng |
| `judge/problem_authoring/service.py` | Save draft, optimistic concurrency và idempotency |
| `judge/problem_authoring/data.py` | Chuẩn bị/cài/activate testcase và configuration |
| `judge/problem_authoring/verification.py` | Source/run kiểm chứng, retry và stale result |
| `judge/problem_authoring/forms.py`, `views.py`, `urls.py` | Forms và HTTP adapter chung |
| `judge/tasks/problem_authoring.py` | Worker processing và reconciliation |
| `judge/management/commands/reconcile_problem_authoring.py` | Recovery/cleanup/kiểm tra legacy flow |
| `templates/problem/authoring.html`, `templates/problem/authoring/*.html`, `resources/problem-authoring.js`, `resources/problem-authoring.scss` | Trình soạn chung và progressive enhancement |
| `judge/tests/test_problem_authoring_{models,packages,uploads,service,data,policy,verification,views,legacy,concurrency}.py` | Tests tập trung theo boundary |

Dùng package `judge/problem_authoring/__init__.py` nhẹ, không import view từ utility. Các file đang có sẽ sửa tại task tương ứng. Nếu pipeline static repo cần vị trí khác, theo cách `editor.html`/SCSS hiện có và sửa file map trước khi viết, không thêm bundler.

### Các kiểu dùng xuyên task

Định nghĩa trong `types.py`:
- `AuthoringContext(user_id: int, organization_id: int | None)`; context được xây từ request/session/URL sau kiểm tra quyền, không deserialize tin cậy từ POST.
- `CaseSpec(input_file: str, output_file: str, order: int, points: Decimal, is_pretest: bool = False)`.
- `PackageManifest(kind: str, fields: dict, tests: list[CaseSpec], source_name: str | None, warnings: list[str], sha256: str, compressed_bytes: int, expanded_bytes: int)`; không trả nội dung testcase.
- `DraftChanges(problem_fields: dict, solution_fields: dict | None, test_upload_id: UUID | None, cases: list[CaseSpec] | None, reference_upload_id: UUID | None, reference_language_id: int | None, replace_sections: frozenset[str])`.
- `SaveResult(problem_id: int, revision: int, operation_id: UUID | None)`.
- `AuthoringError(code: str, message: str, field: str | None = None)`: lỗi an toàn để render form; subclass `ConflictError` cho revision cũ.

Nếu runtime Python của image không hỗ trợ cú pháp union, dùng Optional/List tương đương, không tăng version chỉ vì type hints.

## Task 1: Schema trạng thái và revision không làm đổi bài cũ

**Files:** Create `judge/models/problem_authoring.py`, `judge/problem_authoring/{__init__,types}.py`, `judge/tests/test_problem_authoring_models.py`; Modify `judge/models/__init__.py`; Create migration kế tiếp sau migration leaf thực tế (hiện có `0234_problem_package_import.py`).

**Interfaces:** Produces các models và kiểu ở file map; không service hoặc UI ở task này.

- [ ] **Step 1 — Viết test đỏ:** `test_legacy_problem_has_no_authoring_gate` khẳng định bài có sẵn không tự nhận readiness mới; `test_request_token_is_unique_per_actor` khẳng định unique `(actor, request_token)`; `test_one_nonterminal_data_operation_per_problem` khẳng định tạo operation cạnh tranh bị từ chối qua khóa service, không dựa partial unique index MariaDB không hỗ trợ. Migration roundtrip giữ `ProblemPackageImport`, dữ liệu test, editorials và visibility cũ.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_models -v 2`; expected FAIL vì model chưa có.
- [ ] **Step 3 — Tạo schema:** `ProblemAuthoringState` OneToOne Problem, `revision`, `grading_revision`, `active_data_revision`, `data_state` (`MISSING/PENDING/READY/FAILED`), nullable `current_operation`; `ProblemAuthoringUpload` UUID với owner, organization, kind (`TESTS/PACKAGE/PDF/SOURCE`), private relative path, digest, manifest, size, expires_at, nullable consumed_by; `ProblemAuthoringSave` actor/token/digest/result; `ProblemDataOperation` UUID, problem, immutable config JSON, upload refs, target revision, state (`PENDING/INSTALLING/PUBLISHING/READY/FAILED/WAITING`), phase, lease_until, attempts, safe_error, created/updated; `ProblemReferenceSource` OneToOne Problem với private upload, Language; `ProblemReferenceRun` UUID, problem, owner, token, grading_revision, source digest, runtime, nullable submission OneToOne, state/error/timestamps. FK operation/upload bảo vệ reference bằng PROTECT khi cần; xóa bài có cleanup có kiểm soát, không xóa staging của worker còn sống. Không thêm authoring state cho mọi bài cũ trong data migration.
- [ ] **Step 4 — Chạy test trên +** `python manage.py makemigrations --check --dry-run`; expected PASS/no changes; migration forward/back trên DB test rỗng và fixture cũ.
- [ ] **Step 5 — Checkpoint:** review model/state contracts, ghi kết quả; commit chỉ nếu đã được cho phép.

## Task 2: Parser ZIP chung, có giới hạn và không đoán mơ hồ

**Files:** Create `judge/problem_authoring/packages.py`, `judge/tests/test_problem_authoring_packages.py`; Modify `judge/utils/problem_package.py`, `judge/tests/test_problem_package_parser.py` chỉ để giữ adapter cũ.

**Interfaces:** Consumes `CaseSpec/PackageManifest`; produces `inspect_tests(stream: BinaryIO) -> PackageManifest`, `inspect_full_package(stream: BinaryIO) -> PackageManifest`. Legacy `inspect_package` giữ return shape cũ cho job cũ và yêu cầu full package cũ; không đổi semantic của pending job.

- [ ] **Step 1 — Test đỏ:** tên test/điều kiện chính: `test_natural_order` asserts `['1.in','2.in','10.in']`; `test_test_roots` nhận root, tests/, wrapper/, wrapper/tests/ nhưng từ chối trộn root; `test_missing_pair_names_error`; `test_full_package_allows_statement_only`; `test_old_complete_package_still_parses`; `test_unknown_files_are_not_ignored`; `test_md_limits_are_suggestions`. Parameterize traversal, symlink, duplicate normalized name, encrypted, invalid ZIP/UTF-8, empty required statement, forged size, 100 MiB/1 GiB/10.000 entries/5 MiB/256 MiB boundary (mock streaming counters, không tạo fixture GiB). `test_mass_testcases_not_formset_limited` dùng 1.002 cặp và quyền/technical cap để Task 4 consume.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_packages judge.tests.test_problem_package_parser -v 2`; expected test mới FAIL.
- [ ] **Step 3 — Implement parser:** enumerate an toàn và đọc streaming, checksum archive; chỉ một scope không mơ hồ. Full package hỗ trợ statement.md, optional editorial.md, solution.cpp, tests/*.in/out; file nguồn thủ công chọn qua SOURCE upload. Không extractall, không deserialize init.yml từ archive. Trần testcase thường từ VNOJ_TESTCASE_HARD_LIMIT; privileged technical cap 4.998 cặp trong full ZIP (10.000 entry trừ tài liệu), vẫn kiểm tra giới hạn entry tổng thực tế. Source và test names không được phát qua public media.
- [ ] **Step 4 — Chạy lại cùng lệnh:** PASS, không regression parser cũ.
- [ ] **Step 5 — Checkpoint:** review parser an toàn và compatibility.

## Task 3: Private upload, expiry và quota reservation

**Files:** Create `judge/problem_authoring/{storage,uploads,quota}.py`, `judge/tests/test_problem_authoring_uploads.py`; Modify `dmoj/settings.py`, `dmoj/local_settings.docker.py.example`, `docker-compose.dev.yml`, `docker-compose.production.yml` chỉ khi private mount/settings hiện có chưa đủ (đọc trước, không đưa secrets vào diff).

**Interfaces:** `receive_upload(context: AuthoringContext, stream: BinaryIO, kind: str, *, problem_id: int | None = None) -> ProblemAuthoringUpload`; `get_upload(context, upload_id: UUID, *, kind: str, for_consumption: bool = False) -> ProblemAuthoringUpload`; `reserve_upload_bytes(context, compressed_bytes: int, problem_id: int | None) -> None` chạy dưới org/owner lock. Storage `stage_upload(stream, upload_id: UUID) -> tuple[str, str, int]` trả relative path/digest/bytes; path không nhận từ client.

- [ ] **Step 1 — Test đỏ:** owner khác, scope khác, expired đúng mốc 24h, quyền bị thu hồi không dùng được upload; valid upload giữ nguyên khi validation form sau đó lỗi. `test_exact_quota_boundary` kiểm tra <= chứ không chỉ current < quota; `test_replacement_reserves_temporary_bytes`, `test_shared_upload_not_double_counted`, `test_failed_upload_releases_reservation`. PDF quyền/type/size và source UTF-8/5 MiB. Hai POST không vượt hạn mức khi cùng owner/org. File chưa tham chiếu được cleanup, file thuộc pending operation không bị cleanup.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_uploads -v 2`; expected FAIL.
- [ ] **Step 3 — Implement:** root riêng tư kế thừa PROBLEM_PACKAGE_ROOT bằng setting `PROBLEM_AUTHORING_ROOT`, mount dùng chung site/Celery; UUID/subpath do server tạo, open exclusive và quota lock trước write có giới hạn. Defaults configurable: per-user unconsumed 200 MiB compressed, org temporary replacement budget 100 MiB compressed ngoài max_storage, tổng expanded và technical caps như Task 2. Reserve active + upload + operations, không tính cùng object hai lần; global user không có org quota nhưng vẫn có technical/per-owner cap. Dùng private staging cho PDF trước upload media, PDF media failure giữ retryable artifact và không mất URL cũ. Download quyền được bind lại khi consume, upload đã consume không dùng để tạo bài thứ hai.
- [ ] **Step 4 — Chạy lại:** PASS; concurrency DB kiểm ở Task 12, không giả SQLite select_for_update có tác dụng.
- [ ] **Step 5 — Checkpoint:** xác nhận private mount, cleanup/quota ownership.

## Task 4: Một service lưu bài cho mọi nguồn nhập

**Files:** Create `judge/problem_authoring/{policy,service}.py`, `judge/tests/test_problem_authoring_service.py`; Modify `judge/views/organization.py` chỉ để expose/reuse permission predicate nếu cần, không làm yếu AdminOrganizationMixin.

**Interfaces:** `authorize_create(context) -> None`, `authorize_edit(context, problem) -> None`; `save_draft(context, changes: DraftChanges, *, problem_id: int | None, expected_revision: int | None, request_token: UUID) -> SaveResult`; `grading_fields_changed(before: dict, after: dict) -> bool`. Tasks 5–10 dùng các hàm này, không form.save trực tiếp.

- [ ] **Step 1 — Test đỏ:** create global actor nonstaff; org-only actor có create_organization_problem + edit_own_problem và admin scope nhưng không add_problem global vẫn tạo được; add-only thiếu edit_own_problem báo lỗi trước khi ghi DB. Assert organization/private/author/curator, languages, tags/group/types và partial/visibility giữ nguyên. `test_duplicate_token_returns_original_result`, `test_same_token_different_payload_rejected`, `test_stale_revision_does_not_overwrite`, `test_expired_upload_does_not_create_problem`, `test_revoke_permission_before_save`. Lưu không test => private/MISSING, metadata model tối thiểu vẫn required. PDF upload thành công assert URL persisted; lỗi media không tạo partial Problem. Broker delay mock raise assert Problem + operation PENDING tồn tại và form không báo mất bài. 1.002 test privileged hợp lệ không dùng view formset; hard limit thường vẫn enforced. Quota full ở POST/direct/concurrent không tạo bài.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_service -v 2`; expected FAIL.
- [ ] **Step 3 — Implement:** allowlist fields, model validation và service validators; không tin is_public/org/author từ POST. Lock order org (nếu có), Problem/state, upload; create token row và payload fingerprint trong transaction; unique collision xử lý bằng savepoint rồi đọc result. Fresh revision mỗi save; grading_revision chỉ đổi với test/checker/grader/TL/ML/languages/reference source/runtime, không đổi vì statement/editorial. Editorial save không reset metadata không có trong payload. DB writes/revision audit trong transaction; data operation được ghi cùng commit, enqueue best-effort ngoài transaction; pending durable được Task 5 tìm lại. Source upload optional, không required C++; runtime phải nằm trong allowed languages, không âm thầm mở thêm runtime ngoài chính sách. PDF upload thành artifact trước transaction nhưng ghi URL trong lần save model, giữ cleanup reference nếu rollback. New drafts private; publish do Task 6 riêng.
- [ ] **Step 4 — Chạy lại:** PASS; không gọi confirm_import hoặc subclass form_valid để tạo bài mới.
- [ ] **Step 5 — Checkpoint:** review service invariants + permission matrix.

## Task 5: Worker cài test có recovery, release activation không chạy nhầm phiên bản

**Files:** Create `judge/problem_authoring/data.py`, `judge/tasks/problem_authoring.py`, `judge/management/commands/reconcile_problem_authoring.py`, `judge/tests/test_problem_authoring_data.py`; Modify `judge/utils/problem_releases.py`, `judge/tasks/__init__.py`, `dmoj/settings.py` và Celery beat config hiện hành sau khi locate.

**Interfaces:** `prepare_data_operation(operation_id: UUID) -> None`, `process_data_operation(operation_id: UUID) -> None`; `upload_release(source_dir: Path, code: str, version: str) -> dict` không update ProblemData pointer; `activate_operation(operation_id: UUID, manifest: dict | None) -> None`; `reconcile_authoring(*, now: datetime, limit: int = 100) -> dict`. Legacy `publish_problem_to_r2` giữ API, reuse upload helper.

- [ ] **Step 1 — Test đỏ:** new/replacement R2 và non-R2; compiler output đúng points/checker; R2 fail giữ old pointer/artifact và pending retry, draft chưa sẵn sàng. Kill/fault injection sau build, backup rename, install rename, put_object, trước/sau DB pointer commit => retry idempotent. `test_retry_same_release_never_overwrites_different_digest`; `test_pending_recovered_without_broker`; `test_cleanup_skips_referenced_staging`; `test_old_operation_cannot_activate_after_new_revision`; `test_queued_submission_blocks_activation` gồm QU/P/G và trạng thái unknown nonterminal.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_data judge.tests.test_problem_releases -v 2`; expected test mới FAIL.
- [ ] **Step 3 — Implement build/install:** dùng ProblemDataCompiler với desired cases từ config operation và staging riêng, không replace active rows/files trước validate. Operation version `authoring-<uuid hex>` deterministic; digest manifest cố định. Claim lease ngắn qua DB, xử lý network ngoài transaction; đọc heartbeat/claim token trước từng final activation để worker cũ không thắng worker mới. Mỗi filesystem phase có journal marker UUID + checksums + backup, fsync metadata khi cần. Chỉ activate khi không có nonterminal submissions, và submission enqueue/rejudge/bridge cùng tuân admission lock ở Task 6. Với non-R2, cũng chỉ swap khi quiescent, không giả judge hỗ trợ version pin. Ready cũ + pending operation => block nhận submission mới đến khi activation/abort rõ ràng; bài nộp cũ được drain.
- [ ] **Step 4 — Implement commit/reconcile:** upload từ staging (không từ thư mục active), verify existing release digest khi retry; update testcase/ProblemData/release pointer + active_data_revision/readiness trong transaction sau journal install. Recovery quyết định theo operation ID + phase, rollback về backup nếu chưa commit hoặc finalize nếu đã commit, không overwrite thư mục không có marker sở hữu. Failed replacement giữ bộ cũ; nút retry tiếp tục, không tự mở admission nếu local/DB chưa khớp. Reconciler mỗi 60 giây qua beat + command, reenqueue pending/expired lease, cleanup unreferenced uploads >24h; defaults lease 5 phút heartbeat 30 giây, không giữ DB lock suốt network. Tách số liệu recovered/failed/cleaned để command kiểm tra được.
- [ ] **Step 5 — Chạy lại cùng test:** PASS ở cả BRIDGED_R2_PROBLEMS True/False; mocks không gọi network thật.
- [ ] **Step 6 — Checkpoint:** chưa expose UI cho đến Task 6 admission guards hoàn chỉnh.

## Task 6: Readiness, field guards và admission dùng chung

**Files:** Modify `judge/problem_authoring/policy.py`, `judge/models/problem.py`, `judge/models/contest.py`, `judge/forms.py`, `judge/views/problem.py`, `judge/judgeapi.py`, `judge/bridge/{django_handler,judge_handler}.py`, `judge/utils/problem_package_guards.py`; Create `judge/tests/test_problem_authoring_policy.py`.

**Interfaces:** `assert_can_submit(problem_id: int, *, existing_submission_id: int | None = None) -> None`; `assert_can_attach_to_contest(problem_id: int) -> None`; `assert_mutation_allowed(problem_id: int, changed_fields: set[str]) -> None`; `publish_problem(context, problem_id: int, *, expected_revision: int, accept_unverified: bool) -> int`. Admission mutex chính là state row lock; legacy ungated không tạo lock/state tự động chỉ do submit.

- [ ] **Step 1 — Test đỏ:** direct submit POST, resubmit/rejudge/judgeapi, bridge request, ContestProblem admin/form/model không cho MISSING/nonready vào chấm/contest. New ready private vẫn chấm được khi có quyền. Legacy hidden contest problem không bị chặn vì is_public=False. `test_statement_and_editorial_edit_while_verifying` pass; `test_grading_mutation_returns_validation_not_500` fail rõ; model save(update_fields) không bypass guard. Publication require visibility + statement/PDF + readiness, non-AC/unverified require accept flag. `test_enqueue_racing_activation_is_serialized` qua TransactionTestCase trên MariaDB ở Task 12.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_policy -v 2`; expected FAIL.
- [ ] **Step 3 — Implement gates:** giữ existing guard cho legacy pending imports đến Task 11, thay broad Problem.save lock bằng diff persisted allowlist field guard; ở model route không có form phải ValidationError an toàn, view/admin dịch thành lỗi. Create Submission và admission lock cùng transaction; rejudge/bridge load+dispatch handshake dùng cùng admission serialization, không nhận dispatch mới khi activation đã claim. Existing queued submissions vẫn được phép drain (không block chính các submission worker đang đợi kết thúc); activation không xảy ra khi một nonterminal còn tồn tại. Kiểm tra fresh DB ở bridge, không chỉ cache. Không gửi source hoặc publish pointer ra judge khi chưa đúng active revision. Form/ContestProblem.clean+save và admin actions không bypass; readiness gate cho submit, không chỉ is_accessible_by để người tạo vẫn xem nháp được. Admin bulk publish queryset.update thay bằng policy per object.
- [ ] **Step 4 — Chạy lại + regression:** policy, submission/contest test hiện có; expected PASS. Pin test cho Q/QU, CE, IE, AB và terminal status mapping theo model thực tế, không suy P/G là toàn bộ active set.
- [ ] **Step 5 — Checkpoint:** review việc drain queued so với chặn submissions mới; không làm mạng dưới transaction dài nếu thay handshake lease kiểm chứng được.

## Task 7: Kiểm chứng độc lập, source riêng tư và kết quả đúng revision

**Files:** Create `judge/problem_authoring/verification.py`, `judge/tests/test_problem_authoring_verification.py`; Modify `judge/tasks/problem_authoring.py`, `judge/judgeapi.py` để tích hợp run dispatch nếu cần; không thay API sandbox judge.

**Interfaces:** `start_verification(context, problem_id: int, *, request_token: UUID, expected_grading_revision: int) -> ProblemReferenceRun`; `dispatch_verification(run_id: UUID) -> None`; `refresh_verification(run_id: UUID) -> ProblemReferenceRun`; `retry_verification(context, run_id: UUID) -> ProblemReferenceRun` cho cùng lượt lỗi hạ tầng. Chấm lại cố ý dùng token mới + run mới.

- [ ] **Step 1 — Test đỏ:** optional source không chặn save; runtime ngoài allowed languages từ chối; start chỉ khi READY và không pending data operation; repeated token trả same run/submission; ambiguous bridge ack/retry không xóa testcase hay tạo submission thứ hai; error publish khác error judge. `test_result_stale_after_grading_change_not_statement_change`; `test_non_ac_does_not_publish_or_delete_problem`; source download unauthorized denied. Pending verification có recovery không phụ thuộc GET editor.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_verification -v 2`; expected FAIL.
- [ ] **Step 3 — Implement:** snapshot grading revision/source digest/runtime trước create Submission+Source, lock source và grading fields khi run active. Dùng judge pipeline sandbox hiện tại, không subprocess compile. Check terminal/submission status trước retry; record run-to-submission bền và idempotent, request bridge trùng cùng submission ID xử lý theo protocol hiện có thay vì reset job P/G. Nếu ack không chắc, đối soát status trước resend. Reconciler gọi refresh, editor GET chỉ đọc trạng thái; stale compare revision/digest/runtime. Sau complete có thể thay source, kết quả cũ giữ lịch sử nhưng không đánh dấu current verified.
- [ ] **Step 4 — Chạy lại:** PASS với mock judge và broker mất kết nối; regression import jobs cũ vẫn pass trước Task 11.
- [ ] **Step 5 — Checkpoint:** phân biệt retry infrastructure và intentional rejudge trong API/copy.

## Task 8: Forms và HTTP adapter của trình soạn chung

**Files:** Create `judge/problem_authoring/{forms,views,urls}.py`, `judge/tests/test_problem_authoring_views.py`; Modify `dmoj/urls.py`, `judge/views/{problem,organization}.py`.

**Interfaces:** routes giữ `/problems/create`, `/problem/<code>/edit` và org create; views mới `ProblemAuthoringCreateView`, `ProblemAuthoringEditView`, `OrganizationProblemAuthoringCreateView`. POST action allowlist `upload_tests/upload_package/apply_package/upload_source/save_draft/verify/retry_data/retry_verification/publish`. Scoped upload download route `problem_authoring_download`, chỉ nhận UUID/kind allowlist. Các views dùng Tasks 3–7, không ghi model trực tiếp.

- [ ] **Step 1 — Test đỏ:** create/edit/org/nonstaff staff tương đương; org form kwargs đúng ở mọi nhánh. Form lỗi giữ tất cả field partial/visibility/testers/tags/editorial và valid upload refs. `test_bad_replacement_zip_preserves_editorial`; `test_package_apply_requires_confirmed_sections`; absent checkbox/empty selection không thành default khác; unknown action 400; CSRF 403; permission revoked before POST 403. Save success 302 cùng edit URL, conflict 409 render dữ liệu đã nhập + thông báo không ghi đè. PDF error và broker failure không 500, safe error không lộ server path. GET không mutation trạng thái kiểm chứng.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_views -v 2`; expected FAIL.
- [ ] **Step 3 — Implement forms:** reuse ProblemEditForm validation qua subclass/adapter (time/memory/PDF) nhưng extract service validators, không form.save ở view; `AuthoringMetadataForm` MB↔KB exact, `AuthoringEditorialForm`, `AuthoringTestsForm` plain forms không default absolute_max=1001, `AuthoringReferenceForm`. Section replace explicit; omitted unrelated fields không xóa old data. Required metadata validation khi save; upload actions chỉ validate upload và giữ raw bound other sections, không đòi toàn bộ bài hợp lệ để xem ZIP.
- [ ] **Step 4 — Implement views/routes:** request context server-side, scoped forms, upload token retention, Post/Redirect/Get cho mutations thành công, form errors inline. Mọi action mutation POST; retry/publish/verify recheck permissions/expected revision. Existing title/context/navigation tiếp tục dùng được; legacy package URLs Task 11. File serve FileResponse attachment private, không đường dẫn từ GET; PDF theo policy media hiện có.
- [ ] **Step 5 — Chạy lại:** PASS; add URL reverse regression cho tên route hiện tại.
- [ ] **Step 6 — Checkpoint:** view tests kiểm đủ tổ chức/global thay vì chỉ superuser.

## Task 9: Giao diện thống nhất, thao tác nhanh và không mất chỉnh sửa

**Files:** Create `templates/problem/authoring.html`, partials `templates/problem/authoring/{metadata,statement,editorial,tests,reference,status}.html`, `resources/problem-authoring.js`, `resources/problem-authoring.scss`; Modify template/static inclusion theo pipeline đang có và locale/vi khi cần; Extend `judge/tests/test_problem_authoring_views.py`.

**Interfaces:** context `metadata_form/editorial_form/tests_form/reference_form`, `upload_preview`, `authoring_state`, `reference_run`, `capabilities`, `revision`, `request_token`. Progressive enhancement, server POST là fallback đầy đủ.

- [ ] **Step 1 — Test đỏ:** rendered sections có đề/editorial/ZIP test cùng form; accept trường upload rõ; only permitted publish/PDF/package controls xuất hiện; old source/test không embedded trong HTML public; imported preview count và paired filenames escaped. Form retained test từ Task 8 assert nội dung hiển thị chứ không chỉ context. Keyboard labels/field errors và status live region có thể kiểm tra từ markup.
- [ ] **Step 2 — Chạy:** view tests expected FAIL vì template/controls thiếu.
- [ ] **Step 3 — Implement UI:** theo style.md, một trang có sections, ZIP package là lối tắt không phải luồng chính. Primary `Lưu nháp`, actions sau lưu `Chấm lời giải chuẩn`, `Xem bài`, `Công khai` theo capability; status lưu/dữ liệu/kiểm chứng riêng, non-AC/stale rõ ràng. Preview replacement nêu sections + xác nhận trước apply, test weights bulk edit và natural order; bảng nhiều test phân trang/vùng cuộn không dựng hàng nghìn Martor widgets. Không khóa statement/editorial khi worker active. Warn unsaved navigation; giữ selected upload references thay vì cố set file input; JS không bắt buộc. Status polling read-only có timeout/backoff chỉ khi operation active, không mutate GET. Dùng text an toàn/escaping; không inline raw manifest source vào script.
- [ ] **Step 4 — Verify:** view tests PASS; `npm ci`/`./make_style.sh` theo environment project, build không lỗi; `collectstatic --noinput` với test settings. Browser smoke ở Task 12 (không tự dùng preview để kiểm tra nếu user chưa yêu cầu browser).
- [ ] **Step 5 — Checkpoint:** review UI/copy và mobile overflow qua người dùng hoặc công cụ browser khi được yêu cầu; chưa tuyên bố đã kiểm chứng trực quan nếu chưa làm.

## Task 10: Admin và dữ liệu nâng cao đi qua cùng policy

**Files:** Modify `judge/admin/problem.py`, `judge/views/problem_data.py`, `judge/views/problem.py` (Polygon), `judge/tasks/problem.py`, `judge/models/contest.py`, admin contest module đang register ContestProblem (locate trước sửa); Create admin change template override nếu cần; Extend policy/views tests.

**Interfaces:** `begin_external_data_change(context, problem_id: int, *, expected_revision: int) -> UUID`, `finish_external_data_change(operation_id: UUID) -> None` trong `data.py`; advanced adapter capture full config/artifacts và dùng operation Task 5. Legacy problem adoption khởi tạo state READY chỉ sau xác minh current dataset, không đánh dấu mọi bài cũ MISSING.

- [ ] **Step 1 — Test đỏ:** admin add GET redirect same editor nhưng POST add không bypass create; admin change metadata giữ tất cả special fields và source, data edits active => form error không 500. Admin bulk public enforce visibility/readiness + cảnh báo unverified. Advanced data edit và Polygon publish làm stale verification/revision; advanced checker/grader/subtasks không bị reset khi soạn đề/save nháp. `test_legacy_non_r2_advanced_edit_waits_for_active_submissions`; direct advanced POST không vượt quota/guard.
- [ ] **Step 2 — Chạy:** policy/views + `judge.tests.test_problem_releases`; expected mới FAIL.
- [ ] **Step 3 — Admin:** override add_view redirect GET to problem_create, POST add không ghi model bằng flow cũ (redirect có message hoặc 405); change form thêm link nổi bật trình soạn; admin model forms/actions gọi field/publish policy. Không thay authors/taxonomy/admin-only fields bằng defaults site form. Kiểm tra queryset.update bypass với từng action, không chỉ save_model.
- [ ] **Step 4 — Advanced:** ProblemDataView bind/validate cấu hình hiện có nhưng stage toàn bộ artifacts (zip/generator/checker/grader/header/init) để Task 5 activate, không ghi thẳng active dir. Polygon create/update dùng admission lock trước importer mutation và backup/recovery wrapper; không execute package code trên web. Nếu pending old submissions, update trả validation chờ trước mọi filesystem write, không sửa rồi mới kiểm tra. Publish task dùng cùng per-problem operation serialization, tránh old publish ghi đè new pointer. Revision thay ở transaction của mutation, không đánh dấu verification stale chỉ khi worker cuối cùng xong.
- [ ] **Step 5 — Verify:** tests PASS; chạy regression organization quota và Polygon hiện có (locate test module tên thật trước chạy). Có test rollback fault không mất grader/checker cũ.
- [ ] **Step 6 — Checkpoint:** kiểm tất cả đường mutation để không có UI chung nhưng đường quản trị bỏ qua invariant.

## Task 11: Tương thích ZIP cũ và chuyển tiếp an toàn

**Files:** Modify `judge/views/problem_package.py`, `judge/package_urls.py`, `judge/tasks/problem_package.py`, `judge/utils/problem_package_import.py`, `judge/utils/problem_package_guards.py`, `judge/management/commands/reconcile_problem_authoring.py`; Create `judge/tests/test_problem_authoring_legacy.py`; Modify `judge/tests/test_problem_package_import.py` theo public behavior mới, không xóa test lỗi để làm suite xanh.

**Interfaces:** `adopt_legacy_draft(context, package_import_id: UUID) -> ProblemAuthoringUpload`; command `reconcile_problem_authoring --legacy-check` report counts/statuses, read-only; `--adopt-legacy-finished` idempotent cho finished/failed đã có bài và không job active. Không tự chạy job hoặc resubmit trong migration.

- [ ] **Step 1 — Test đỏ:** old upload GET redirect create; draft detail redirect editor/create với scope sau kiểm tra owner, expired 24h yêu cầu reupload. Duplicate adoption trả same upload. Existing completed import giữ downloads/source/submission, FINISHED result không tự coi hợp lệ nếu thiếu revision evidence (hiển thị legacy). Pending PUBLISHING/SUBMITTING/JUDGING vẫn do worker cũ drain, không tạo new op/run trùng; edit liên quan locked với validation; GET không đổi state. Private legacy download vẫn kiểm quyền.
- [ ] **Step 2 — Chạy:** `python manage.py test judge.tests.test_problem_authoring_legacy judge.tests.test_problem_package_import -v 2`; expected mới FAIL.
- [ ] **Step 3 — Implement adapters:** giữ archive_path và require_access cho records cũ; mapping legacy draft thành upload refs với checksum/scope, không ghi đè saved fields từ manifest. New UI không gọi confirm_import cũ; worker cũ giữ API trong giai đoạn drain. Reconciler cập nhật terminal import từ submission bền thay cho editor GET. Không drop model/permission/file legacy; bỏ broad legacy guard chỉ khi không còn pending legacy record của bài đó. Admin Add không expose old package create bypass.
- [ ] **Step 4 — Verify:** full package/parser/import/release legacy suite PASS; migration không chạy network/job và không đổi source/result.
- [ ] **Step 5 — Checkpoint:** ghi rollout order trong tài liệu: schema additive, deploy compatible workers, legacy check/drain, enable new paths; production thực thi là yêu cầu riêng.

## Task 12: Kiểm thử tích hợp, concurrency và bàn giao

**Files:** Create `judge/tests/test_problem_authoring_concurrency.py`; Update spec và tạo `docs/problem-authoring.md` hướng dẫn người ra đề/operator, cập nhật test config CI hiện có sau khi đọc; không ghi VPS credentials.

**Interfaces:** Không API mới; xác minh các contract Tasks 1–11.

- [ ] **Step 1 — Test đỏ cho race:** TransactionTestCase trên MariaDB với connection riêng/barrier: create quota race chỉ một success; same token đúng một Problem/op; stale forms conflict; submission admission racing activation không thể dùng wrong data; hai worker lease takeover chỉ một activation; expired cleanup racing consume không xóa consumed file. Skip có lý do khi SQLite, bắt buộc chạy trên MariaDB trước tuyên bố concurrency verified.
- [ ] **Step 2 — Chạy trước sửa:** `python manage.py test judge.tests.test_problem_authoring_concurrency -v 2` với MariaDB settings, ghi failures và sửa boundary sở hữu lỗi theo task. Không dùng sleep để làm race pass; dùng barrier/mocks phase deterministic.
- [ ] **Step 3 — Chạy tích hợp:** `python manage.py test judge urlshortener`; `python manage.py check`; `python manage.py makemigrations --check --dry-run`; `flake8`; `python -m compileall -q judge`; `./make_style.sh`; expected exit 0, no migration drift. Phân biệt baseline failure và regression; báo mọi test skipped/fail, không coi compile là thay test. Release tests R2 dùng mock; smoke local compatible storage riêng nếu có, không network production.
- [ ] **Step 4 — Smoke giao diện khi người dùng yêu cầu chạy/browser:** nonstaff tạo từ form + test, import full ZIP rồi sửa editorial, bad replacement không mất sửa, org quota full, retry broker/R2 lỗi, sửa đề khi kiểm chứng, source unauthorized, admin entry, mobile/keyboard. Dùng skill run và công cụ preview khi được yêu cầu; không start server chỉ để chụp tự kiểm tra. Nếu chưa được yêu cầu, đưa checklist này để người dùng chạy và ghi rõ chưa browser-verified.
- [ ] **Step 5 — Viết tài liệu:** ZIP mẫu đủ/thiếu tùy chọn, test-only naming, không bắt buộc source/AC; permissions global/org/PDF/import, status/retry/recovery/retention, private mounts, settings caps, command read-only legacy check. Giải thích draft cần metadata model tối thiểu và không thể chèn contest trước READY. Không chép bình luận/tài liệu cũ làm bằng chứng đúng của code.
- [ ] **Step 6 — Final review và evidence:** dùng verification-before-completion trước success claims; review toàn diff với requesting-code-review theo phương thức thực thi được chọn. Fix findings, rerun tests liên quan; báo migration count, test totals/fail/skips và phần chưa kiểm tra. Không push/commit/deploy nếu chưa được yêu cầu; khi commit được phép, kết thúc message `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

## Self-review kế hoạch

- Spec coverage: UX/source/ZIP (2, 7–9), durable save+PDF (3–5), locks/recovery/quota (3–6,12), readiness/publication/contest (6), admin/advanced/Polygon (10), legacy compatibility (11), security/testing (2–4,8,12).
- Type consistency: views consume SaveResult; operations nhận UUID, không nhận filesystem path từ client; CaseSpec chung parser/service/compiler; grading_revision không đổi cho statement/editorial. Mọi helper xuyên task có signature ở Interfaces hoặc phần types.
- Review Focus: năm lớp lỗi đều có test được chỉ định tại task sở hữu; MariaDB races không được suy từ SQLite.
- Scope: không triển khai multi-problem import, custom config UI, autosave, cloud secrets hoặc deployment. Không viết code sản phẩm trong bước lập kế hoạch.
- Safety rollout: pending legacy workers được giữ; migration additive, không xóa dữ liệu hoặc tự resubmit. Quyền/quota không dựa vào frontend. Operation install không phát hành trước admission gates.

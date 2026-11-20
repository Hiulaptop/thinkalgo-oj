import uuid
from dataclasses import replace
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from judge.models import Organization, Problem, ProblemAuthoringState, ProblemAuthoringUpload, ProblemGroup, ProblemType
from judge.problem_authoring.forms import AuthoringCaseForms, AuthoringMetadataForm
from judge.problem_authoring.policy import authorize_create, authorize_edit
from judge.problem_authoring.service import save_draft
from judge.problem_authoring.storage import upload_path
from judge.problem_authoring.types import AuthoringContext, AuthoringError, ConflictError
from judge.problem_authoring.uploads import get_upload, receive_upload


class ProblemAuthoringCreateView(LoginRequiredMixin, View):
    actions = {'save_draft', 'upload_tests', 'upload_package', 'apply_package', 'upload_source',
               'verify', 'retry_data', 'retry_verification', 'publish', 'adopt_legacy', 'apply_test_points'}

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.problem = None
        self.organization = None
        self.upload_preview = None

    def _context(self):
        if 'problem' in self.kwargs:
            self.problem = get_object_or_404(Problem, code=self.kwargs['problem'], deleted_at__isnull=True)
            self.organization = self.problem.organization
        elif 'slug' in self.kwargs:
            self.organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
        request_organization = getattr(self.request, 'organization', None)
        if request_organization is not None and (
                self.organization is None or self.organization.pk != request_organization.pk):
            raise AuthoringError('permission_denied', 'You cannot manage another scope from this organization site.')
        context = AuthoringContext(self.request.user.pk, self.organization.pk if self.organization else None)
        (authorize_edit(context, self.problem) if self.problem else authorize_create(context))
        return context

    def _initial(self):
        values = {'request_token': uuid.uuid4(), 'revision': 0}
        if self.problem:
            state = ProblemAuthoringState.objects.filter(problem=self.problem).first()
            values['revision'] = state.revision if state else 0
            values['memory_mb'] = Decimal(self.problem.memory_limit) / 1024
            try:
                values['reference_language'] = self.problem.reference_source.language_id
            except self.problem.__class__.reference_source.RelatedObjectDoesNotExist:
                pass
        else:
            values.update(memory_mb=256, partial=True, time_limit=1, points=100)
            group = ProblemGroup.objects.order_by('pk').first()
            kind = ProblemType.objects.order_by('pk').first()
            values.update(group=group.pk if group else None, types=[kind.pk] if kind else [])
            if self.organization:
                values['code'] = ''.join(char for char in self.organization.slug.lower() if char.isalnum()) + '_'
        return values

    def _form(self, data=None):
        kwargs = {'user': self.request.user, 'instance': self.problem, 'initial': self._initial()}
        if self.organization:
            kwargs['org_pk'] = self.organization.pk
        return AuthoringMetadataForm(data=data, files=self.request.FILES or None, **kwargs)

    def _language_limits(self, data=None):
        from judge.forms import LanguageLimitFormSet
        return LanguageLimitFormSet(
            data=data if data is not None and 'limits-TOTAL_FORMS' in data else None,
            instance=self.problem, prefix='limits', form_kwargs={'user': self.request.user},
        )

    def _testcases(self, data=None):
        upload_id = data.get('tests_upload_id') if data is not None else None
        if not upload_id:
            return None
        context = AuthoringContext(self.request.user.pk, self.organization.pk if self.organization else None)
        try:
            upload = get_upload(context, upload_id, kind='TESTS', for_consumption=True,
                                problem_id=self.problem.pk if self.problem else None)
        except AuthoringError as exc:
            if exc.code != 'invalid_upload':
                raise
            upload = get_upload(context, upload_id, kind='PACKAGE', for_consumption=True,
                                problem_id=self.problem.pk if self.problem else None)
        self.upload_preview = self.upload_preview or upload
        initial = [{key: case[key] for key in ('input_file', 'output_file', 'order', 'points', 'is_pretest')
                    if key in case} for case in upload.manifest['tests']]
        bound = data if 'testcases-TOTAL_FORMS' in data else None
        return AuthoringCaseForms(data=bound, initial=initial, prefix='testcases',
                                  expected_pairs=[(case['input_file'], case['output_file']) for case in initial])

    def _render(self, form, status=200):
        try:
            testcase_forms = self._testcases(form.data if form.is_bound else form.initial)
        except AuthoringError as exc:
            testcase_forms = None
            if form.is_bound:
                form.is_valid()
                form.add_error(None, exc.message)
        state = ProblemAuthoringState.objects.filter(problem=self.problem).select_related('current_operation').first() \
            if self.problem else None
        run = (self.problem.reference_runs.select_related('submission').order_by('-created').first()
               if self.problem else None)
        return render(self.request, 'problem/authoring.html', {
            'title': 'Soạn bài tập', 'form': form, 'object': self.problem, 'problem': self.problem,
            'organization': self.organization, 'authoring_state': state, 'reference_run': run,
            'language_limit_formset': self._language_limits(form.data if form.is_bound else None),
            'testcase_forms': testcase_forms,
            'saved_uploads': (self.problem.authoring_uploads.order_by('-created')
                              if self.problem else ProblemAuthoringUpload.objects.none()),
            'upload_preview': self.upload_preview,
            'legacy_package_id': self.request.GET.get('package_id') if self.problem is None else None,
            'capabilities': {
                'package': self.request.user.has_perm('judge.import_problem_package'),
                'pdf': self.request.user.has_perm('judge.upload_file_statement'),
                'publish': self.request.user.has_perm('judge.change_public_visibility'),
            },
        }, status=status)

    def _status(self):
        from judge.models import ProblemReferenceSource
        state = ProblemAuthoringState.objects.select_related('current_operation').filter(problem=self.problem).first()
        run = self.problem.reference_runs.select_related('submission').order_by('-created').first()
        ready = bool(state and state.data_state == 'READY' and (
            not state.current_operation_id or state.current_operation.state == 'READY'))
        busy = bool(run and run.state in ('PENDING', 'DISPATCHING', 'JUDGING'))
        source = ProblemReferenceSource.objects.filter(problem=self.problem).exists()
        return {
            'revision': state.revision if state else 0,
            'grading_revision': state.grading_revision if state else 0,
            'data_state': state.data_state if state else 'LEGACY',
            'operation_state': state.current_operation.state if state and state.current_operation_id else None,
            'safe_error': state.current_operation.safe_error if state and state.current_operation_id else '',
            'run_state': run.state if run else None,
            'result': run.submission.result if run and run.submission_id else None,
            'stale_verification': bool(run and state and run.grading_revision != state.grading_revision),
            'can_verify': ready and source and not busy,
            'can_publish': ready and self.request.user.has_perm('judge.change_public_visibility') and bool(
                self.problem.description.strip() or self.problem.pdf_url),
        }

    def get(self, request, *args, **kwargs):
        try:
            self._context()
            if request.GET.get('status') == '1' and self.problem is not None:
                response = JsonResponse(self._status())
                response['Cache-Control'] = 'private, no-store'
                return response
            return self._render(self._form())
        except AuthoringError as exc:
            from judge.utils.views import generic_message
            return generic_message(request, 'Không có quyền', exc.message, status=403)

    @staticmethod
    def _reset_testcases(data):
        for key in list(data):
            if key.startswith('testcases-'):
                del data[key]

    def _receive_files(self, context, data):
        kinds = (('tests_file', 'tests_upload_id', 'TESTS'),
                 ('reference_file', 'reference_upload_id', 'SOURCE'),
                 ('statement_file', 'pdf_upload_id', 'PDF'))
        for field, reference, kind in kinds:
            if field in self.request.FILES:
                upload = receive_upload(context, self.request.FILES[field], kind,
                                        problem_id=self.problem.pk if self.problem else None)
                data[reference] = str(upload.pk)
                if kind == 'TESTS':
                    self._reset_testcases(data)
                    self.upload_preview = upload

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'save_draft')
        if action not in self.actions:
            return HttpResponseBadRequest('Unsupported editor action.')
        data = request.POST.copy()
        form = None
        try:
            context = self._context()
            if action == 'adopt_legacy':
                if self.problem is not None:
                    raise AuthoringError('invalid_upload', 'Legacy drafts can only start a new problem.')
                from judge.problem_authoring.legacy import adopt_legacy_draft
                upload = adopt_legacy_draft(context, data.get('legacy_package_id'))
                self.upload_preview = upload
                form = self._form(data if 'code' in data else None)
                if not form.is_bound:
                    fields = upload.manifest['fields']
                    form.initial.update({key: fields[key] for key in ('name', 'description', 'time_limit')
                                         if key in fields})
                    if 'memory_limit' in fields:
                        form.initial['memory_mb'] = Decimal(fields['memory_limit']) / 1024
                    form.initial['editorial'] = fields.get('editorial', '')
                    form.initial['package_upload_id'] = upload.pk
                else:
                    data['package_upload_id'] = str(upload.pk)
                    form = self._form(data)
                return self._render(form)
            if action in ('save_draft', 'upload_tests', 'upload_source', 'upload_package', 'apply_package'):
                self._receive_files(context, data)
            if action in ('upload_package', 'apply_package'):
                return self._package(context, data, action)
            if action == 'apply_test_points':
                cases = self._testcases(data)
                if cases is None:
                    raise AuthoringError('missing_tests', 'Upload tests before applying weights.')
                try:
                    points = int(data.get('test_points', ''))
                    if points < 0:
                        raise ValueError
                except ValueError as exc:
                    raise AuthoringError('invalid_tests', 'Enter a nonnegative integer weight.') from exc
                if not cases.is_bound:
                    for index, case in enumerate(cases.initial):
                        for key, value in case.items():
                            data['testcases-%d-%s' % (index, key)] = str(value)
                    data['testcases-TOTAL_FORMS'] = str(len(cases.initial))
                    data['testcases-INITIAL_FORMS'] = str(len(cases.initial))
                for index in range(cases.total_form_count()):
                    data['testcases-%d-points' % index] = str(points)
                return self._render(self._form(data))
            form = self._form(data)
            if action in ('upload_tests', 'upload_source'):
                return self._render(form)
            if action != 'save_draft':
                return self._problem_action(context, data, action, form)
            limits = self._language_limits(data)
            testcases = self._testcases(data)
            valid = form.is_valid()
            if testcases is not None and testcases.is_bound:
                valid = testcases.is_valid() and valid
            if 'limits-TOTAL_FORMS' in data:
                valid = limits.is_valid() and valid
            if valid:
                changes = form.to_changes()
                if testcases is not None and testcases.is_bound:
                    fields = {key: value for key, value in changes.data_fields.items() if key != 'test_points'}
                    changes = replace(changes, cases=testcases.case_specs(), data_fields=fields)
                if 'limits-TOTAL_FORMS' in data:
                    values = []
                    for limit_form in limits.forms:
                        cleaned = limit_form.cleaned_data
                        if cleaned and not cleaned.get('DELETE') and cleaned.get('language'):
                            values.append({'language_id': cleaned['language'].pk,
                                           'time_limit': cleaned.get('time_limit'),
                                           'memory_limit': cleaned.get('memory_limit')})
                    changes = replace(changes, language_limits=values)
                result = save_draft(context, changes, problem_id=self.problem.pk if self.problem else None,
                                    expected_revision=form.cleaned_data['revision'] if self.problem else None,
                                    request_token=form.cleaned_data['request_token'])
                code = Problem.objects.values_list('code', flat=True).get(pk=result.problem_id)
                return HttpResponseRedirect(reverse('problem_edit', args=[code]))
            return self._render(form)
        except AuthoringError as exc:
            form = form or self._form(data)
            form.is_valid()
            form.add_error(None, exc.message)
            status = 409 if isinstance(exc, ConflictError) else 403 if exc.code == 'permission_denied' else 200
            return self._render(form, status=status)

    def _package(self, context, data, action):
        problem_id = self.problem.pk if self.problem else None
        if action == 'upload_package':
            if 'package_file' not in self.request.FILES:
                raise AuthoringError('missing_file', 'Choose a package ZIP file.')
            upload = receive_upload(context, self.request.FILES['package_file'], 'PACKAGE', problem_id=problem_id)
            data['package_upload_id'] = str(upload.pk)
        else:
            upload = get_upload(context, data.get('package_upload_id'), kind='PACKAGE',
                                for_consumption=True, problem_id=problem_id)
            fields = upload.manifest['fields']
            if data.get('replace_statement'):
                for name in ('description', 'name', 'time_limit'):
                    if name in fields:
                        data[name] = fields[name]
                if 'memory_limit' in fields:
                    data['memory_mb'] = Decimal(fields['memory_limit']) / 1024
            if data.get('replace_editorial') and 'editorial' in fields:
                data['editorial'] = fields['editorial']
            if data.get('replace_tests') and upload.manifest['tests']:
                self._reset_testcases(data)
                data['tests_upload_id'] = str(upload.pk)
            if data.get('replace_reference') and upload.manifest.get('source_name'):
                import zipfile
                with zipfile.ZipFile(upload_path(upload)) as archive:
                    with archive.open(upload.manifest['source_name']) as source:
                        import io
                        reference = receive_upload(context, io.BytesIO(source.read()), 'SOURCE', problem_id=problem_id)
                data['reference_upload_id'] = str(reference.pk)
        self.upload_preview = upload
        return self._render(self._form(data))

    def _problem_action(self, context, data, action, form):
        if self.problem is None:
            raise AuthoringError('save_first', 'Save the draft before using this action.')
        try:
            revision = int(data.get('revision', ''))
        except ValueError as exc:
            raise AuthoringError('invalid_revision', 'Reload the editor before using this action.') from exc
        state = ProblemAuthoringState.objects.filter(problem=self.problem).first()
        if state and state.revision != revision:
            raise ConflictError('stale_revision', 'This problem changed. Reload before continuing.')
        if action == 'publish':
            from judge.problem_authoring.policy import publish_problem
            publish_problem(context, self.problem.pk, expected_revision=revision,
                            accept_unverified=bool(data.get('accept_unverified')))
        elif action == 'verify':
            from judge.problem_authoring.verification import start_verification
            try:
                token = uuid.UUID(data.get('request_token', ''))
            except (ValueError, AttributeError) as exc:
                raise AuthoringError('invalid_token', 'Reload the editor before starting verification.') from exc
            start_verification(context, self.problem.pk, request_token=token,
                               expected_grading_revision=state.grading_revision if state else 0)
        elif action == 'retry_data':
            from judge.problem_authoring.data import retry_data_operation
            retry_data_operation(context, self.problem.pk, expected_revision=revision)
        elif action == 'retry_verification':
            from judge.problem_authoring.verification import retry_verification
            run = self.problem.reference_runs.order_by('-created').first()
            if run:
                retry_verification(context, run.pk)
        return HttpResponseRedirect(reverse('problem_edit', args=[self.problem.code]))


class ProblemAuthoringEditView(ProblemAuthoringCreateView):
    pass


class OrganizationProblemAuthoringCreateView(ProblemAuthoringCreateView):
    pass


class AuthoringDownloadView(LoginRequiredMixin, View):
    def get(self, request, upload_id):
        upload = get_object_or_404(ProblemAuthoringUpload, pk=upload_id)
        context = AuthoringContext(request.user.pk, upload.organization_id)
        try:
            upload = get_upload(context, upload.pk, kind=upload.kind, problem_id=upload.consumed_by_id)
        except AuthoringError:
            from django.http import Http404
            raise Http404()
        response = FileResponse(upload_path(upload).open('rb'), as_attachment=True,
                                filename='tests.zip' if upload.kind in ('TESTS', 'PACKAGE') else 'reference-source.txt')
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

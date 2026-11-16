from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from judge.models import Language, ProblemGroup, ProblemPackageImport, ProblemType
from judge.utils.problem_package import PackageValidationError
from judge.utils.problem_package_import import archive_path, confirm_import, create_draft, enqueue_import, \
    require_access, require_import


class PackageMetadataForm(forms.Form):
    code = forms.RegexField(r'^[a-z0-9_]+$', max_length=32)
    name = forms.CharField(max_length=100)
    time_limit = forms.FloatField(min_value=0.01)
    memory_mb = forms.IntegerField(min_value=1)
    points = forms.FloatField(min_value=0, initial=100)
    group = forms.ModelChoiceField(queryset=ProblemGroup.objects.all())
    types = forms.ModelMultipleChoiceField(queryset=ProblemType.objects.all())
    language = forms.ModelChoiceField(queryset=Language.objects.filter(key__startswith='CPP'))


@login_required
def upload(request):
    require_import(request.user)
    error = ''
    if request.method == 'POST':
        try:
            if 'package' not in request.FILES:
                raise PackageValidationError('Choose a ZIP file.')
            record = create_draft(request.user, request.FILES['package'])
            return redirect('problem_package_detail', pk=record.pk)
        except (PackageValidationError, ValidationError) as exc:
            error = str(exc)
    return render(request, 'problem/package-upload.html', {'title': 'Import bài từ ZIP', 'error': error})


@login_required
def detail(request, pk):
    record = get_object_or_404(ProblemPackageImport.objects.select_related('problem', 'submission'), pk=pk)
    require_access(record, request.user)
    form = PackageMetadataForm(request.POST or None, initial=record.manifest)
    if request.method == 'POST' and not record.problem_id:
        if form.is_valid():
            values = form.cleaned_data.copy()
            values['memory_limit'] = values.pop('memory_mb') * 1024
            values['group'] = values['group'].pk
            values['types'] = [item.pk for item in values['types']]
            values['language'] = values['language'].pk
            try:
                confirm_import(record.pk, request.user, values)
                return redirect('problem_package_detail', pk=pk)
            except (ValidationError, PackageValidationError) as exc:
                form.add_error(None, str(exc))
    if record.state == 'JUDGING' and record.submission and record.submission.status in ('D', 'CE', 'IE', 'AB'):
        ProblemPackageImport.objects.filter(pk=pk, state='JUDGING').update(state='FINISHED')
        record.state = 'FINISHED'
    return render(request, 'problem/package-detail.html', {
        'title': 'Import bài từ ZIP', 'record': record, 'form': form,
        'test_count': len(record.manifest['tests']),
    })


@login_required
@require_POST
def retry(request, pk):
    record = get_object_or_404(ProblemPackageImport, pk=pk)
    require_access(record, request.user)
    require_import(request.user)
    if record.problem_id and record.state in ('FAILED', 'PUBLISHING', 'SUBMITTING'):
        enqueue_import(pk)
    return redirect('problem_package_detail', pk=pk)


@login_required
def download(request, pk, kind):
    record = get_object_or_404(ProblemPackageImport, pk=pk)
    require_access(record, request.user)
    if kind == 'source':
        response = FileResponse(archive_path(record).open('rb'), as_attachment=True, filename='package.zip')
    elif kind == 'solution':
        response = HttpResponse(record.manifest['source'], content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="solution.cpp"'
    else:
        from django.http import Http404
        raise Http404
    response['Cache-Control'] = 'private, no-store'
    return response

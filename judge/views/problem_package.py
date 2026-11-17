from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from judge.models import ProblemPackageImport
from judge.utils.problem_package_import import archive_path, enqueue_import, \
    require_access, require_import


@login_required
def upload(request):
    require_import(request.user)
    if request.method == 'POST':
        return HttpResponse('Upload ZIP from the Create problem page.', status=400)
    return redirect('problem_create')


@login_required
def detail(request, pk):
    record = get_object_or_404(ProblemPackageImport.objects.select_related('problem', 'submission'), pk=pk)
    require_access(record, request.user)
    if request.method != 'GET':
        return HttpResponse('Save the package through the Create problem page.', status=400)
    if record.problem_id:
        return redirect('problem_edit', problem=record.problem.code)
    return redirect(reverse('problem_create') + '?package_id=' + str(record.pk))


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

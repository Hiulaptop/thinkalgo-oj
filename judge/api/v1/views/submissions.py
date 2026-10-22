from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from judge.api.v1.adapters import build_submission_list
from judge.api.v1.pagination import HasNextPagination, PAGINATION_PARAMETERS, paginated
from judge.api.v1.serializers.submission import (SubmissionDetailSerializer, SubmissionListItemSerializer,
                                                 SubmissionSourceSerializer)
from judge.jinja2.submission import submission_layout
from judge.models import Submission
from judge.models.problem import ProblemTestcaseResultAccess
from judge.utils.problems import user_completed_ids, user_editable_ids, user_tester_ids
from judge.views.submission import group_test_cases


def _language(language):
    return {'key': language.key, 'name': language.short_display_name}


def _list_row(submission, can_view, problem_name=None):
    return {
        'id': submission.id,
        'date': submission.date,
        'user': {'username': submission.user.user.username, 'display_name': submission.user.display_name},
        'problem': {'code': submission.problem.code, 'name': problem_name or submission.problem.i18n_name},
        'language': _language(submission.language),
        'result': submission.result,
        'status': submission.status,
        'is_graded': submission.is_graded,
        'points': submission.points,
        'case_points': submission.case_points,
        'case_total': submission.case_total,
        'time': submission.time,
        'memory': submission.memory,
        'contest_key': submission.contest_object.key if submission.contest_object_id else None,
        'can_view': can_view,
    }


class SubmissionListView(APIView):
    """Danh sách bài nộp theo đúng quy tắc hiển thị của trang /submissions/."""

    @extend_schema(
        parameters=[
            OpenApiParameter('language', {'type': 'array', 'items': {'type': 'string'}}, explode=True),
            OpenApiParameter('status', {'type': 'array', 'items': {'type': 'string'}}, explode=True),
            OpenApiParameter('organization', int),
        ] + PAGINATION_PARAMETERS,
        responses=paginated(SubmissionListItemSerializer), operation_id='submissions_list')
    def get(self, request):
        view = build_submission_list(request._request)
        paginator = HasNextPagination()
        submissions = paginator.paginate_queryset(view.get_queryset(), request)

        profile = request._request.profile
        profile_id = profile.id if profile is not None else None
        completed = user_completed_ids(profile) if profile is not None else set()
        editable = user_editable_ids(profile) if profile is not None else set()
        testers = user_tester_ids(profile) if profile is not None else set()
        rows = []
        for submission in submissions:
            can_view, _ = submission_layout(submission, profile_id, request.user, completed, editable, testers)
            rows.append(_list_row(submission, bool(can_view)))
        return paginator.get_paginated_response(SubmissionListItemSerializer(rows, many=True).data)


class SubmissionDetailView(APIView):
    """Chi tiết bài nộp. Giống trang Jinja: cần đăng nhập, và chỉ người có quyền xem mới thấy."""

    @extend_schema(responses=SubmissionDetailSerializer, operation_id='submissions_retrieve')
    def get(self, request, pk):
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        submission = get_object_or_404(
            Submission.objects.select_related('problem', 'language', 'judged_on', 'contest_object', 'user__user'),
            pk=pk)
        if not submission.can_see_detail(request.user):
            raise PermissionDenied()

        problem = submission.problem
        mode = problem.testcase_result_visibility_mode
        if request.user.is_superuser or mode == ProblemTestcaseResultAccess.ALL_TEST_CASE:
            visibility = 'all'
        elif mode == ProblemTestcaseResultAccess.ONLY_BATCH_RESULT:
            visibility = 'batch'
        else:
            visibility = 'none'

        batches = []
        if visibility != 'none':
            raw_batches, _, _ = group_test_cases(submission.test_cases.all())
            for batch in raw_batches:
                item = {'id': batch['id'], 'points': batch.get('points'), 'total': batch.get('total'),
                        'status': batch.get('status')}
                if visibility == 'all':
                    item['cases'] = [{'case': c.case, 'status': c.status, 'time': c.time, 'memory': c.memory,
                                      'points': c.points, 'total': c.total} for c in batch['cases']]
                batches.append(item)

        time_limit = problem.time_limit
        limit = problem.language_limits.filter(language=submission.language).first()
        if limit is not None:
            time_limit = limit.time_limit

        data = _list_row(submission, True, problem.translated_name(request._request.LANGUAGE_CODE))
        data.update({
            'error': submission.error,
            'batches': batches,
            'test_case_visibility': visibility,
            'time_limit': time_limit,
            'memory_limit': problem.memory_limit,
        })
        return Response(SubmissionDetailSerializer(data).data)


class SubmissionSourceView(APIView):
    """Mã nguồn bài nộp: cùng điều kiện với chi tiết; ngôn ngữ chỉ nhận tệp thì chỉ superuser xem được."""

    @extend_schema(responses=SubmissionSourceSerializer, operation_id='submissions_source')
    def get(self, request, pk):
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        submission = get_object_or_404(
            Submission.objects.select_related('problem', 'language', 'source', 'contest_object'), pk=pk)
        if not submission.can_see_detail(request.user):
            raise PermissionDenied()
        if submission.language.file_only and not request.user.is_superuser:
            raise NotFound()
        return Response(SubmissionSourceSerializer({
            'language': _language(submission.language),
            'source': submission.source.source.rstrip('\n'),
        }).data)

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from judge.api.v1.adapters import build_problem_list, problem_list_queryset
from judge.api.v1.exceptions import ApiError
from judge.api.v1.pagination import HasNextPagination
from judge.api.v1.serializers.problem import (ProblemDetailSerializer, ProblemFiltersSerializer,
                                              ProblemListItemSerializer)
from judge.jinja2.markdown import markdown
from judge.jinja2.reference import reference
from judge.models import Problem, ProblemGroup, ProblemTranslation, ProblemType
from judge.utils.problems import user_attempted_ids, user_completed_ids

LIST_PARAMETERS = [
    OpenApiParameter('search', str, description='Tìm theo mã, tên, nguồn, tên đã dịch.'),
    OpenApiParameter('category', int, description='Id nhóm đề.'),
    OpenApiParameter('type', {'type': 'array', 'items': {'type': 'integer'}}, explode=True,
                     description='Id loại đề (lặp lại tham số).'),
    OpenApiParameter('point_start', float), OpenApiParameter('point_end', float),
    OpenApiParameter('hide_solved', int, enum=[0, 1], description='1: ẩn đề đã AC (cần đăng nhập).'),
    OpenApiParameter('show_types', int, enum=[0, 1], description='1: kèm danh sách loại đề.'),
    OpenApiParameter('has_public_editorial', int, enum=[0, 1]),
    OpenApiParameter('order', str, description='Khoá sắp xếp, tiền tố "-" để giảm dần.'),
]


def _status(problem_id, solved, attempted):
    if problem_id in solved:
        return 'solved'
    if problem_id in attempted:
        return 'attempted'
    return None


class ProblemListView(APIView):
    """Danh sách đề người dùng được xem; dùng đúng logic lọc/sắp xếp của trang /problems."""

    @extend_schema(parameters=LIST_PARAMETERS, responses=ProblemListItemSerializer(many=True),
                   operation_id='problems_list')
    def get(self, request):
        django_request = request._request
        view = build_problem_list(django_request)
        paginator = HasNextPagination()
        problems = paginator.paginate_queryset(problem_list_queryset(view), request)

        profile = view.profile
        solved = user_completed_ids(profile) if profile is not None else set()
        attempted = user_attempted_ids(profile) if profile is not None else set()
        rows = []
        for problem in problems:
            problem.status = _status(problem.id, solved, attempted)
            if view.show_types:
                problem.types_names = problem.types_list
            rows.append(problem)
        data = ProblemListItemSerializer(rows, many=True).data
        for row, problem in zip(data, rows):
            row['name'] = problem.i18n_name
            if not view.show_types:
                row.pop('types', None)
        return paginator.get_paginated_response(data)


class ProblemFiltersView(APIView):
    @extend_schema(responses=ProblemFiltersSerializer, operation_id='problem_filters')
    def get(self, request):
        groups = [{'id': g.id, 'name': g.full_name} for g in ProblemGroup.objects.all()]
        types = [{'id': t.id, 'name': t.full_name} for t in ProblemType.objects.all()]
        return Response({'groups': groups, 'types': types})


class ProblemDetailView(APIView):
    """Chi tiết đề; 404 nếu không tồn tại hoặc không có quyền xem (không lộ sự tồn tại)."""

    @extend_schema(responses=ProblemDetailSerializer, operation_id='problems_retrieve')
    def get(self, request, code):
        user = request.user
        problem = get_object_or_404(Problem.objects.select_related('group', 'license'), code=code)
        if not problem.is_accessible_by(user):
            raise NotFound()
        if problem.is_deleted:
            raise ApiError('problem_deleted', 'This problem has been deleted.', status_code=410,
                           extra={'name': problem.name})

        language = request._request.LANGUAGE_CODE
        try:
            translation = problem.translations.get(language=language)
        except ProblemTranslation.DoesNotExist:
            name, description, translated = problem.name, problem.description, False
        else:
            name, description, translated = translation.name, translation.description, True

        profile = getattr(request._request, 'profile', None)
        solved = user_completed_ids(profile) if profile is not None else set()
        attempted = user_attempted_ids(profile) if profile is not None else set()

        submission_limit = None
        participation = getattr(request._request, 'participation', None)
        if participation is not None:
            try:
                contest_problem = participation.contest.contest_problems.get(problem=problem)
            except ObjectDoesNotExist:
                contest_problem = None
            if contest_problem is not None:
                submission_limit = contest_problem.max_submissions or None

        data = {
            'code': problem.code,
            'name': name,
            'translated': translated,
            'description_html': str(reference(markdown(description, problem.markdown_style, None))),
            'time_limit': problem.time_limit,
            'memory_limit': problem.memory_limit,
            'points': problem.points,
            'partial': problem.partial,
            'group': problem.group.full_name,
            'types': problem.types_list,
            'source': problem.source,
            'allowed_languages': list(problem.allowed_languages.values_list('key', flat=True)),
            'ac_rate': problem.ac_rate,
            'user_count': problem.user_count,
            'is_public': problem.is_public,
            'status': _status(problem.id, solved, attempted),
            'can_edit': problem.is_editable_by(user),
            'submission_limit': submission_limit,
        }
        return Response(ProblemDetailSerializer(data).data)

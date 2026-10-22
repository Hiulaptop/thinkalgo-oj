from rest_framework.pagination import BasePagination
from rest_framework.response import Response

from judge.api.v1.exceptions import ApiError

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _positive_int(request, name, default, maximum=None):
    raw = request.query_params.get(name)
    if raw is None or raw == '':
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1 or (maximum is not None and value > maximum):
        limit = f'1..{maximum}' if maximum else '>= 1'
        raise ApiError(f'invalid_{name}', f'{name} must be an integer in {limit}.')
    return value


class HasNextPagination(BasePagination):
    """
    Phân trang theo trang, KHÔNG đếm tổng (tránh COUNT(*) trên bảng lớn như bài nộp).
    Lấy page_size + 1 bản ghi để biết còn trang sau hay không, giống InfinitePaginationMixin của Jinja.
    """

    def paginate_queryset(self, queryset, request, view=None):
        self.page = _positive_int(request, 'page', 1)
        self.page_size = _positive_int(request, 'page_size', DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        offset = (self.page - 1) * self.page_size
        window = list(queryset[offset:offset + self.page_size + 1])
        self.has_next = len(window) > self.page_size
        return window[:self.page_size]

    def get_paginated_response(self, data):
        return Response({
            'page': self.page,
            'page_size': self.page_size,
            'has_next': self.has_next,
            'results': data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'required': ['page', 'page_size', 'has_next', 'results'],
            'properties': {
                'page': {'type': 'integer', 'minimum': 1},
                'page_size': {'type': 'integer', 'minimum': 1, 'maximum': MAX_PAGE_SIZE},
                'has_next': {'type': 'boolean'},
                'results': schema,
            },
        }

    def get_schema_operation_parameters(self, view):
        return [
            {'name': 'page', 'required': False, 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1}},
            {'name': 'page_size', 'required': False, 'in': 'query',
             'schema': {'type': 'integer', 'minimum': 1, 'maximum': MAX_PAGE_SIZE, 'default': DEFAULT_PAGE_SIZE}},
        ]

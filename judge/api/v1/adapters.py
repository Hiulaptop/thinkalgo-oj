"""
Bộ điều hợp dùng lại logic lọc/sắp xếp/quyền của các view Jinja.

API không viết lại điều kiện quyền và lọc: nó tạo một thể hiện của lớp view, gọi đúng các
phương thức dựng queryset, chỉ bỏ phần phụ thuộc session (tuỳ chọn lọc phải nằm trong tham số
truy vấn). Nhờ đó API và trang Jinja cho cùng kết quả (spec: "Tương đương với bản Jinja").
"""
from django.db import ProgrammingError

from judge.api.v1.exceptions import ApiError
from judge.views.problem import ProblemList


def resolve_order(view, request):
    """Giống QueryStringSortMixin.get: tham số `order` không hợp lệ thì dùng thứ tự mặc định."""
    order = request.GET.get('order', '')
    if not ((not order.startswith('-') or order.count('-') == 1) and order.lstrip('-') in view.all_sorts):
        order = view.get_default_sort_order(request)
    return order


class StatelessProblemList(ProblemList):
    """ProblemList nhưng tuỳ chọn lọc chỉ lấy từ tham số truy vấn, không đọc/ghi session."""

    def GET_with_session(self, request, key):
        return request.GET.get(key) == '1'


def build_problem_list(request):
    """`request` là HttpRequest của Django (DRF Request._request). Trả về view đã thiết lập, có `.order`."""
    view = StatelessProblemList()
    view.setup(request)
    view.setup_problem_list(request)
    view.order = resolve_order(view, request)
    return view


def problem_list_queryset(view):
    try:
        return view.get_queryset()
    except ProgrammingError as e:
        raise ApiError('invalid_search', 'The search query is not valid.') from e

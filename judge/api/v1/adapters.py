"""
Bộ điều hợp dùng lại logic lọc/sắp xếp/quyền của các view Jinja.

API không viết lại điều kiện quyền và lọc: nó tạo một thể hiện của lớp view, gọi đúng các
phương thức dựng queryset, chỉ bỏ phần phụ thuộc session (tuỳ chọn lọc phải nằm trong tham số
truy vấn). Nhờ đó API và trang Jinja cho cùng kết quả (spec: "Tương đương với bản Jinja").
"""
from django.conf import settings
from django.db import ProgrammingError
from rest_framework.exceptions import NotFound

from judge.api.v1.exceptions import ApiError
from judge.views.blog import ModernBlogList
from judge.views.problem import ProblemList
from judge.views.submission import AllSubmissions
from judge.views.user import UserList


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


def build_user_list(request):
    view = UserList()
    view.setup(request)
    view.order = resolve_order(view, request)
    return view


def build_blog_list(request):
    view = ModernBlogList()
    view.setup(request)
    return view


def build_submission_list(request):
    """
    Giống phần thiết lập đầu của SubmissionsListBase.get: chế độ tiết kiệm (low power) giới hạn
    số trang và chỉ cho lọc một ngôn ngữ/trạng thái; ngược lại cho lọc nhiều giá trị.
    """
    view = AllSubmissions()
    view.setup(request)

    if view.is_in_low_power_mode():
        max_page = settings.VNOJ_LOW_POWER_MODE_CONFIG.get('max_page', 5)
        try:
            if int(request.GET.get('page') or 1) > max_page:
                raise NotFound()
        except ValueError:
            raise NotFound()
        language = request.GET.get('language')
        view.selected_languages = {language} if language else set()
        status = request.GET.get('status')
        view.selected_statuses = {status} if status else set()
        view.selected_organization = None
    else:
        view.selected_languages = set(request.GET.getlist('language'))
        view.selected_statuses = set(request.GET.getlist('status'))
        view.selected_organization = request.GET.get('organization')
    if view.selected_organization:
        try:
            view.selected_organization = int(view.selected_organization)
        except ValueError:
            raise ApiError('invalid_organization', 'organization must be an integer.')
    return view

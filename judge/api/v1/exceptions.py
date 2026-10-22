from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

# `code` ổn định (không dịch) cho frontend; `detail` có thể dịch theo ngôn ngữ yêu cầu.
# Không đưa dữ liệu nội bộ vào detail.
_CODES = {
    exceptions.NotAuthenticated: 'not_authenticated',
    exceptions.AuthenticationFailed: 'authentication_failed',
    exceptions.PermissionDenied: 'permission_denied',
    exceptions.NotFound: 'not_found',
    exceptions.MethodNotAllowed: 'method_not_allowed',
    exceptions.Throttled: 'throttled',
    exceptions.ParseError: 'invalid_request',
    exceptions.ValidationError: 'invalid_request',
}


class ApiError(exceptions.APIException):
    """Lỗi có `code` riêng, vd ApiError('invalid_page_size', 'page_size must be 1-100', 400)."""

    def __init__(self, code, detail, status_code=400, extra=None):
        super().__init__(detail=detail, code=code)
        self.status_code = status_code
        self.api_code = code
        self.extra = extra or {}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, 'api_code', None)
    if code is None:
        for cls, mapped in _CODES.items():
            if isinstance(exc, cls):
                code = mapped
                break
        else:
            code = 'error'

    # Không phân biệt "không tồn tại" và "không có quyền xem" ở chính tài nguyên: view tự ném NotFound.
    if isinstance(exc, exceptions.NotFound):
        detail = _('Not found.')
    elif isinstance(exc, exceptions.APIException) and isinstance(exc.detail, (str, exceptions.ErrorDetail)):
        detail = str(exc.detail)
    else:
        detail = _('Invalid request.')

    data = {'code': code, 'detail': detail}
    data.update(getattr(exc, 'extra', {}))
    if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict):
        data['errors'] = {key: [str(item) for item in (value if isinstance(value, list) else [value])]
                          for key, value in exc.detail.items()}
    headers = {key: value for key, value in response.items()
               if key.lower() in ('retry-after', 'www-authenticate', 'allow')}
    return Response(data, status=response.status_code, headers=headers)

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from judge.api.v1.serializers.user import MeSerializer
from judge.jinja2.gravatar import gravatar

SITE_THEMES = ('light', 'dark', 'auto')


class MeView(APIView):
    """Người dùng hiện tại, hoặc trạng thái ẩn danh. Không bao giờ trả email/IP."""

    @extend_schema(responses=MeSerializer, operation_id='me')
    def get(self, request):
        # Giống Django: người dùng đã đăng nhập dùng Profile.site_theme, khách dùng cookie, mặc định sáng.
        theme = request.COOKIES.get(settings.SITE_THEME_COOKIE_NAME, 'light')
        profile = getattr(request._request, 'profile', None)
        if profile is None:
            data = {
                'authenticated': False, 'username': None, 'display_name': None, 'avatar_url': None,
                'site_theme': theme if theme in SITE_THEMES else 'light',
                'in_contest': False, 'contest_key': None,
            }
        else:
            participation = getattr(request._request, 'participation', None)
            data = {
                'authenticated': True,
                'username': request.user.username,
                'display_name': profile.display_name,
                'avatar_url': gravatar(profile, 80),
                'site_theme': profile.site_theme,
                'in_contest': participation is not None,
                'contest_key': participation.contest.key if participation is not None else None,
            }
        return Response(MeSerializer(data).data)

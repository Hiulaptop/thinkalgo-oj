from operator import attrgetter

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from judge.api.v1.adapters import build_user_list
from judge.api.v1.pagination import HasNextPagination, PAGINATION_PARAMETERS, paginated
from judge.api.v1.serializers.user import RankedUserSerializer
from judge.jinja2.gravatar import gravatar
from judge.ratings import rating_class
from judge.utils.ranker import ranker


class UserRankingView(APIView):
    """Bảng xếp hạng người dùng công khai; cùng truy vấn và cách tính hạng với trang /users/."""

    @extend_schema(
        parameters=[OpenApiParameter('order', str, enum=['points', '-points', 'problem_count', '-problem_count',
                                                         'rating', '-rating', 'performance_points',
                                                         '-performance_points'])] + PAGINATION_PARAMETERS,
        responses=paginated(RankedUserSerializer), operation_id='users_ranking')
    def get(self, request):
        view = build_user_list(request._request)
        paginator = HasNextPagination()
        profiles = paginator.paginate_queryset(view.get_queryset(), request)
        offset = (paginator.page - 1) * paginator.page_size
        rows = []
        for rank, profile in ranker(profiles, key=attrgetter('performance_points', 'problem_count'), rank=offset):
            rows.append({
                'rank': rank,
                'username': profile.user.username,
                'display_name': profile.display_name,
                'avatar_url': gravatar(profile, 80),
                'display_rank': profile.display_rank,
                'rating': profile.rating,
                'rating_class': rating_class(profile.rating) if profile.rating is not None else None,
                'points': profile.points,
                'performance_points': profile.performance_points,
                'problem_count': profile.problem_count,
                'organizations': [{'id': o.id, 'name': o.name, 'slug': o.slug} for o in profile.organizations.all()],
            })
        return paginator.get_paginated_response(RankedUserSerializer(rows, many=True).data)

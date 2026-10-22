from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from judge.api.v1.adapters import build_blog_list
from judge.api.v1.pagination import HasNextPagination, PAGINATION_PARAMETERS, paginated
from judge.api.v1.serializers.blog import BlogPostDetailSerializer, BlogPostListItemSerializer
from judge.jinja2.markdown import markdown
from judge.jinja2.reference import reference
from judge.models import BlogPost


def _html(text, lazy_load=False):
    return str(reference(markdown(text, 'blog', None, lazy_load=lazy_load)))


def _authors(post):
    return [{'username': a.user.username, 'display_name': a.display_name} for a in post.authors.all()]


def _row(post):
    return {
        'id': post.id,
        'slug': post.slug,
        'title': post.title,
        # Giống blog-post.html: dùng tóm tắt, nếu trống thì dùng toàn bộ nội dung.
        'summary_html': _html(post.summary or post.content, lazy_load=True),
        'publish_on': post.publish_on,
        'sticky': post.sticky,
        'score': post.score,
        'authors': _authors(post),
        'tags': [{'name': t.name, 'slug': t.slug} for t in post.tags.all()],
    }


class BlogPostListView(APIView):
    """Danh sách bài blog công khai; dùng đúng truy vấn của trang /blogs/ (tìm kiếm, thẻ, sắp xếp)."""

    @extend_schema(
        parameters=[OpenApiParameter('q', str), OpenApiParameter('tag', str),
                    OpenApiParameter('sort', str, enum=['latest', 'top'])] + PAGINATION_PARAMETERS,
        responses=paginated(BlogPostListItemSerializer), operation_id='blog_posts_list')
    def get(self, request):
        view = build_blog_list(request._request)
        paginator = HasNextPagination()
        posts = paginator.paginate_queryset(view.get_queryset(), request)
        return paginator.get_paginated_response(BlogPostListItemSerializer([_row(p) for p in posts], many=True).data)


class BlogPostDetailView(APIView):
    """Chi tiết bài blog; 404 nếu chưa xuất bản/không có quyền (giống PostView.get_object)."""

    @extend_schema(responses=BlogPostDetailSerializer, operation_id='blog_posts_retrieve')
    def get(self, request, pk):
        post = get_object_or_404(BlogPost.objects.prefetch_related('authors__user', 'tags'), pk=pk)
        if not post.can_see(request.user):
            raise NotFound()
        data = _row(post)
        data['content_html'] = _html(post.content)
        data['organization'] = post.organization.slug if post.organization_id else None
        return Response(BlogPostDetailSerializer(data).data)

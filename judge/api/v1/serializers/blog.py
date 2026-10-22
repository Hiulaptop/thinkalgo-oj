from rest_framework import serializers

from judge.api.v1.serializers.submission import UserRefSerializer


class BlogTagSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()


class BlogPostListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    title = serializers.CharField()
    summary_html = serializers.CharField(help_text='HTML đã render và làm sạch.')
    publish_on = serializers.DateTimeField()
    sticky = serializers.BooleanField()
    score = serializers.IntegerField()
    authors = UserRefSerializer(many=True)
    tags = BlogTagSerializer(many=True)


class BlogPostDetailSerializer(BlogPostListItemSerializer):
    content_html = serializers.CharField(help_text='HTML đã render và làm sạch (cùng pipeline với trang Jinja).')
    organization = serializers.CharField(allow_null=True, help_text='Slug tổ chức nếu bài riêng của tổ chức.')

from rest_framework import serializers


class MeSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    username = serializers.CharField(allow_null=True)
    display_name = serializers.CharField(allow_null=True)
    avatar_url = serializers.URLField(allow_null=True)
    site_theme = serializers.ChoiceField(choices=['light', 'dark', 'auto'])
    in_contest = serializers.BooleanField(help_text='Người dùng đang tham gia một kỳ thi (bị hạn chế truy cập).')
    contest_key = serializers.CharField(allow_null=True)


class OrganizationRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()


class RankedUserSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    avatar_url = serializers.URLField()
    display_rank = serializers.CharField()
    rating = serializers.IntegerField(allow_null=True)
    rating_class = serializers.CharField(allow_null=True)
    points = serializers.FloatField()
    performance_points = serializers.FloatField()
    problem_count = serializers.IntegerField()
    organizations = OrganizationRefSerializer(many=True)

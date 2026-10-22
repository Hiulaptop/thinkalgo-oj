from rest_framework import serializers


class MeSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    username = serializers.CharField(allow_null=True)
    display_name = serializers.CharField(allow_null=True)
    avatar_url = serializers.URLField(allow_null=True)
    site_theme = serializers.ChoiceField(choices=['light', 'dark', 'auto'])
    in_contest = serializers.BooleanField(help_text='Người dùng đang tham gia một kỳ thi (bị hạn chế truy cập).')
    contest_key = serializers.CharField(allow_null=True)

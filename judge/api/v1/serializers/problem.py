from rest_framework import serializers


class NamedRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ProblemListItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField(help_text='Tên theo ngôn ngữ yêu cầu, rơi về tên gốc nếu chưa dịch.')
    group = serializers.CharField(source='group.full_name')
    points = serializers.FloatField()
    partial = serializers.BooleanField()
    ac_rate = serializers.FloatField()
    user_count = serializers.IntegerField()
    date = serializers.DateTimeField(allow_null=True)
    has_public_editorial = serializers.BooleanField()
    types = serializers.ListField(child=serializers.CharField(), required=False, source='types_names',
                                  help_text='Chỉ có khi show_types=1.')
    status = serializers.ChoiceField(choices=['solved', 'attempted'], allow_null=True,
                                     help_text='Trạng thái của người xem; null nếu chưa nộp hoặc ẩn danh.')


class ProblemFiltersSerializer(serializers.Serializer):
    groups = NamedRefSerializer(many=True)
    types = NamedRefSerializer(many=True)


class ProblemDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    translated = serializers.BooleanField(help_text='Nội dung đã được dịch sang ngôn ngữ yêu cầu.')
    description_html = serializers.CharField(help_text='HTML đã render và làm sạch (cùng pipeline với trang Jinja).')
    time_limit = serializers.FloatField()
    memory_limit = serializers.IntegerField(help_text='KB.')
    points = serializers.FloatField()
    partial = serializers.BooleanField()
    group = serializers.CharField()
    types = serializers.ListField(child=serializers.CharField())
    source = serializers.CharField(allow_blank=True)
    allowed_languages = serializers.ListField(child=serializers.CharField(), help_text='Khoá ngôn ngữ cho phép.')
    ac_rate = serializers.FloatField()
    user_count = serializers.IntegerField()
    is_public = serializers.BooleanField()
    status = serializers.ChoiceField(choices=['solved', 'attempted'], allow_null=True)
    can_edit = serializers.BooleanField()
    submission_limit = serializers.IntegerField(allow_null=True, help_text='Giới hạn lần nộp trong kỳ thi hiện tại.')

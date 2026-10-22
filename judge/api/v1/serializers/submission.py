from rest_framework import serializers


class UserRefSerializer(serializers.Serializer):
    username = serializers.CharField()
    display_name = serializers.CharField()


class ProblemRefSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class LanguageRefSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField(help_text='Tên ngắn dùng trong danh sách.')


class SubmissionListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateTimeField()
    user = UserRefSerializer()
    problem = ProblemRefSerializer()
    language = LanguageRefSerializer()
    result = serializers.CharField(allow_null=True, help_text='AC, WA, TLE... hoặc null khi chưa chấm xong.')
    status = serializers.CharField(help_text='QU, P, G, D, IE, CE, AB.')
    is_graded = serializers.BooleanField()
    points = serializers.FloatField(allow_null=True)
    case_points = serializers.FloatField()
    case_total = serializers.FloatField()
    time = serializers.FloatField(allow_null=True)
    memory = serializers.FloatField(allow_null=True, help_text='KB.')
    contest_key = serializers.CharField(allow_null=True)
    can_view = serializers.BooleanField(help_text='Người xem được mở chi tiết/mã nguồn của bài nộp này.')


class TestCaseSerializer(serializers.Serializer):
    case = serializers.IntegerField()
    status = serializers.CharField()
    time = serializers.FloatField(allow_null=True)
    memory = serializers.FloatField(allow_null=True)
    points = serializers.FloatField(allow_null=True)
    total = serializers.FloatField(allow_null=True)


class BatchSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True, help_text='null cho nhóm test không thuộc batch nào.')
    points = serializers.FloatField(allow_null=True)
    total = serializers.FloatField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    cases = TestCaseSerializer(many=True, required=False, help_text='Chỉ có khi được phép xem trạng thái từng test.')


class SubmissionDetailSerializer(SubmissionListItemSerializer):
    error = serializers.CharField(allow_null=True, allow_blank=True, help_text='Thông báo biên dịch/lỗi hệ thống.')
    batches = BatchSerializer(many=True)
    test_case_visibility = serializers.ChoiceField(choices=['all', 'batch', 'none'])
    time_limit = serializers.FloatField()
    memory_limit = serializers.IntegerField()


class SubmissionSourceSerializer(serializers.Serializer):
    language = LanguageRefSerializer()
    source = serializers.CharField()

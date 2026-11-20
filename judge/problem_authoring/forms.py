from decimal import Decimal

from django import forms
from django.urls import reverse_lazy
from django.utils import timezone

from judge.forms import ProblemEditForm
from judge.models import CHECKERS, Language, Profile
from judge.problem_authoring.types import CaseSpec, DraftChanges
from judge.widgets import HeavySelect2MultipleWidget, MartorWidget


class AuthoringCaseForm(forms.Form):
    input_file = forms.CharField(max_length=100, widget=forms.HiddenInput)
    output_file = forms.CharField(max_length=100, widget=forms.HiddenInput)
    order = forms.IntegerField(min_value=1, label='Thứ tự')
    points = forms.IntegerField(min_value=0, label='Trọng số')
    is_pretest = forms.BooleanField(required=False, label='Pretest')


class AuthoringCaseFormSet(forms.BaseFormSet):
    def __init__(self, *args, expected_pairs, **kwargs):
        self.expected_pairs = set(expected_pairs)
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        pairs = [(form.cleaned_data['input_file'], form.cleaned_data['output_file']) for form in self.forms
                 if form.cleaned_data]
        orders = [form.cleaned_data['order'] for form in self.forms if form.cleaned_data]
        if (len(pairs) != len(self.expected_pairs) or set(pairs) != self.expected_pairs or
                len(orders) != len(set(orders))):
            raise forms.ValidationError('Each uploaded test must appear once, with a distinct order.')

    def case_specs(self):
        return [CaseSpec(**form.cleaned_data) for form in sorted(
            self.forms, key=lambda form: form.cleaned_data['order'],
        ) if form.cleaned_data]


AuthoringCaseForms = forms.formset_factory(
    AuthoringCaseForm, formset=AuthoringCaseFormSet, extra=0, max_num=4998, validate_max=True, absolute_max=4998,
)


class AuthoringMetadataForm(ProblemEditForm):
    memory_mb = forms.DecimalField(min_value=Decimal('0.0009765625'), decimal_places=10,
                                   initial=256, label='Bộ nhớ (MB)')
    allowed_languages = forms.ModelMultipleChoiceField(queryset=Language.objects.all(), required=False,
                                                       label='Ngôn ngữ được phép nộp')
    editorial = forms.CharField(required=False, label='Editorial (Markdown)',
                                widget=MartorWidget(attrs={'data-markdownfy-url': reverse_lazy('solution_preview')}))
    editorial_is_public = forms.BooleanField(required=False, label='Công khai editorial theo lịch đã chọn')
    editorial_publish_on = forms.DateTimeField(required=False, label='Lịch công khai editorial',
                                               widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M',
                                                                          attrs={'type': 'datetime-local'}))
    editorial_authors = forms.ModelMultipleChoiceField(
        queryset=Profile.objects.all(), required=False, label='Tác giả editorial',
        widget=HeavySelect2MultipleWidget(data_view='profile_select2'),
    )
    tests_file = forms.FileField(required=False, label='Bộ test ZIP')
    reference_file = forms.FileField(required=False, label='Mã nguồn lời giải chuẩn')
    reference_language = forms.ModelChoiceField(queryset=Language.objects.all(), required=False,
                                                label='Runtime lời giải chuẩn')
    package_file = forms.FileField(required=False, label='ZIP trọn gói')
    tests_upload_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    reference_upload_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    package_upload_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    pdf_upload_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput, initial=0)
    request_token = forms.UUIDField(widget=forms.HiddenInput)
    accept_unverified = forms.BooleanField(required=False, label='Xác nhận công khai khi chưa kiểm chứng AC')
    replace_statement = forms.BooleanField(required=False, label='Thay đề bài')
    replace_editorial = forms.BooleanField(required=False, label='Thay editorial')
    replace_tests = forms.BooleanField(required=False, label='Thay bộ test')
    replace_reference = forms.BooleanField(required=False, label='Thay mã nguồn chuẩn')
    checker = forms.ChoiceField(choices=[choice for choice in CHECKERS if choice[0] != 'bridged'],
                                initial='standard', required=False, label='Checker')
    test_points = forms.IntegerField(min_value=0, initial=1, required=False, label='Trọng số mỗi test')

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields.pop('is_public', None)
        if not self.user.has_perm('judge.change_public_visibility'):
            self.fields.pop('editorial_is_public', None)
        self.fields['memory_limit'].widget = forms.HiddenInput()
        self.fields['memory_limit'].required = False
        self.fields['allowed_languages'].initial = (
            instance.allowed_languages.all() if instance and instance.pk else
            Language.objects.filter(include_in_problem=True)
        )
        if instance and instance.pk:
            self.fields['memory_mb'].initial = Decimal(instance.memory_limit) / 1024
            try:
                self.fields['editorial'].initial = instance.solution.content
                if 'editorial_is_public' in self.fields:
                    self.fields['editorial_is_public'].initial = instance.solution.is_public
                self.fields['editorial_publish_on'].initial = instance.solution.publish_on
                self.fields['editorial_authors'].initial = instance.solution.authors.all()
            except instance.__class__.solution.RelatedObjectDoesNotExist:
                pass
        self.order_fields(['code', 'name', 'time_limit', 'memory_mb', 'points', 'partial', 'group', 'types',
                           'tags', 'source', 'description', 'statement_file', 'editorial', 'tests_file',
                           'checker', 'test_points', 'reference_file', 'reference_language'])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('memory_mb'):
            kilobytes = cleaned['memory_mb'] * 1024
            if kilobytes != kilobytes.to_integral_value():
                self.add_error('memory_mb', 'Memory must represent a whole number of KB.')
            else:
                cleaned['memory_limit'] = int(kilobytes)
        return cleaned

    def to_changes(self):
        cleaned = self.cleaned_data
        scalar = ('code', 'name', 'description', 'time_limit', 'memory_limit', 'points', 'partial', 'source',
                  'submission_source_visibility_mode', 'testcase_visibility_mode')
        fields = {key: cleaned[key] for key in scalar if key in cleaned}
        fields['group_id'] = cleaned['group'].pk
        for name in ('types', 'tags', 'testers', 'allowed_languages'):
            if name in cleaned:
                fields[name] = list(cleaned[name].values_list('pk', flat=True))
        data_fields = {
            'checker': cleaned.get('checker') or 'standard',
            'test_points': cleaned['test_points'] if cleaned.get('test_points') is not None else 1,
        }
        solution_fields = {'content': cleaned.get('editorial', '')}
        if 'editorial_is_public' in self.fields:
            solution_fields['is_public'] = cleaned.get('editorial_is_public', False)
        if 'editorial_publish_on' in self.data:
            solution_fields['publish_on'] = cleaned.get('editorial_publish_on') or timezone.now()
        if 'editorial_authors' in self.data or self.data.get('editorial_authors_present'):
            solution_fields['authors'] = list(cleaned['editorial_authors'].values_list('pk', flat=True))
        return DraftChanges(problem_fields=fields, solution_fields=solution_fields,
                            test_upload_id=cleaned.get('tests_upload_id'), data_fields=data_fields,
                            pdf_upload_id=cleaned.get('pdf_upload_id'),
                            reference_upload_id=cleaned.get('reference_upload_id'),
                            reference_language_id=getattr(cleaned.get('reference_language'), 'pk', None))

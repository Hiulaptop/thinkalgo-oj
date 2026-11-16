from django.core.exceptions import ValidationError


def assert_package_mutable(problem_id):
    from judge.models import ProblemPackageImport
    if problem_id and ProblemPackageImport.objects.filter(
        problem_id=problem_id, state__in=('PUBLISHING', 'SUBMITTING', 'JUDGING'),
    ).exists():
        raise ValidationError('ZIP reference verification is active. Wait for it to finish before changing this problem.')

import uuid

from django.db import models
from django.utils import timezone


class ProblemPackageImport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey('Profile', on_delete=models.CASCADE)
    problem = models.OneToOneField('Problem', null=True, blank=True, on_delete=models.CASCADE,
                                   related_name='package_import')
    submission = models.OneToOneField('Submission', null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='reference_import')
    language = models.ForeignKey('Language', null=True, on_delete=models.PROTECT)
    manifest = models.JSONField(default=dict)
    state = models.CharField(max_length=32, default='AWAITING_CONFIRMATION')
    error = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)
    release_version = models.CharField(max_length=64, blank=True)
    release_sha256 = models.CharField(max_length=64, blank=True)

    class Meta:
        permissions = [('import_problem_package', 'Import problem ZIP packages')]

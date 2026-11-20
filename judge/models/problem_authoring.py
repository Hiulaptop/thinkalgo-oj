import uuid

from django.db import models
from django.utils import timezone


class ProblemAuthoringState(models.Model):
    problem = models.OneToOneField('Problem', on_delete=models.CASCADE, related_name='authoring_state')
    revision = models.PositiveIntegerField(default=0)
    grading_revision = models.PositiveIntegerField(default=0)
    active_data_revision = models.PositiveIntegerField(default=0)
    data_state = models.CharField(max_length=16, default='MISSING')
    current_operation = models.OneToOneField('ProblemDataOperation', null=True, blank=True,
                                             on_delete=models.SET_NULL, related_name='+')


class ProblemAuthoringUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey('Profile', on_delete=models.PROTECT, related_name='authoring_uploads')
    organization = models.ForeignKey('Organization', null=True, blank=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=16)
    path = models.CharField(max_length=255, unique=True)
    sha256 = models.CharField(max_length=64)
    manifest = models.JSONField(default=dict)
    size = models.PositiveBigIntegerField(default=0)
    expanded_size = models.PositiveBigIntegerField(default=0)
    created = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    consumed_by = models.ForeignKey('Problem', null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='authoring_uploads')


class ProblemDataOperation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey('Problem', on_delete=models.PROTECT, related_name='data_operations')
    upload = models.ForeignKey(ProblemAuthoringUpload, null=True, blank=True, on_delete=models.PROTECT)
    target_revision = models.PositiveIntegerField()
    config = models.JSONField(default=dict)
    state = models.CharField(max_length=16, default='PENDING', db_index=True)
    phase = models.CharField(max_length=32, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    safe_error = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)


class ProblemAuthoringSave(models.Model):
    actor = models.ForeignKey('Profile', on_delete=models.PROTECT)
    request_token = models.UUIDField()
    payload_sha256 = models.CharField(max_length=64)
    problem = models.ForeignKey('Problem', on_delete=models.CASCADE)
    revision = models.PositiveIntegerField()
    operation = models.ForeignKey(ProblemDataOperation, null=True, blank=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['actor', 'request_token'], name='authoring_actor_save_token')]


class ProblemReferenceSource(models.Model):
    problem = models.OneToOneField('Problem', on_delete=models.CASCADE, related_name='reference_source')
    upload = models.ForeignKey(ProblemAuthoringUpload, on_delete=models.PROTECT)
    language = models.ForeignKey('Language', on_delete=models.PROTECT)


class ProblemReferenceRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey('Problem', on_delete=models.PROTECT, related_name='reference_runs')
    owner = models.ForeignKey('Profile', on_delete=models.PROTECT)
    request_token = models.UUIDField()
    grading_revision = models.PositiveIntegerField()
    source_sha256 = models.CharField(max_length=64)
    upload = models.ForeignKey(ProblemAuthoringUpload, on_delete=models.PROTECT)
    language = models.ForeignKey('Language', on_delete=models.PROTECT)
    submission = models.OneToOneField('Submission', null=True, blank=True, on_delete=models.SET_NULL)
    state = models.CharField(max_length=16, default='PENDING', db_index=True)
    safe_error = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'request_token'], name='authoring_owner_run_token')]

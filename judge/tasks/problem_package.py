import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

from judge.judgeapi import judge_submission
from judge.models import ProblemPackageImport, Submission, SubmissionSource
from judge.utils.problem_releases import publish_problem_to_r2

logger = logging.getLogger(__name__)


@shared_task
def run_import(pk):
    # Serialize retries; publishing and dispatch are bounded by their network timeouts.
    with transaction.atomic():
        record = ProblemPackageImport.objects.select_for_update().select_related('problem', 'language').get(pk=pk)
        if record.state in ('JUDGING', 'FINISHED', 'AWAITING_CONFIRMATION'):
            return
        if record.state == 'SUBMITTING':
            transaction.on_commit(lambda: dispatch_reference.delay(str(pk)))
            return
        try:
            if not record.release_version:
                if not getattr(settings, 'BRIDGED_R2_PROBLEMS', False):
                    raise ValueError('Enable BRIDGED_R2_PROBLEMS and configure problem release storage before judging.')
                manifest = publish_problem_to_r2(record.problem.code, version='import-' + record.pk.hex)
                record.release_version = manifest['version']
                record.release_sha256 = manifest['sha256']
            if not record.submission_id:
                submission = Submission.objects.create(user=record.owner, problem=record.problem,
                                                        language=record.language)
                SubmissionSource.objects.create(submission=submission, source=record.manifest['source'])
                record.submission = submission
            record.state = 'SUBMITTING'
            record.error = ''
            record.save()
            transaction.on_commit(lambda: dispatch_reference.delay(str(pk)))
        except Exception:
            logger.exception('Problem package publishing failed: %s', pk)
            record.state = 'FAILED'
            record.error = 'Unable to publish tests. Check release storage configuration, then retry.'
            record.save()


@shared_task
def dispatch_reference(pk):
    with transaction.atomic():
        record = ProblemPackageImport.objects.select_for_update().select_related('submission').get(pk=pk)
        if record.state != 'SUBMITTING':
            return
        submission = record.submission
        if submission.status in ('P', 'G', 'D', 'CE', 'AB'):
            record.state = 'JUDGING'
        else:
            sent = judge_submission(submission)
            submission.refresh_from_db()
            record.state = 'JUDGING' if sent and submission.status != 'IE' else 'FAILED'
            record.error = '' if record.state == 'JUDGING' else 'Judge dispatch failed. Retry uses the same submission.'
        record.save()

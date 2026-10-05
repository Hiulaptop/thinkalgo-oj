import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from judge.models import Problem
from judge.utils.problems import fast_delete_problem

__all__ = ('problem_garbage_collect', 'publish_problem_release', 'purge_problem_release')

logger = logging.getLogger('judge.tasks')


@shared_task
def problem_garbage_collect():
    problems = Problem.expired_deletion.all()
    end = timezone.now() + settings.VNOJ_PROBLEM_GARBAGE_COLLECTOR_TIME_LIMIT
    for problem in problems:
        if timezone.now() > end:
            break
        fast_delete_problem(problem)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def publish_problem_release(self, code):
    """Re-publish a problem's local test data (including test case points) to R2.

    Runs asynchronously so saving test data in the admin UI does not block
    on an R2 upload. Retries a few times on transient failures (network,
    R2 throttling); if it keeps failing the problem simply keeps grading
    from its last published release until someone retries manually with
    `manage.py publish_problem_release`.
    """
    from judge.utils.problem_releases import publish_problem_to_r2

    try:
        manifest = publish_problem_to_r2(code)
    except Exception as exc:
        logger.exception('Failed to publish R2 release for problem %s', code)
        raise self.retry(exc=exc)
    logger.info('Published R2 release %s@%s (%s)', code, manifest['version'], manifest['sha256'])
    return manifest


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def purge_problem_release(self, code):
    """Delete every R2 release for a problem (the "delete" half), e.g. after the problem is deleted."""
    from judge.utils.problem_releases import purge_releases

    try:
        purge_releases(code)
    except Exception as exc:
        logger.exception('Failed to purge R2 releases for problem %s', code)
        raise self.retry(exc=exc)
    logger.info('Purged R2 releases for problem %s', code)

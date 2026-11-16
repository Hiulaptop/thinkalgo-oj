import shutil

from django.core.management.base import BaseCommand
from django.utils import timezone

from judge.models import ProblemPackageImport
from judge.utils.problem_package_import import archive_path, enqueue_import


class Command(BaseCommand):
    help = 'Recover pending ZIP imports and expire unconfirmed uploads after 24 hours.'

    def handle(self, *args, **options):
        for record in ProblemPackageImport.objects.filter(state__in=('PUBLISHING', 'SUBMITTING')):
            enqueue_import(record.pk)
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        for record in ProblemPackageImport.objects.filter(problem__isnull=True, created__lt=cutoff):
            shutil.rmtree(archive_path(record).parent, ignore_errors=True)
            record.delete()

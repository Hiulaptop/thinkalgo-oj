import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from judge.problem_authoring.data import reconcile_authoring


class Command(BaseCommand):
    help = 'Recover pending shared-editor data operations without creating new problems.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        modes = parser.add_mutually_exclusive_group()
        modes.add_argument('--legacy-check', action='store_true')
        modes.add_argument('--adopt-legacy-finished', action='store_true')

    def handle(self, *args, **options):
        if options['legacy_check']:
            from django.db.models import Count
            from judge.models import ProblemPackageImport
            result = {row['state']: row['total'] for row in ProblemPackageImport.objects.values('state').annotate(
                total=Count('pk'),
            )}
        elif options['adopt_legacy_finished']:
            from judge.problem_authoring.legacy import adopt_finished_legacy
            result = adopt_finished_legacy(limit=max(1, options['limit']))
        else:
            result = reconcile_authoring(now=timezone.now(), limit=max(1, options['limit']))
        self.stdout.write(json.dumps(result, sort_keys=True))

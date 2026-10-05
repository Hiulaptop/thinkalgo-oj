import json

from django.core.management.base import BaseCommand, CommandError

from judge.utils.problem_releases import delete_release, list_releases, purge_releases, read_release_manifest


class Command(BaseCommand):
    help = (
        'Inspect and manage Cloudflare R2 problem releases: list published versions, '
        'read a release manifest, or delete one version / all versions of a problem.'
    )

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action', required=True)

        list_parser = sub.add_parser('list', help='List published release versions for a problem')
        list_parser.add_argument('code')

        show_parser = sub.add_parser('show', help="Print a release's manifest.json")
        show_parser.add_argument('code')
        show_parser.add_argument('version')

        delete_parser = sub.add_parser('delete', help='Delete one release version from R2')
        delete_parser.add_argument('code')
        delete_parser.add_argument('version')

        purge_parser = sub.add_parser('purge', help='Delete every release version for a problem from R2')
        purge_parser.add_argument('code')
        purge_parser.add_argument('--yes', action='store_true', help='Skip the confirmation prompt')

    def handle(self, *args, **options):
        action = options['action']
        try:
            if action == 'list':
                self._list(options['code'])
            elif action == 'show':
                self._show(options['code'], options['version'])
            elif action == 'delete':
                self._delete(options['code'], options['version'])
            elif action == 'purge':
                self._purge(options['code'], options['yes'])
        except Exception as e:
            raise CommandError(str(e)) from e

    def _list(self, code):
        releases = list_releases(code)
        if not releases:
            self.stdout.write(f'No releases found for {code}')
            return
        for release in releases:
            size = release['size']
            size_str = f'{size} bytes' if size is not None else 'unknown size'
            self.stdout.write(f"{release['version']}  {release['last_modified']}  {size_str}")

    def _show(self, code, version):
        manifest = read_release_manifest(code, version)
        self.stdout.write(json.dumps(manifest, indent=2, sort_keys=True))

    def _delete(self, code, version):
        delete_release(code, version)
        self.stdout.write(self.style.SUCCESS(f'Deleted {code}@{version} from R2'))

    def _purge(self, code, confirmed):
        if not confirmed:
            answer = input(f'This will permanently delete ALL R2 releases for "{code}". Type "yes" to continue: ')
            if answer.strip().lower() != 'yes':
                self.stdout.write('Aborted.')
                return
        purge_releases(code)
        self.stdout.write(self.style.SUCCESS(f'Purged all R2 releases for {code}'))

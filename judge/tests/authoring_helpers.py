import io
import tempfile
import zipfile

from django.test import override_settings

from judge.models import Language, Problem, ProblemGroup, ProblemType, problem_data_storage
from judge.models.tests.util import create_user


def make_zip(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    stream.seek(0)
    return stream


class AuthoringTestMixin:
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        settings = override_settings(
            PROBLEM_AUTHORING_ROOT=self.temp.name + '/uploads',
            PROBLEM_PACKAGE_ROOT=self.temp.name + '/packages',
            DMOJ_PROBLEM_DATA_ROOT=self.temp.name + '/data',
        )
        settings.enable()
        self.addCleanup(settings.disable)
        old_location = problem_data_storage._location
        problem_data_storage._location = self.temp.name + '/data'
        for key in ('location', 'base_location'):
            problem_data_storage.__dict__.pop(key, None)
        self.addCleanup(self._restore_storage, old_location)
        self.user = create_user('author', is_superuser=True, is_staff=True)
        self.group = ProblemGroup.objects.create(name='Authoring')
        self.kind = ProblemType.objects.create(name='Authoring')
        self.language = Language.objects.create(key='CPP20', name='C++20', short_name='C++20')

    @staticmethod
    def _restore_storage(location):
        problem_data_storage._location = location
        for key in ('location', 'base_location'):
            problem_data_storage.__dict__.pop(key, None)

    def make_problem(self, code='authoringtest'):
        return Problem.objects.create(
            code=code, name='Authoring test', description='# Statement',
            group=self.group, time_limit=1, memory_limit=262144, points=100,
        )

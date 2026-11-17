import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import yaml
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from judge.models import Language, Problem, ProblemData, ProblemPackageImport, ProblemTestCase, Solution
from judge.utils.problem_data import ProblemDataCompiler
from judge.utils.problem_package import PackageValidationError, inspect_package


def archive_path(record):
    root = getattr(settings, 'PROBLEM_PACKAGE_ROOT', '/private-problem-imports')
    return Path(root) / str(record.pk) / 'source.zip'


def require_access(record, user):
    if not user.is_authenticated:
        raise PermissionDenied
    if record.problem_id:
        allowed = record.problem.is_editable_by(user)
    else:
        allowed = user.is_superuser or record.owner_id == user.profile.pk
    if not allowed:
        raise PermissionDenied


def require_import(user):
    if not user.has_perms(('judge.add_problem', 'judge.import_problem_package')):
        raise PermissionDenied


def create_draft(user, upload):
    require_import(user)
    manifest = inspect_package(upload)
    record = ProblemPackageImport(owner=user.profile, manifest=manifest)
    target = archive_path(record)
    target.parent.mkdir(parents=True, mode=0o700)
    try:
        upload.seek(0)
        with target.open('xb') as out:
            shutil.copyfileobj(upload, out, 65536)
        record.save()
    except Exception:
        shutil.rmtree(target.parent)
        raise
    return record


def enqueue_import(pk):
    from judge.tasks.problem_package import run_import
    try:
        run_import.delay(str(pk))
    except Exception:
        ProblemPackageImport.objects.filter(pk=pk).update(error='Queue unavailable. Retry from this page.')


def confirm_import(pk, user, metadata, *, problem_form=None, solution_formset=None):
    require_import(user)
    target = None
    staging = None
    try:
        with transaction.atomic():
            record = ProblemPackageImport.objects.select_for_update().get(pk=pk)
            require_access(record, user)
            if record.problem_id:
                return record
            if record.created < timezone.now() - timezone.timedelta(hours=24):
                raise ValidationError('Upload expired. Please upload again.')
            with archive_path(record).open('rb') as source:
                manifest = inspect_package(source)
            if manifest['sha256'] != record.manifest['sha256']:
                raise ValidationError('Uploaded archive changed.')
            if len(manifest['tests']) > settings.VNOJ_TESTCASE_HARD_LIMIT and not user.has_perm(
                    'judge.create_mass_testcases'):
                raise ValidationError('Too many test cases.')
            language = Language.objects.get(pk=metadata['language'], key__startswith='CPP')
            if problem_form is not None:
                problem = problem_form.save(commit=False)
                problem.is_public = False
                problem.date = timezone.now()
                problem.save()
                problem_form.save_m2m()
            else:
                problem = Problem(code=metadata['code'], name=metadata['name'],
                                  description=manifest['statement'], time_limit=metadata['time_limit'],
                                  memory_limit=metadata['memory_limit'], points=metadata['points'],
                                  group_id=metadata['group'], partial=True, is_public=False)
                problem.full_clean(exclude=['deleted_at'])
                problem.save()
                problem.types.set(metadata['types'])
            problem.authors.add(user.profile)
            problem.curators.add(user.profile)
            problem.allowed_languages.set(Language.objects.filter(include_in_problem=True))
            problem.allowed_languages.add(language)
            if solution_formset is not None:
                solution_formset.instance = problem
                for solution in solution_formset.save(commit=False):
                    solution.is_public = False
                    solution.save()
                solution_formset.save_m2m()
            else:
                solution = Solution.objects.create(problem=problem, content=manifest['editorial'],
                                                    publish_on=timezone.now(), is_public=False)
                solution.authors.add(user.profile)
            root = Path(settings.DMOJ_PROBLEM_DATA_ROOT)
            root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix='.package-', dir=root))
            files = [name for pair in manifest['tests'] for name in pair]
            with zipfile.ZipFile(archive_path(record)) as original:
                with zipfile.ZipFile(staging / 'tests.zip', 'w', zipfile.ZIP_DEFLATED) as tests:
                    for name in files:
                        with original.open(manifest['root'] + name) as src, tests.open(name, 'w') as dst:
                            shutil.copyfileobj(src, dst, 65536)
            data = ProblemData.objects.create(problem=problem, zipfile=problem.code + '/tests.zip')
            from judge.views.problem_data import ProblemCaseFormSet
            case_values = {'form-TOTAL_FORMS': str(len(manifest['tests'])), 'form-INITIAL_FORMS': '0',
                           'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': str(len(manifest['tests']))}
            for i, pair in enumerate(manifest['tests']):
                for key, value in {'order': i + 1, 'type': 'C', 'input_file': pair[0],
                                   'output_file': pair[1], 'points': 1, 'is_pretest': ''}.items():
                    case_values['form-%d-%s' % (i, key)] = value
            case_forms = ProblemCaseFormSet(case_values, queryset=ProblemTestCase.objects.none(), valid_files=files)
            if not case_forms.is_valid():
                raise ValidationError(str(case_forms.errors) + str(case_forms.non_form_errors()))
            for case in case_forms.save(commit=False):
                case.dataset = problem
                case.save()
            init = ProblemDataCompiler(problem, data, problem.cases.order_by('order'), files).make_init()
            if not init:
                raise PackageValidationError('Empty test configuration.')
            (staging / 'init.yml').write_text(yaml.safe_dump(init), encoding='utf-8')
            destination = root / problem.code
            if destination.exists():
                raise ValidationError('Problem data directory already exists.')
            os.rename(staging, destination)
            target = destination
            data.update_zipfile_size()
            data.save()
            record.problem = problem
            record.language = language
            record.state = 'PUBLISHING'
            record.save()
            transaction.on_commit(lambda: enqueue_import(record.pk))
        return record
    except Exception:
        if target is not None:
            shutil.rmtree(target, ignore_errors=True)
        raise
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)

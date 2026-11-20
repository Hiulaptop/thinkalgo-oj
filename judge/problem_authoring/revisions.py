from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from django.db.models import F


_managed = ContextVar('problem_authoring_managed_revision', default=False)


@contextmanager
def managed_revision():
    token = _managed.set(True)
    try:
        yield
    finally:
        _managed.reset(token)


def manages_revision(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with managed_revision():
            return function(*args, **kwargs)
    return wrapped


def invalidate_revision(problem_id, *, grading=False):
    if _managed.get():
        return
    from judge.models import ProblemAuthoringState
    updates = {'revision': F('revision') + 1}
    if grading:
        updates['grading_revision'] = F('grading_revision') + 1
    ProblemAuthoringState.objects.filter(problem_id=problem_id).update(**updates)

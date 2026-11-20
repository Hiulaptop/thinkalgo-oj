import errno
import os
from typing import Optional

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver
from registration.models import RegistrationProfile
from registration.signals import user_registered

from judge.caching import finished_submission
from judge.models import BlogPost, Comment, Contest, ContestAnnouncement, ContestProblem, ContestSubmission, \
    EFFECTIVE_MATH_ENGINES, Judge, Language, LanguageLimit, License, MiscConfig, Organization, Problem, Profile, \
    Solution, Submission, WebAuthnCredential
from judge.tasks import on_new_comment
from judge.views.register import RegistrationView


def get_pdf_path(basename: str) -> Optional[str]:
    if not settings.DMOJ_PDF_PROBLEM_CACHE:
        return None

    return os.path.join(settings.DMOJ_PDF_PROBLEM_CACHE, basename)


def unlink_if_exists(file):
    try:
        os.unlink(file)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


@receiver(m2m_changed, sender=Problem.allowed_languages.through)
def problem_authoring_languages_guard(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in ('pre_add', 'pre_remove', 'pre_clear'):
        return
    from django.core.exceptions import ValidationError
    from judge.problem_authoring.policy import assert_mutation_allowed
    from judge.problem_authoring.types import AuthoringError
    if reverse:
        ids = pk_set if pk_set is not None else instance.problem_set.values_list('pk', flat=True)
    else:
        ids = [instance.pk]
    try:
        ids = sorted(ids)
        list(Problem.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
        instance._authoring_language_changes = []
        for problem_id in ids:
            assert_mutation_allowed(problem_id, {'allowed_languages'})
            relation = Problem.allowed_languages.through.objects.filter(problem_id=problem_id)
            if reverse:
                relation = relation.filter(language_id=instance.pk)
            elif pk_set is not None:
                relation = relation.filter(language_id__in=pk_set)
            changed = bool(pk_set) if action == 'pre_add' else relation.exists()
            if changed:
                instance._authoring_language_changes.append(problem_id)
    except AuthoringError as exc:
        raise ValidationError(exc.message) from exc


@receiver(m2m_changed, sender=Problem.allowed_languages.through)
def problem_authoring_languages_revision(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        from judge.problem_authoring.revisions import invalidate_revision
        for problem_id in getattr(instance, '_authoring_language_changes', []):
            invalidate_revision(problem_id, grading=True)
        instance._authoring_language_changes = []


@receiver(pre_delete, sender=LanguageLimit)
def authoring_language_limit_delete_guard(sender, instance, origin=None, **kwargs):
    if isinstance(origin, Problem):
        return
    list(Problem.objects.select_for_update().filter(pk=instance.problem_id))
    instance.clean()


@receiver(post_delete, sender=LanguageLimit)
def authoring_language_limit_delete_revision(sender, instance, origin=None, **kwargs):
    if isinstance(origin, Problem):
        return
    from judge.problem_authoring.revisions import invalidate_revision
    invalidate_revision(instance.problem_id, grading=True)


@receiver(pre_delete, sender=Solution)
def authoring_editorial_delete_lock(sender, instance, **kwargs):
    list(Problem.objects.select_for_update().filter(pk=instance.problem_id))


@receiver(post_delete, sender=Solution)
def authoring_editorial_delete_revision(sender, instance, **kwargs):
    from judge.problem_authoring.revisions import invalidate_revision
    invalidate_revision(instance.problem_id)


@receiver(m2m_changed, sender=Solution.authors.through)
def authoring_editorial_authors_revision(sender, instance, action, reverse, pk_set, **kwargs):
    from judge.problem_authoring.revisions import invalidate_revision
    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        if reverse:
            solutions = Solution.objects.filter(pk__in=pk_set) if pk_set is not None else instance.solution_set.all()
        else:
            solutions = Solution.objects.filter(pk=instance.pk)
        problem_ids = sorted(solutions.values_list('problem_id', flat=True))
        list(Problem.objects.select_for_update().filter(pk__in=problem_ids).order_by('pk'))
        relation = Solution.authors.through.objects.filter(solution_id__in=solutions.values('pk'))
        if reverse:
            relation = relation.filter(profile_id=instance.pk)
        elif pk_set is not None:
            relation = relation.filter(profile_id__in=pk_set)
        if action == 'pre_add':
            changed = problem_ids if pk_set else []
        else:
            changed = sorted(set(relation.values_list('solution__problem_id', flat=True)))
        instance._authoring_editorial_changes = changed
    elif action in ('post_add', 'post_remove', 'post_clear'):
        for problem_id in getattr(instance, '_authoring_editorial_changes', []):
            invalidate_revision(problem_id)
        instance._authoring_editorial_changes = []


@receiver(post_save, sender=Problem)
def problem_update(sender, instance, **kwargs):
    if hasattr(instance, '_updating_stats_only'):
        return

    cache.delete_many([
        make_template_fragment_key('submission_problem', (instance.id,)),
        make_template_fragment_key('problem_feed', (instance.id,)),
        'problem_tls:%s' % instance.id, 'problem_mls:%s' % instance.id,
    ])
    cache.delete_many([make_template_fragment_key('problem_html', (instance.id, engine, lang))
                       for lang, _ in settings.LANGUAGES for engine in EFFECTIVE_MATH_ENGINES])
    cache.delete_many([make_template_fragment_key('problem_authors', (instance.id, lang))
                       for lang, _ in settings.LANGUAGES])
    cache.delete_many(['generated-meta-problem:%s:%d' % (lang, instance.id) for lang, _ in settings.LANGUAGES])

    for lang, _ in settings.LANGUAGES:
        cached_pdf_filename = get_pdf_path('%s.%s.pdf' % (instance.code, lang))
        if cached_pdf_filename is not None:
            unlink_if_exists(cached_pdf_filename)


@receiver(post_save, sender=Profile)
def profile_update(sender, instance, **kwargs):
    if hasattr(instance, '_updating_stats_only'):
        return

    cache.delete_many([make_template_fragment_key('user_about', (instance.id, engine))
                       for engine in EFFECTIVE_MATH_ENGINES])


@receiver(post_delete, sender=WebAuthnCredential)
def webauthn_delete(sender, instance, **kwargs):
    profile = instance.user
    if profile.webauthn_credentials.count() == 0:
        profile.is_webauthn_enabled = False
        profile.save(update_fields=['is_webauthn_enabled'])


@receiver(post_save, sender=Contest)
def contest_update(sender, instance, **kwargs):
    if hasattr(instance, '_updating_stats_only'):
        return

    cache.delete_many(['generated-meta-contest:%d' % instance.id] +
                      [make_template_fragment_key('contest_html', (instance.id, engine))
                       for engine in EFFECTIVE_MATH_ENGINES])


@receiver(post_delete, sender=ContestProblem)
def contest_problem_delete(sender, instance, **kwargs):
    # `contest_object` is the `Contest` object indirectly associated with the `Submission` object
    # `contest` is the `ContestSubmission` object associated with the `Submission` object
    Submission.objects.filter(contest_object=instance.contest, contest__isnull=True).update(contest_object=None)


@receiver(post_delete, sender=Problem)
def problem_delete_r2_releases(sender, instance, **kwargs):
    if not getattr(settings, 'BRIDGED_R2_PROBLEMS', False):
        return
    code = instance.code
    # Defer until the deleting transaction actually commits, so a rolled-back
    # delete (e.g. fast_delete_problem failing midway) never purges a release
    # that is still in use.
    transaction.on_commit(lambda: _purge_problem_release(code))


def _purge_problem_release(code):  # pragma: no cover - thin wrapper, see judge.tasks.problem
    from judge.tasks.problem import purge_problem_release
    return purge_problem_release.delay(code)


@receiver(post_save, sender=License)
def license_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('license_html', (instance.id,)))


@receiver(post_save, sender=Language)
def language_update(sender, instance, **kwargs):
    cache.delete_many([make_template_fragment_key('language_html', (instance.id,)),
                       'lang:cn_map'])


@receiver(post_save, sender=Judge)
def judge_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('judge_html', (instance.id,)))


@receiver(post_save, sender=Comment)
def comment_update(sender, instance, created, **kwargs):
    cache.delete('comment_feed:%d' % instance.id)
    if not created:
        return
    on_new_comment.delay(instance.id)


@receiver(post_save, sender=BlogPost)
def post_update(sender, instance, **kwargs):
    cache.delete_many([
        make_template_fragment_key('post_summary', (instance.id,)),
        'blog_slug:%d' % instance.id,
        'blog_feed:%d' % instance.id,
    ])
    cache.delete_many([make_template_fragment_key('post_content', (instance.id, engine))
                       for engine in EFFECTIVE_MATH_ENGINES])


@receiver(post_delete, sender=Submission)
def submission_delete(sender, instance, **kwargs):
    finished_submission(instance)
    instance.user._updating_stats_only = True
    instance.user.calculate_points()
    instance.problem._updating_stats_only = True
    instance.problem.update_stats()


@receiver(post_delete, sender=ContestSubmission)
def contest_submission_delete(sender, instance, **kwargs):
    participation = instance.participation
    participation.recompute_results()
    Submission.objects.filter(id=instance.submission_id).update(contest_object=None)


@receiver(post_save, sender=Organization)
def organization_update(sender, instance, **kwargs):
    cache.delete_many([make_template_fragment_key('organization_html', (instance.id, engine))
                       for engine in EFFECTIVE_MATH_ENGINES])


@receiver(m2m_changed, sender=Organization.admins.through)
def organization_admin_update(sender, instance, action, **kwargs):
    if action == 'post_add':
        pks = kwargs.get('pk_set') or set()
        for profile in Profile.objects.filter(pk__in=pks):
            profile.organizations.add(instance)


@receiver(post_save, sender=MiscConfig)
def misc_config_update(sender, instance, **kwargs):
    cache.delete('misc_config')


@receiver(post_delete, sender=MiscConfig)
def misc_config_delete(sender, instance, **kwargs):
    cache.delete('misc_config')


@receiver(post_save, sender=ContestSubmission)
def contest_submission_update(sender, instance, **kwargs):
    Submission.objects.filter(id=instance.submission_id).update(contest_object_id=instance.participation.contest_id)


@receiver(post_save, sender=FlatPage)
def flatpage_update(sender, instance, **kwargs):
    cache.delete(make_template_fragment_key('flatpage', (instance.url, )))


@receiver(m2m_changed, sender=Profile.organizations.through)
def profile_organization_update(sender, instance, action, **kwargs):
    orgs_to_be_updated = []
    if action == 'pre_clear':
        orgs_to_be_updated = instance.organizations.get_queryset()
    if action == 'post_remove' or action == 'post_add':
        pks = kwargs.get('pk_set') or set()
        orgs_to_be_updated = Organization.objects.filter(pk__in=pks)
    for org in orgs_to_be_updated:
        org.on_user_changes()


@receiver(post_save, sender=ContestAnnouncement)
def contest_announcement_create(sender, instance, created, **kwargs):
    if not created:
        return

    instance.send()


@receiver(user_registered, sender=RegistrationView)
def registration_user_registered(sender, user, request, **kwargs):
    """Automatically activate user if SEND_ACTIVATION_EMAIL is False"""

    if not getattr(settings, 'SEND_ACTIVATION_EMAIL', True):
        # get should never fail here
        # but if it does, we won't catch it so it can show up in our log
        profile = RegistrationProfile.objects.get(user=user)

        user.is_active = True
        profile.activated = True

        with transaction.atomic():
            user.save()
            profile.save()

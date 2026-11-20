from celery import shared_task


@shared_task
def process_authoring_data(operation_id):
    from judge.problem_authoring.data import process_data_operation
    process_data_operation(operation_id)


@shared_task
def recover_authoring_operations():
    from judge.problem_authoring.data import reconcile_authoring
    from django.utils import timezone
    return reconcile_authoring(now=timezone.now())

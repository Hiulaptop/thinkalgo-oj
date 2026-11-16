from django.urls import path

from judge.views import problem_package

urlpatterns = [
    path('', problem_package.upload, name='problem_package_upload'),
    path('<uuid:pk>/', problem_package.detail, name='problem_package_detail'),
    path('<uuid:pk>/retry/', problem_package.retry, name='problem_package_retry'),
    path('<uuid:pk>/download/<str:kind>/', problem_package.download, name='problem_package_download'),
]

from django.urls import include, path

from judge.problem_authoring.views import AuthoringDownloadView, OrganizationProblemAuthoringCreateView, \
    ProblemAuthoringCreateView, ProblemAuthoringEditView

urlpatterns = [
    path('problems/authoring/uploads/<uuid:upload_id>', AuthoringDownloadView.as_view(),
         name='problem_authoring_download'),
    path('problems/create', ProblemAuthoringCreateView.as_view(), name='problem_create'),
    path('problem/<str:problem>/edit', ProblemAuthoringEditView.as_view(), name='problem_edit'),
    path('organization/<slug:slug>/problem-create', OrganizationProblemAuthoringCreateView.as_view(),
         name='problem_create_organization'),
    path('', include('dmoj.urls')),
]

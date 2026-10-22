from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from judge.api.v1.views import me, problems

app_name = 'api_v1'

urlpatterns = [
    path('me', me.MeView.as_view(), name='me'),
    path('problems', problems.ProblemListView.as_view(), name='problem_list'),
    path('problem-filters', problems.ProblemFiltersView.as_view(), name='problem_filters'),
    path('problems/<str:code>', problems.ProblemDetailView.as_view(), name='problem_detail'),
    path('schema', SpectacularAPIView.as_view(), name='schema'),
]

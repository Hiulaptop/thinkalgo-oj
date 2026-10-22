from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from judge.api.v1.views import blog, me, problems, submissions, users

app_name = 'api_v1'

urlpatterns = [
    path('me', me.MeView.as_view(), name='me'),
    path('problems', problems.ProblemListView.as_view(), name='problem_list'),
    path('problem-filters', problems.ProblemFiltersView.as_view(), name='problem_filters'),
    path('problems/<str:code>', problems.ProblemDetailView.as_view(), name='problem_detail'),
    path('submissions', submissions.SubmissionListView.as_view(), name='submission_list'),
    path('submissions/<int:pk>', submissions.SubmissionDetailView.as_view(), name='submission_detail'),
    path('submissions/<int:pk>/source', submissions.SubmissionSourceView.as_view(), name='submission_source'),
    path('users', users.UserRankingView.as_view(), name='user_ranking'),
    path('blog/posts', blog.BlogPostListView.as_view(), name='blog_post_list'),
    path('blog/posts/<int:pk>', blog.BlogPostDetailView.as_view(), name='blog_post_detail'),
    path('schema', SpectacularAPIView.as_view(), name='schema'),
]

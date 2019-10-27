from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
#    path('', views.IndexView.as_view(), name='index'),
    path('create/', views.ProjectCreate.as_view(), name='create'),
    path('<int:pk>/update', views.ProjectUpdate.as_view(), name='update'),
    path('<int:pk>/delete', views.ProjectDelete.as_view(), name='delete'),
    path('<int:pk>/', views.Details.as_view(), name='details'),
#    path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),
#    path('<int:question_id>/vote/', views.vote, name='vote'),
]

from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
#    path('', views.IndexView.as_view(), name='index'),
    path('create/', views.ProjectCreate.as_view(), name='create'),
    path('<int:pk>/update', views.ProjectUpdate.as_view(), name='update'),
    path('<int:pk>/delete', views.ProjectDelete.as_view(), name='delete'),
    path('<int:pk>/', views.Details.as_view(), name='details'),
    path('legal/create/', views.LegalEntityCreate.as_view(), name='legal_create'),
    path('legal/<int:pk>', views.LegalEntityDetails.as_view(), name='legal_details'),
    path('legal/<int:pk>/update/', views.LegalEntityUpdate.as_view(), name='legal_update'),
    path('legal/<int:pk>/delete', views.LegalEntityDelete.as_view(), name='legal_delete'),
    path('legal/', views.LegalEntityList.as_view(), name='legal_list'),
    path('legal/<int:pk>/join', views.legal_join, name='legal_join'),
    path('legal/<int:pk>/exit', views.legal_exit, name='legal_exit'),
]

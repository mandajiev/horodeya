from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
#    path('', views.IndexView.as_view(), name='index'),
    path('create/<str:type>', views.ProjectCreate.as_view(), name='create'),
    path('<int:pk>/update', views.ProjectUpdate.as_view(), name='update'),
    path('<int:pk>/delete', views.ProjectDelete.as_view(), name='delete'),
    path('<int:pk>/', views.ProjectDetails.as_view(), name='details'),
    path('legal/create/', views.LegalEntityCreate.as_view(), name='legal_create'),
    path('legal/<int:pk>', views.LegalEntityDetails.as_view(), name='legal_details'),
    path('legal/<int:pk>/update', views.LegalEntityUpdate.as_view(), name='legal_update'),
    path('legal/<int:pk>/delete', views.LegalEntityDelete.as_view(), name='legal_delete'),
    path('legal/', views.LegalEntityList.as_view(), name='legal_list'),
    path('legal/<int:pk>/join', views.legal_join, name='legal_join'),
    path('legal/<int:pk>/exit', views.legal_exit, name='legal_exit'),
    path('<int:project>/report/create/', views.ReportCreate.as_view(), name='report_create'),
    path('report/<int:pk>', views.ReportDetails.as_view(), name='report_details'),
    path('report/<int:pk>/update', views.ReportUpdate.as_view(), name='report_update'),
    path('report/<int:pk>/delete', views.ReportDelete.as_view(), name='report_delete'),
    path('<int:project>/report/list', views.ReportList.as_view(), name='report_list'),
    path('report/<int:pk>/vote-up', views.report_vote_up, name='report_vote_up'),
    path('report/<int:pk>/vote-down', views.report_vote_down, name='report_vote_down'),

    path('<int:project_id>/support/create/', views.support_create, name='support_create'),
    path('<int:project>/msupport/create/', views.MoneySupportCreate.as_view(), name='msupport_create'),
    path('support/<int:pk>', views.support_details, name='support_details'),
    path('msupport/<int:pk>', views.MoneySupportDetails.as_view(), name='msupport_details'),
    path('msupport/<int:pk>/update', views.MoneySupportUpdate.as_view(), name='msupport_update'),
    path('<int:project>/tsupport/create/', views.TimeSupportCreate.as_view(), name='tsupport_create'),
    path('tsupport/<int:pk>', views.TimeSupportDetails.as_view(), name='tsupport_details'),
    path('tsupport/<int:pk>/update', views.TimeSupportUpdate.as_view(), name='tsupport_update'),

    path('support/<int:pk>/<str:type>/delete', views.SupportDelete.as_view(), name='support_delete'),
    path('support/<int:pk>/<str:type>/accept', views.support_accept, name='support_accept'),
    path('support/<int:pk>/<str:type>/decline', views.support_decline, name='support_decline'),
    path('support/<int:pk>/<str:type>/delivered', views.support_delivered, name='support_delivered'),
    path('<int:project_id>/support/list', views.support_list, name='support_list'),
]

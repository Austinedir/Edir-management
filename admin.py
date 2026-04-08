from django.urls import path
from apps.events import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('new/', views.event_create, name='create'),
    path('<uuid:pk>/', views.event_detail, name='detail'),
    path('<uuid:pk>/verify/', views.event_verify, name='verify'),
    path('<uuid:pk>/approve/', views.event_approve, name='approve'),
    path('<uuid:event_pk>/disburse/', views.payout_disburse, name='disburse'),
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('meetings/new/', views.meeting_create, name='meeting_create'),
]

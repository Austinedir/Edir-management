from django.urls import path
from apps.members.views import dashboard as views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('reports/', views.reports, name='reports'),
]

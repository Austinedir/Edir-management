from django.urls import path
from apps.contributions import views

app_name = 'contributions'

urlpatterns = [
    path('', views.period_list, name='period_list'),
    path('new/', views.period_create, name='period_create'),
    path('<int:pk>/', views.period_detail, name='period_detail'),
    path('pay/<uuid:contribution_pk>/', views.mark_paid, name='mark_paid'),
    path('levies/', views.levy_list, name='levy_list'),
    path('levies/new/', views.levy_create, name='levy_create'),
]

from django.urls import path
from apps.members.views import members as views

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='list'),
    path('add/', views.member_create, name='create'),
    path('<uuid:pk>/', views.member_detail, name='detail'),
    path('<uuid:pk>/edit/', views.member_edit, name='edit'),
    path('<uuid:pk>/card/', views.member_card, name='card'),
    path('<uuid:member_pk>/beneficiary/add/', views.beneficiary_create, name='beneficiary_create'),
]

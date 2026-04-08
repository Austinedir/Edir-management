from django.urls import path
from apps.members.views import portal as views
from django.views.generic import TemplateView

app_name = 'portal'

urlpatterns = [
    # FR 1.2 – Public registration
    path('apply/', views.register_online, name='apply'),
    path('apply/success/<uuid:pk>/', views.registration_success, name='registration_success'),
    path('contact/', views.contact_form, name='contact'),
    path('contact/thanks/', TemplateView.as_view(template_name='portal/contact_success.html'), name='contact_success'),

    # FR 1.1 – Member portal
    path('portal/', views.member_portal, name='member_portal'),
    path('portal/payments/', views.my_payment_status, name='my_payment_status'),
    path('portal/messages/', views.my_messages, name='my_messages'),
    path('portal/messages/send/', views.send_message, name='send_message'),
    path('portal/messages/<uuid:pk>/', views.read_message, name='read_message'),
    path('portal/documents/', views.documents_archive, name='documents_archive'),

    # FR 2 – Admin portal
    path('admin-portal/applications/', views.application_list, name='application_list'),
    path('admin-portal/applications/<uuid:pk>/', views.application_detail, name='application_detail'),
    path('admin-portal/applications/<uuid:pk>/approve/', views.application_approve, name='application_approve'),
    path('admin-portal/applications/<uuid:pk>/deny/', views.application_deny, name='application_deny'),
    path('admin-portal/messages/', views.admin_messages_inbox, name='admin_inbox'),
    path('admin-portal/messages/<uuid:pk>/reply/', views.reply_message, name='reply_message'),
    path('admin-portal/mass-messages/', views.mass_message_list, name='mass_message_list'),
    path('admin-portal/mass-messages/new/', views.mass_message_create, name='mass_message_create'),
    path('admin-portal/documents/upload/', views.upload_document, name='upload_document'),
]

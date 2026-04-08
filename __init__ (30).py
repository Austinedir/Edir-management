"""
Views for:
- Online member registration (FR 1.2)
- Member portal: payment status, messaging, documents (FR 1.1)
- Admin: application review, approval/denial (FR 2.4)
- Mass messaging (FR 3)
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from apps.members.models import Member, EdirGroup, User, MemberApplication, Message, Document, MassMessage
from apps.contributions.models import Contribution, ContributionPeriod
from apps.members.registration_forms import (
    OnlineRegistrationForm, ApplicationReviewForm, MassMessageForm, DocumentUploadForm
)


def is_admin(user):
    return user.is_staff or user.is_superuser


# ──────────────────────────────────────────────────────────────────
# FR 1.2 – Online Registration (public)
# ──────────────────────────────────────────────────────────────────
def register_online(request):
    """Public registration form for prospective members."""
    edir = EdirGroup.objects.filter(is_active=True).first()
    if not edir:
        return render(request, 'registration/closed.html')

    if request.method == 'POST':
        form = OnlineRegistrationForm(request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.edir = edir
            app.save()

            # FR 1.2.4 – Email registrant with pending status
            if app.email:
                try:
                    send_mail(
                        subject=f'[{edir.name}] Application Received – Pending Review',
                        message=(
                            f'Dear {app.first_name},\n\n'
                            f'Thank you for applying to join {edir.name}.\n\n'
                            f'Your application has been received and is pending review by our administrators.\n'
                            f'We will notify you once a decision has been made.\n\n'
                            f'Application Reference: {str(app.id)[:8].upper()}\n\n'
                            f'If you have questions, please contact us at {settings.DEFAULT_FROM_EMAIL}.\n\n'
                            f'Thank you,\n{edir.name}'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[app.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

            # Notify admins
            admin_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
            if admin_emails:
                send_mail(
                    subject=f'[{edir.name}] New Membership Application – {app.full_name}',
                    message=f'A new membership application has been submitted by {app.full_name} ({app.email}).\n\nPlease review at your admin portal.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
                )

            return redirect('portal:registration_success', pk=app.pk)
    else:
        form = OnlineRegistrationForm()

    return render(request, 'registration/apply.html', {'form': form, 'edir': edir})


def registration_success(request, pk):
    app = get_object_or_404(MemberApplication, pk=pk)
    return render(request, 'registration/success.html', {'app': app})


# ──────────────────────────────────────────────────────────────────
# FR 1.1 – Member Portal
# ──────────────────────────────────────────────────────────────────
@login_required
def member_portal(request):
    """Member's own dashboard – payment status, info."""
    try:
        member = request.user.member_profile
    except Exception:
        return render(request, 'portal/no_profile.html')

    # FR 1.1.5 – Payment status
    contributions = member.contributions.select_related('period').order_by('-period__year', '-period__month')
    total_paid = contributions.filter(status='paid').aggregate(t=Sum('amount'))['t'] or 0
    pending = contributions.filter(status='pending').count()

    # FR 1.1.6 – Messages
    inbox = Message.objects.filter(recipient=request.user, archived=False).order_by('-created_at')[:5]
    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()

    # Documents
    edir = member.edir
    documents = Document.objects.filter(edir=edir, is_public=True).order_by('-created_at')[:5]

    context = {
        'member': member,
        'contributions': contributions[:12],
        'total_paid': total_paid,
        'pending_count': pending,
        'inbox': inbox,
        'unread_count': unread_count,
        'documents': documents,
    }
    return render(request, 'portal/member_home.html', context)


@login_required
def my_payment_status(request):
    """FR 1.1.5 – Detailed payment status."""
    try:
        member = request.user.member_profile
    except Exception:
        return redirect('portal:member_portal')

    contributions = member.contributions.select_related('period').order_by('-period__year', '-period__month')
    total_paid = contributions.filter(status='paid').aggregate(t=Sum('amount'))['t'] or 0
    total_overdue = contributions.filter(status='pending').aggregate(t=Sum('amount'))['t'] or 0

    return render(request, 'portal/payment_status.html', {
        'member': member,
        'contributions': contributions,
        'total_paid': total_paid,
        'total_overdue': total_overdue,
    })


@login_required
def my_messages(request):
    """FR 1.1.6 – Send/receive/document messages."""
    inbox = Message.objects.filter(recipient=request.user, archived=False).order_by('-created_at')
    return render(request, 'portal/messages.html', {'inbox': inbox})


@login_required
def send_message(request):
    """FR 1.1.6 – Send a message to admin."""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        if subject and body:
            # Send to all staff
            for admin in User.objects.filter(is_staff=True):
                Message.objects.create(
                    sender=request.user,
                    recipient=admin,
                    subject=subject,
                    body=body,
                    message_type='inbox',
                )
            messages.success(request, 'Your message has been sent to the administrators.')
            return redirect('portal:my_messages')
    return render(request, 'portal/send_message.html')


@login_required
def read_message(request, pk):
    msg = get_object_or_404(Message, pk=pk, recipient=request.user)
    msg.mark_read()
    return render(request, 'portal/message_detail.html', {'msg': msg})


@login_required
def documents_archive(request):
    """FR 1.1.7 – View archived documents."""
    try:
        member = request.user.member_profile
        edir = member.edir
    except Exception:
        edir = EdirGroup.objects.filter(is_active=True).first()

    category = request.GET.get('category', '')
    docs = Document.objects.filter(is_public=True)
    if edir:
        docs = docs.filter(edir=edir)
    if category:
        docs = docs.filter(category=category)
    docs = docs.order_by('-created_at')

    return render(request, 'portal/documents.html', {
        'documents': docs,
        'category_choices': Document.Category.choices,
        'category': category,
    })


# ──────────────────────────────────────────────────────────────────
# FR 2.4 – Admin: Application Review
# ──────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def application_list(request):
    """FR 2.4.1 – Admin reviews applications."""
    apps = MemberApplication.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        apps = apps.filter(status=status_filter)
    paginator = Paginator(apps, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_portal/applications.html', {
        'page_obj': page,
        'status_choices': MemberApplication.Status.choices,
        'status_filter': status_filter,
        'pending_count': MemberApplication.objects.filter(status='pending').count(),
    })


@login_required
@user_passes_test(is_admin)
def application_detail(request, pk):
    app = get_object_or_404(MemberApplication, pk=pk)
    return render(request, 'admin_portal/application_detail.html', {'app': app})


@login_required
@user_passes_test(is_admin)
def application_approve(request, pk):
    """FR 2.4.1 + 2.4.4 – Approve and auto-email."""
    app = get_object_or_404(MemberApplication, pk=pk, status='pending')

    if request.method == 'POST':
        edir = app.edir
        # Create the Member
        member = Member.objects.create(
            edir=edir,
            first_name=app.first_name,
            last_name=app.last_name,
            gender=app.gender,
            date_of_birth=app.date_of_birth,
            phone=app.phone[:20],
            email=app.email,
            address=app.address,
            city=app.city,
            zip_code=app.zip_code,
            status=Member.Status.ACTIVE,
            join_date=timezone.now().date(),
            emergency_contact_name=app.rep_name,
            emergency_contact_phone=app.rep_phone,
        )

        app.status = MemberApplication.Status.APPROVED
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.approval_notes = request.POST.get('notes', '')
        app.converted_member = member
        app.save()

        # FR 2.4.4 – Auto-email approval
        if app.email:
            send_mail(
                subject=f'[{edir.name}] Membership Application Approved! Welcome!',
                message=(
                    f'Dear {app.first_name},\n\n'
                    f'Congratulations! Your application to join {edir.name} has been APPROVED.\n\n'
                    f'Your member number is: {member.member_number}\n\n'
                    f'Please contact us for next steps regarding your registration fee payment.\n\n'
                    f'Welcome to our edir!\n\n{edir.name}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[app.email],
                fail_silently=True,
            )

        messages.success(request, f'Application approved. Member {member.member_number} created.')
        return redirect('portal:application_list')

    return render(request, 'admin_portal/application_approve.html', {'app': app})


@login_required
@user_passes_test(is_admin)
def application_deny(request, pk):
    """FR 2.4.2 + 2.4.4 – Deny and auto-email."""
    app = get_object_or_404(MemberApplication, pk=pk, status='pending')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        app.status = MemberApplication.Status.DENIED
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.denial_reason = reason
        app.save()

        # FR 2.4.4 – Auto-email denial
        if app.email:
            send_mail(
                subject=f'[{app.edir.name}] Membership Application Update',
                message=(
                    f'Dear {app.first_name},\n\n'
                    f'We regret to inform you that your membership application to {app.edir.name} '
                    f'has not been approved at this time.\n\n'
                    f'Reason: {reason or "Does not meet current membership requirements."}\n\n'
                    f'If you have questions, please contact us.\n\n{app.edir.name}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[app.email],
                fail_silently=True,
            )

        messages.warning(request, 'Application denied. Applicant has been notified.')
        return redirect('portal:application_list')

    return render(request, 'admin_portal/application_deny.html', {'app': app})


# ──────────────────────────────────────────────────────────────────
# FR 3 – Mass Messaging
# ──────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def mass_message_list(request):
    msgs = MassMessage.objects.all().order_by('-created_at')
    return render(request, 'admin_portal/mass_messages.html', {'messages_list': msgs})


@login_required
@user_passes_test(is_admin)
def mass_message_create(request):
    """FR 3.1/3.2 – Admin sends mass email or SMS."""
    edir = get_object_or_404(EdirGroup, is_active=True)

    if request.method == 'POST':
        form = MassMessageForm(request.POST)
        if form.is_valid():
            mm = form.save(commit=False)
            mm.edir = edir
            mm.sent_by = request.user
            mm.save()

            # Build recipient list
            qs = Member.objects.filter(edir=edir)
            if mm.target_active_only:
                qs = qs.filter(status=Member.Status.ACTIVE)
            if mm.target_city:
                qs = qs.filter(city__iexact=mm.target_city)

            emails = [m.email for m in qs if m.email]
            mm.recipients_count = len(emails)
            mm.status = MassMessage.Status.SENDING
            mm.save()

            # Send emails (FR 3.1)
            if mm.channel in ('email', 'both') and emails:
                from apps.notifications.tasks import send_mass_message_task
                send_mass_message_task.delay(str(mm.pk))

            messages.success(request, f'Mass message queued for {len(emails)} recipients.')
            return redirect('portal:mass_message_list')
    else:
        form = MassMessageForm()

    # Contact count preview (FR 4.1)
    active_count = Member.objects.filter(edir=edir, status=Member.Status.ACTIVE).exclude(email='').count()
    return render(request, 'admin_portal/mass_message_form.html', {
        'form': form,
        'active_count': active_count,
    })


# ──────────────────────────────────────────────────────────────────
# FR 2.1.1 + 2.3 – Financial Reports & Document Upload
# ──────────────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def upload_document(request):
    """FR 2.1.1 – Upload bank statement / financial documents."""
    edir = get_object_or_404(EdirGroup, is_active=True)
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.edir = edir
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, f'Document "{doc.title}" uploaded successfully.')
            return redirect('portal:documents_archive')
    else:
        form = DocumentUploadForm()
    return render(request, 'admin_portal/upload_document.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def admin_messages_inbox(request):
    """Admin inbox – view messages from members."""
    inbox = Message.objects.filter(
        recipient=request.user, archived=False
    ).order_by('-created_at')
    return render(request, 'admin_portal/inbox.html', {'inbox': inbox})


@login_required
@user_passes_test(is_admin)
def reply_message(request, pk):
    original = get_object_or_404(Message, pk=pk)
    original.mark_read()
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body and original.sender:
            Message.objects.create(
                sender=request.user,
                recipient=original.sender,
                subject=f'Re: {original.subject}',
                body=body,
                message_type='inbox',
                related_application=original.related_application,
            )
            messages.success(request, 'Reply sent.')
            return redirect('portal:admin_inbox')
    return render(request, 'admin_portal/reply_message.html', {'original': original})


# FR 4.4 – Member contact / inquiry form (public)
def contact_form(request):
    edir = EdirGroup.objects.filter(is_active=True).first()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        question = request.POST.get('question', '').strip()
        if name and email and question:
            # Send to edir email + acknowledge sender
            admin_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
            if admin_emails:
                send_mail(
                    subject=f'[{edir.name if edir else "EDIR"}] Question from {name}',
                    message=f'Name: {name}\nEmail: {email}\n\nQuestion:\n{question}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
                )
            send_mail(
                subject=f'[{edir.name if edir else "EDIR"}] We received your question',
                message=f'Dear {name},\n\nThank you for contacting us. We have received your question and will respond shortly.\n\nYour question:\n{question}\n\nWarm regards,\n{edir.name if edir else "EDIR"}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
            messages.success(request, 'Your question has been sent. We will respond to your email.')
            return redirect('portal:contact_success')
    return render(request, 'portal/contact.html', {'edir': edir})

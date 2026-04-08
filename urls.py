from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from apps.members.models import EdirGroup
from apps.events.models import EdirEvent, Payout, MeetingMinute
from apps.events.forms import EdirEventForm, PayoutForm, MeetingMinuteForm


@login_required
def event_list(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    events = EdirEvent.objects.filter(edir=edir).select_related('member')

    event_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    if event_type:
        events = events.filter(event_type=event_type)
    if status:
        events = events.filter(status=status)

    context = {
        'events': events,
        'edir': edir,
        'event_type_choices': EdirEvent.EventType.choices,
        'status_choices': EdirEvent.Status.choices,
        'type_filter': event_type,
        'status_filter': status,
    }
    return render(request, 'events/list.html', context)


@login_required
def event_detail(request, pk):
    event = get_object_or_404(EdirEvent, pk=pk)
    payout = getattr(event, 'payout', None)
    context = {
        'event': event,
        'payout': payout,
        'payout_amount': event.get_payout_amount(),
    }
    return render(request, 'events/detail.html', context)


@login_required
def event_create(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    if request.method == 'POST':
        form = EdirEventForm(request.POST, request.FILES, edir=edir)
        if form.is_valid():
            event = form.save(commit=False)
            event.edir = edir
            event.reported_by = request.user
            event.save()
            messages.success(request, 'Event reported successfully. Pending verification.')
            return redirect('events:detail', pk=event.pk)
    else:
        form = EdirEventForm(edir=edir)
    return render(request, 'events/form.html', {'form': form, 'action': 'Report Event'})


@login_required
def event_verify(request, pk):
    event = get_object_or_404(EdirEvent, pk=pk, status=EdirEvent.Status.REPORTED)
    event.status = EdirEvent.Status.VERIFIED
    event.verified_by = request.user
    event.verified_at = timezone.now()
    event.save()
    messages.success(request, 'Event verified.')
    return redirect('events:detail', pk=event.pk)


@login_required
def event_approve(request, pk):
    event = get_object_or_404(EdirEvent, pk=pk, status=EdirEvent.Status.VERIFIED)
    event.status = EdirEvent.Status.APPROVED
    event.approved_by = request.user
    event.approved_at = timezone.now()
    event.save()

    # Auto-create payout record
    payout_amount = event.get_payout_amount()
    if payout_amount > 0:
        Payout.objects.get_or_create(
            event=event,
            defaults={
                'amount': payout_amount,
                'recipient_name': event.member.full_name,
                'recipient_phone': str(event.member.phone),
            }
        )
        event.status = EdirEvent.Status.PAYOUT_PENDING
        event.save()

    messages.success(request, 'Event approved. Payout record created.')
    return redirect('events:detail', pk=event.pk)


@login_required
def payout_disburse(request, event_pk):
    event = get_object_or_404(EdirEvent, pk=event_pk)
    payout = get_object_or_404(Payout, event=event)
    if request.method == 'POST':
        form = PayoutForm(request.POST, instance=payout)
        if form.is_valid():
            p = form.save(commit=False)
            p.status = Payout.Status.DISBURSED
            p.disbursed_by = request.user
            p.disbursed_at = timezone.now()
            p.save()
            event.status = EdirEvent.Status.CLOSED
            event.save()
            messages.success(request, f'Payout of {p.amount} ETB disbursed successfully.')
            return redirect('events:detail', pk=event.pk)
    else:
        form = PayoutForm(instance=payout)
    return render(request, 'events/payout_form.html', {'form': form, 'event': event, 'payout': payout})


@login_required
def meeting_list(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    meetings = MeetingMinute.objects.filter(edir=edir).order_by('-date')
    return render(request, 'events/meeting_list.html', {'meetings': meetings, 'edir': edir})


@login_required
def meeting_create(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    if request.method == 'POST':
        form = MeetingMinuteForm(request.POST, request.FILES, edir=edir)
        if form.is_valid():
            m = form.save(commit=False)
            m.edir = edir
            m.recorded_by = request.user
            m.save()
            form.save_m2m()
            messages.success(request, 'Meeting recorded.')
            return redirect('events:meeting_list')
    else:
        form = MeetingMinuteForm(edir=edir)
    return render(request, 'events/meeting_form.html', {'form': form})

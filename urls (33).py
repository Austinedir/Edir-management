from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib import messages
from apps.members.models import Member, EdirGroup
from apps.contributions.models import Contribution, ContributionPeriod
from apps.events.models import EdirEvent, Payout
from apps.notifications.models import Notification, Announcement
import datetime


@login_required
def dashboard(request):
    """Main dashboard – overview of edir health."""
    # Get the default edir (first one; extend for multi-edir)
    edir = EdirGroup.objects.filter(is_active=True).first()
    if not edir:
        return render(request, 'dashboard/setup_required.html')

    now = timezone.now()
    current_month = now.month
    current_year = now.year

    # Member stats
    total_members = Member.objects.filter(edir=edir, status=Member.Status.ACTIVE).count()
    new_this_month = Member.objects.filter(
        edir=edir, join_date__year=current_year, join_date__month=current_month
    ).count()

    # Current period
    try:
        current_period = ContributionPeriod.objects.get(
            edir=edir, year=current_year, month=current_month
        )
        paid_count = current_period.contributions.filter(status=Contribution.Status.PAID).count()
        pending_count = current_period.contributions.filter(status=Contribution.Status.PENDING).count()
        total_collected = current_period.contributions.filter(
            status=Contribution.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or 0
        collection_rate = (paid_count / total_members * 100) if total_members else 0
    except ContributionPeriod.DoesNotExist:
        current_period = None
        paid_count = pending_count = 0
        total_collected = 0
        collection_rate = 0

    # Events
    open_events = EdirEvent.objects.filter(
        edir=edir
    ).exclude(status__in=[EdirEvent.Status.CLOSED, EdirEvent.Status.REJECTED]).count()
    recent_events = EdirEvent.objects.filter(edir=edir).order_by('-created_at')[:5]

    # Payouts this year
    total_payouts = Payout.objects.filter(
        event__edir=edir,
        status=Payout.Status.DISBURSED,
        disbursed_at__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Notifications for current user
    user_notifications = Notification.objects.filter(
        Q(member__user=request.user) | Q(member__isnull=True),
        is_read=False
    ).order_by('-created_at')[:5]

    # Announcements
    announcements = Announcement.objects.filter(edir=edir, is_published=True).order_by('-published_at')[:3]

    # Monthly chart data (last 6 months)
    chart_data = []
    for i in range(5, -1, -1):
        d = now - datetime.timedelta(days=30 * i)
        month_collected = Contribution.objects.filter(
            period__edir=edir,
            period__year=d.year,
            period__month=d.month,
            status=Contribution.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or 0
        import calendar
        chart_data.append({
            'month': calendar.month_abbr[d.month],
            'amount': float(month_collected)
        })

    context = {
        'edir': edir,
        'total_members': total_members,
        'new_this_month': new_this_month,
        'current_period': current_period,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'total_collected': total_collected,
        'collection_rate': round(collection_rate, 1),
        'open_events': open_events,
        'recent_events': recent_events,
        'total_payouts': total_payouts,
        'user_notifications': user_notifications,
        'announcements': announcements,
        'chart_data': chart_data,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def reports(request):
    """Reports & analytics page."""
    edir = get_object_or_404(EdirGroup, is_active=True)
    now = timezone.now()

    # Annual summary
    annual_collected = Contribution.objects.filter(
        period__edir=edir, period__year=now.year, status=Contribution.Status.PAID
    ).aggregate(total=Sum('amount'))['total'] or 0

    annual_payouts = Payout.objects.filter(
        event__edir=edir, status=Payout.Status.DISBURSED, disbursed_at__year=now.year
    ).aggregate(total=Sum('amount'))['total'] or 0

    defaulters = Member.objects.filter(edir=edir, status=Member.Status.ACTIVE).annotate(
        unpaid=Count('contributions', filter=Q(contributions__status=Contribution.Status.PENDING))
    ).filter(unpaid__gt=2).order_by('-unpaid')

    context = {
        'edir': edir,
        'annual_collected': annual_collected,
        'annual_payouts': annual_payouts,
        'net_balance': annual_collected - annual_payouts,
        'defaulters': defaulters,
    }
    return render(request, 'dashboard/reports.html', context)

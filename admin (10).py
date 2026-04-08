from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.members.models import Member, EdirGroup
from apps.contributions.models import Contribution, ContributionPeriod, SpecialLevy, LevyPayment
from apps.contributions.forms import ContributionPeriodForm, MarkPaidForm, SpecialLevyForm


@login_required
def period_list(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    periods = ContributionPeriod.objects.filter(edir=edir).annotate(
        paid_count=Count('contributions', filter=Q(contributions__status=Contribution.Status.PAID)),
        total_collected=Sum('contributions__amount', filter=Q(contributions__status=Contribution.Status.PAID)),
    )
    return render(request, 'contributions/period_list.html', {'periods': periods, 'edir': edir})


@login_required
def period_detail(request, pk):
    period = get_object_or_404(ContributionPeriod, pk=pk)
    contributions = period.contributions.select_related('member').order_by('member__member_number')

    status_filter = request.GET.get('status', '')
    if status_filter:
        contributions = contributions.filter(status=status_filter)

    stats = {
        'paid': period.contributions.filter(status=Contribution.Status.PAID).count(),
        'pending': period.contributions.filter(status=Contribution.Status.PENDING).count(),
        'waived': period.contributions.filter(status=Contribution.Status.WAIVED).count(),
        'total_collected': period.contributions.filter(
            status=Contribution.Status.PAID
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
    }

    context = {
        'period': period,
        'contributions': contributions,
        'stats': stats,
        'status_choices': Contribution.Status.choices,
        'status_filter': status_filter,
    }
    return render(request, 'contributions/period_detail.html', context)


@login_required
def period_create(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    if request.method == 'POST':
        form = ContributionPeriodForm(request.POST)
        if form.is_valid():
            period = form.save(commit=False)
            period.edir = edir
            period.save()
            # Auto-create contribution records for all active members
            active_members = Member.objects.filter(edir=edir, status=Member.Status.ACTIVE)
            Contribution.objects.bulk_create([
                Contribution(period=period, member=m, amount=period.amount)
                for m in active_members
            ], ignore_conflicts=True)
            messages.success(request, f'Period {period} created with {active_members.count()} contribution records.')
            return redirect('contributions:period_detail', pk=period.pk)
    else:
        now = timezone.now()
        form = ContributionPeriodForm(initial={
            'year': now.year, 'month': now.month,
            'amount': edir.monthly_contribution
        })
    return render(request, 'contributions/period_form.html', {'form': form})


@login_required
def mark_paid(request, contribution_pk):
    contribution = get_object_or_404(Contribution, pk=contribution_pk)
    if request.method == 'POST':
        form = MarkPaidForm(request.POST)
        if form.is_valid():
            contribution.mark_paid(
                method=form.cleaned_data['payment_method'],
                collected_by=request.user,
                receipt=form.cleaned_data.get('receipt_number'),
            )
            messages.success(request, f'{contribution.member.full_name} marked as paid.')
            return redirect('contributions:period_detail', pk=contribution.period.pk)
    else:
        form = MarkPaidForm()
    return render(request, 'contributions/mark_paid.html', {'form': form, 'contribution': contribution})


@login_required
def levy_list(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    levies = SpecialLevy.objects.filter(edir=edir).order_by('-created_at')
    return render(request, 'contributions/levy_list.html', {'levies': levies, 'edir': edir})


@login_required
def levy_create(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    if request.method == 'POST':
        form = SpecialLevyForm(request.POST, edir=edir)
        if form.is_valid():
            levy = form.save(commit=False)
            levy.edir = edir
            levy.save()
            # Create payment records for all active members
            active_members = Member.objects.filter(edir=edir, status=Member.Status.ACTIVE)
            LevyPayment.objects.bulk_create([
                LevyPayment(levy=levy, member=m, amount=levy.amount_per_member)
                for m in active_members
            ])
            messages.success(request, f'Levy "{levy.title}" created.')
            return redirect('contributions:levy_list')
    else:
        form = SpecialLevyForm(edir=edir)
    return render(request, 'contributions/levy_form.html', {'form': form})

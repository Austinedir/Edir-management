from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from apps.members.models import Member, EdirGroup, Beneficiary
from apps.members.forms import MemberForm, BeneficiaryForm
from apps.contributions.models import Contribution


@login_required
def member_list(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    qs = Member.objects.filter(edir=edir).select_related('user')

    q = request.GET.get('q', '')
    status = request.GET.get('status', '')

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(member_number__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'edir': edir,
        'q': q,
        'status': status,
        'status_choices': Member.Status.choices,
        'total_count': qs.count(),
    }
    return render(request, 'members/list.html', context)


@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    contributions = member.contributions.select_related('period').order_by('-period__year', '-period__month')
    events = member.events.order_by('-event_date')
    beneficiaries = member.beneficiaries.all()
    arrears = member.get_arrears()

    context = {
        'member': member,
        'contributions': contributions[:12],
        'events': events,
        'beneficiaries': beneficiaries,
        'arrears': arrears,
    }
    return render(request, 'members/detail.html', context)


@login_required
def member_create(request):
    edir = get_object_or_404(EdirGroup, is_active=True)
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)
            member.edir = edir
            member.save()
            messages.success(request, f'Member {member.full_name} added successfully.')
            return redirect('members:detail', pk=member.pk)
    else:
        form = MemberForm()
    return render(request, 'members/form.html', {'form': form, 'action': 'Add Member'})


@login_required
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member updated successfully.')
            return redirect('members:detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    return render(request, 'members/form.html', {'form': form, 'member': member, 'action': 'Edit Member'})


@login_required
def beneficiary_create(request, member_pk):
    member = get_object_or_404(Member, pk=member_pk)
    if request.method == 'POST':
        form = BeneficiaryForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.member = member
            b.save()
            messages.success(request, 'Beneficiary added.')
            return redirect('members:detail', pk=member.pk)
    else:
        form = BeneficiaryForm()
    return render(request, 'members/beneficiary_form.html', {'form': form, 'member': member})


@login_required
def member_card(request, pk):
    """Printable member ID card."""
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'members/card.html', {'member': member})

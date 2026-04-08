from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import EdirEvent, Payout, MeetingMinute


class EdirEventForm(forms.ModelForm):
    class Meta:
        model = EdirEvent
        fields = [
            'member', 'event_type', 'event_date', 'deceased_name',
            'description', 'funeral_location', 'funeral_date',
            'death_certificate', 'supporting_document',
        ]
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date'}),
            'funeral_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, edir=None, **kwargs):
        super().__init__(*args, **kwargs)
        if edir:
            from apps.members.models import Member
            self.fields['member'].queryset = Member.objects.filter(edir=edir, status='active')
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('member', css_class='col-md-6'), Column('event_type', css_class='col-md-6')),
            Row(Column('event_date', css_class='col-md-4'), Column('deceased_name', css_class='col-md-8')),
            'description',
            Row(Column('funeral_location', css_class='col-md-8'), Column('funeral_date', css_class='col-md-4')),
            Row(Column('death_certificate', css_class='col-md-6'), Column('supporting_document', css_class='col-md-6')),
            Submit('submit', 'Report Event', css_class='btn btn-danger mt-3'),
        )


class PayoutForm(forms.ModelForm):
    class Meta:
        model = Payout
        fields = ['amount', 'recipient_name', 'recipient_phone', 'payment_method', 'payment_reference', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Confirm Disbursement', css_class='btn btn-success'))


class MeetingMinuteForm(forms.ModelForm):
    class Meta:
        model = MeetingMinute
        fields = ['date', 'location', 'agenda', 'minutes', 'attendees', 'document']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'agenda': forms.Textarea(attrs={'rows': 3}),
            'minutes': forms.Textarea(attrs={'rows': 5}),
            'attendees': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, edir=None, **kwargs):
        super().__init__(*args, **kwargs)
        if edir:
            from apps.members.models import Member
            self.fields['attendees'].queryset = Member.objects.filter(edir=edir, status='active')
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save Meeting', css_class='btn btn-primary'))

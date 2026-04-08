from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import ContributionPeriod, Contribution, SpecialLevy
import calendar


class ContributionPeriodForm(forms.ModelForm):
    class Meta:
        model = ContributionPeriod
        fields = ['year', 'month', 'amount', 'due_date', 'notes']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['month'].widget = forms.Select(choices=[
            (i, calendar.month_name[i]) for i in range(1, 13)
        ])
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('year', css_class='col-md-3'),
                Column('month', css_class='col-md-3'),
                Column('amount', css_class='col-md-3'),
                Column('due_date', css_class='col-md-3'),
            ),
            'notes',
            Submit('submit', 'Create Period & Generate Records', css_class='btn btn-primary'),
        )


class MarkPaidForm(forms.Form):
    payment_method = forms.ChoiceField(choices=Contribution.PaymentMethod.choices)
    receipt_number = forms.CharField(max_length=50, required=False, label='Receipt Number (optional)')
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Confirm Payment', css_class='btn btn-success'))


class SpecialLevyForm(forms.ModelForm):
    class Meta:
        model = SpecialLevy
        fields = ['title', 'reason', 'amount_per_member', 'due_date', 'event']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, edir=None, **kwargs):
        super().__init__(*args, **kwargs)
        if edir:
            from apps.events.models import EdirEvent
            self.fields['event'].queryset = EdirEvent.objects.filter(edir=edir)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Create Levy', css_class='btn btn-warning'))

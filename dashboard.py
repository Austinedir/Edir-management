from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML
from .models import Member, Beneficiary, EdirGroup


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth', 'photo',
            'phone', 'email', 'address', 'kebele', 'woreda', 'city',
            'status', 'join_date',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            'notes',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'join_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3 text-muted">Personal Information</h5>'),
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('last_name', css_class='col-md-4'),
                Column('gender', css_class='col-md-2'),
                Column('date_of_birth', css_class='col-md-2'),
            ),
            Row(
                Column('photo', css_class='col-md-6'),
            ),
            HTML('<h5 class="mb-3 mt-4 text-muted">Contact Details</h5>'),
            Row(
                Column('phone', css_class='col-md-4'),
                Column('email', css_class='col-md-4'),
            ),
            Row(
                Column('address', css_class='col-md-8'),
            ),
            Row(
                Column('kebele', css_class='col-md-4'),
                Column('woreda', css_class='col-md-4'),
                Column('city', css_class='col-md-4'),
            ),
            HTML('<h5 class="mb-3 mt-4 text-muted">Membership</h5>'),
            Row(
                Column('status', css_class='col-md-4'),
                Column('join_date', css_class='col-md-4'),
            ),
            HTML('<h5 class="mb-3 mt-4 text-muted">Emergency Contact</h5>'),
            Row(
                Column('emergency_contact_name', css_class='col-md-4'),
                Column('emergency_contact_phone', css_class='col-md-4'),
                Column('emergency_contact_relation', css_class='col-md-4'),
            ),
            HTML('<h5 class="mb-3 mt-4 text-muted">Notes</h5>'),
            'notes',
            Div(
                Submit('submit', 'Save Member', css_class='btn btn-primary px-4'),
                css_class='mt-4'
            )
        )


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ['name', 'relationship', 'phone', 'share_percentage']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Add Beneficiary', css_class='btn btn-success'))


class EdirGroupForm(forms.ModelForm):
    class Meta:
        model = EdirGroup
        fields = ['name', 'description', 'founded_date', 'location',
                  'monthly_contribution', 'death_payout', 'logo']
        widgets = {
            'founded_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

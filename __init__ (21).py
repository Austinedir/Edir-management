from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div
from apps.members.models_extra import MemberApplication, MassMessage, Document


class OnlineRegistrationForm(forms.ModelForm):
    """FR 1.2.2 – Online registration form."""

    confirm_terms = forms.BooleanField(
        label='I confirm that I meet the membership requirements and agree to the edir rules.',
        required=True
    )

    class Meta:
        model = MemberApplication
        fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth',
            'phone', 'email', 'address', 'city', 'state', 'zip_code',
            'rep_name', 'rep_phone', 'rep_relation',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3" style="font-family:\'Playfair Display\',serif;color:var(--edir-green);">Personal Information</h5>'),
            Row(
                Column('first_name', css_class='col-md-4'),
                Column('last_name', css_class='col-md-4'),
                Column('gender', css_class='col-md-2'),
                Column('date_of_birth', css_class='col-md-2'),
            ),
            HTML('<h5 class="mb-3 mt-4" style="font-family:\'Playfair Display\',serif;color:var(--edir-green);">Contact Details</h5>'),
            Row(
                Column('phone', css_class='col-md-4'),
                Column('email', css_class='col-md-4'),
            ),
            'address',
            Row(
                Column('city', css_class='col-md-4'),
                Column('state', css_class='col-md-2'),
                Column('zip_code', css_class='col-md-3'),
            ),
            HTML('<h5 class="mb-3 mt-4" style="font-family:\'Playfair Display\',serif;color:var(--edir-green);">Designated Representative</h5>'),
            HTML('<p class="text-muted" style="font-size:.85rem;">The person who will act on your behalf in case of an emergency.</p>'),
            Row(
                Column('rep_name', css_class='col-md-4'),
                Column('rep_phone', css_class='col-md-4'),
                Column('rep_relation', css_class='col-md-4'),
            ),
            HTML('<div class="mt-4 p-3 border rounded" style="background:#f8fbf9;">'),
            'confirm_terms',
            HTML('</div>'),
            Div(
                Submit('submit', 'Submit Application', css_class='btn btn-edir-primary px-5 mt-3'),
                css_class='mt-3'
            )
        )


class ApplicationReviewForm(forms.Form):
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Admin Notes')
    residential_verified = forms.BooleanField(required=False, label='Residential requirement verified')
    county_verified = forms.BooleanField(required=False, label='County requirement verified')


class MassMessageForm(forms.ModelForm):
    """FR 3.1/3.2 – Mass email/SMS form."""
    class Meta:
        model = MassMessage
        fields = ['channel', 'subject', 'body', 'target_active_only', 'target_city']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 8}),
            'target_city': forms.TextInput(attrs={'placeholder': 'Leave blank for all cities'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('channel', css_class='col-md-4'),
                Column('subject', css_class='col-md-8'),
            ),
            'body',
            HTML('<h6 class="mt-3 mb-2">Targeting</h6>'),
            Row(
                Column('target_active_only', css_class='col-md-4'),
                Column('target_city', css_class='col-md-4'),
            ),
            Submit('submit', 'Send Mass Message', css_class='btn btn-edir-primary mt-3'),
        )


class DocumentUploadForm(forms.ModelForm):
    """FR 2.1.1 – Upload bank statement/document."""
    class Meta:
        model = Document
        fields = ['title', 'category', 'description', 'file', 'is_public', 'year']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Upload Document', css_class='btn btn-edir-primary'))

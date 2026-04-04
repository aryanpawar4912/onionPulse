# forecast_app/custom_admin/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from ..models import *
from forecast_app.models import OnionPrice

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

class OnionPriceForm(forms.ModelForm):
    class Meta:
        model = OnionPrice
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'market': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'variety': forms.Select(attrs={'class': 'form-control'}),
            'min_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'modal_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'arrival_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
        }

class UserCreationAdminForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('Only CSV files are allowed.')
        return file

class PredictionGenerationForm(forms.Form):
    market = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    days_ahead = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=7,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate market choices dynamically
        markets = OnionPrice.objects.values_list('market', flat=True).distinct()
        self.fields['market'].choices = [(m, m) for m in markets]
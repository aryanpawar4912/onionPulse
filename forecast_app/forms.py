from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import OnionPrice, UserProfile

from django.contrib.auth.models import User


class LoginForm(AuthenticationForm):
    """
    Styled to match your login.html template.
    """
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username',
        'id': 'username',
        'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password',
        'id': 'password'
    }))

class OnionPriceForm(forms.ModelForm):
    """
    Form for manual entry of historical/current market prices.
    """
    class Meta:
        model = OnionPrice
        fields = [
            'date', 'market', 'state', 'district', 'variety', 
            'min_price', 'max_price', 'modal_price', 'arrival_quantity'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'market': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'variety': forms.TextInput(attrs={'class': 'form-control'}),
            'min_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'modal_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'arrival_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile details like User Type or Location.
    """
    class Meta:
        model = UserProfile
        fields = ['user_type', 'phone', 'location']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    
    # Fields from your UserProfile model
    phone = forms.CharField(max_length=15, required=True)
    location = forms.CharField(max_length=100, required=True)
    user_type = forms.ChoiceField(choices=UserProfile.USER_TYPES)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
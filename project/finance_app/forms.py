
from django import forms
from django.contrib.auth.models import User
from .models import AccountGroup, Account, SubAccount


class AccountGroupForm(forms.ModelForm):
    class Meta:
        model = AccountGroup
        fields = '__all__'


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = '__all__'


class SubAccountForm(forms.ModelForm):
    class Meta:
        model = SubAccount
        fields = '__all__'


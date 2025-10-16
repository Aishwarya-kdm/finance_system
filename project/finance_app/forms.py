
from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import AccountGroup, Account, SubAccount,Voucher,Transaction

class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        fields = ['journal_number', 'value_date', 'remarks']
        widgets = {
            'value_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        exclude = ('voucher', 'amount_base')
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'exchange_rate': forms.NumberInput(attrs={'step': '0.0001'}),
        }
TransactionFormSet = inlineformset_factory(
    Voucher, Transaction,
    form=TransactionForm,
    extra=1,        # number of empty rows shown initially
    can_delete=True # allow deleting rows
)    
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


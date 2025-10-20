
from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import AccountGroup, Account, SubAccount,Voucher,Transaction, Currency, Cashflow, Attribute

class VoucherForm(forms.ModelForm):
    value_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Voucher
        fields = ['journal_number', 'value_date', 'remarks']
        widgets = {
            'journal_number': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class TransactionForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        queryset=Account.objects.exclude(
            name__icontains='Position'
        ).exclude(
            name__icontains='Change USD'
        ),
        empty_label="Select Account",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    sub_account = forms.ModelChoiceField(
        queryset=SubAccount.objects.all(),
        empty_label="Select Sub Account",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    cashflow = forms.ModelChoiceField(
        queryset=Cashflow.objects.all(),
        empty_label="Select Cashflow",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    attribute = forms.ModelChoiceField(
        queryset=Attribute.objects.all(),
        empty_label="Select Attribute",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    transaction_type = forms.ChoiceField(
        choices=[('', 'Select Type')] + Transaction.TRANSACTION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
        required=True
    )

    
    currency = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].choices = [('', 'Select Currency')] + [
            (curr.code, curr.code) for curr in Currency.objects.all()
        ]
    
    class Meta:
        model = Transaction
        exclude = ('voucher', 'amount_base')
        widgets = {
            'exchange_rate': forms.NumberInput(attrs={'step': '0.0001', 'readonly': True, 'class': 'form-control'}),
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


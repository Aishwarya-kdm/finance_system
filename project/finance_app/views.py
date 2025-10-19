import requests
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect
from .decorators import jwt_required
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from .models import  AccountGroup, Account, SubAccount,Voucher,Transaction,Currency
from django.contrib.auth.models import User
from .forms import AccountForm,AccountGroupForm,SubAccountForm,VoucherForm,TransactionForm,TransactionFormSet

from decimal import Decimal
from django.db import transaction, models
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import VoucherForm, TransactionFormSet
from .models import Transaction, Currency

@transaction.atomic
def voucher_create(request):
    if request.method == 'POST':
        voucher_form = VoucherForm(request.POST)
        formset = TransactionFormSet(request.POST)

        if voucher_form.is_valid() and formset.is_valid():
            # Get transaction data before saving
            transactions_data = []
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    transactions_data.append(form.cleaned_data)
            
            if not transactions_data:
                messages.error(request, 'At least one transaction is required.')
                context = {'voucher_form': voucher_form, 'formset': formset}
                return render(request, 'voucher_form.html', context)
            
            # Check currency types
            currencies = set(str(t['currency']).upper() for t in transactions_data)
            all_usd = currencies == {'USD'}
            has_usd = 'USD' in currencies
            
            # Case 1: All USD transactions
            if all_usd:
                total_credit = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                                 if t['transaction_type'].upper() == 'CREDIT')
                total_debit = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                                if t['transaction_type'].upper() == 'DEBIT')
                
                if total_credit != total_debit:
                    messages.error(request, f'USD transactions not balanced: Credit ({total_credit}) ≠ Debit ({total_debit})')
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)
            
            # Case 2: Mixed currencies with USD (e.g., GBP + USD)
            elif has_usd:
                # Pre-validate: Check if non-USD amounts match USD amounts when converted
                non_usd_credit_base = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                                        if t['transaction_type'].upper() == 'CREDIT' and str(t['currency']).upper() != 'USD')
                non_usd_debit_base = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                                       if t['transaction_type'].upper() == 'DEBIT' and str(t['currency']).upper() != 'USD')
                usd_credit = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                               if t['transaction_type'].upper() == 'CREDIT' and str(t['currency']).upper() == 'USD')
                usd_debit = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                              if t['transaction_type'].upper() == 'DEBIT' and str(t['currency']).upper() == 'USD')
                
                expected_total_credit = non_usd_credit_base + usd_credit
                expected_total_debit = non_usd_debit_base + usd_debit
                
                if abs(expected_total_credit - expected_total_debit) > Decimal('0.01'):
                    messages.error(request, f'Mixed currency transactions not balanced: Total Credit ({expected_total_credit}) ≠ Total Debit ({expected_total_debit})')
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)
            
            # Case 3: No USD currencies (e.g., GBP + EUR)
            else:
                # Pre-validate: Check if all amounts balance when converted to base currency
                total_credit_base = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                                      if t['transaction_type'].upper() == 'CREDIT')
                total_debit_base = sum(t['amount'] * t['exchange_rate'] for t in transactions_data 
                                     if t['transaction_type'].upper() == 'DEBIT')
                
                if abs(total_credit_base - total_debit_base) > Decimal('0.01'):
                    messages.error(request, f'Multi-currency transactions not balanced: Credit ({total_credit_base}) ≠ Debit ({total_debit_base})')
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)
            
            # If validation passes, save to database
            voucher = voucher_form.save()
            transactions = formset.save(commit=False)
            for t in transactions:
                t.voucher = voucher
                t.amount_base = t.amount * t.exchange_rate  
                t.save()

            # Create position/change rows based on case
            if all_usd:
                messages.success(request, 'USD-only voucher saved successfully!')
            else:
                # Create position/change rows for non-USD currencies
                user_transactions = voucher.transactions.all()
                usd_currency, _ = Currency.objects.get_or_create(code='USD')
                
            

                # Get or create default account group
                default_group, _ = AccountGroup.objects.get_or_create(
                    name="System Accounts",
                    defaults={
                        'short_name': 'SYS',
                        'group_type': 'Assets'
                    }
                )

                for t in user_transactions:
                    currency_code = str(t.currency)[:3]  # Ensure max 3 characters
                    if currency_code.upper() != 'USD':
                        # Get or create Position account
                        position_account, _ = Account.objects.get_or_create(
                            name=f"Position - {currency_code}",
                            defaults={
                                'cr_group': default_group,
                                'dr_group': default_group
                            }
                        )
                        
                        # Get or create Change USD account
                        change_usd_account, _ = Account.objects.get_or_create(
                            name="Change USD",
                            defaults={
                                'cr_group': default_group,
                                'dr_group': default_group
                            }
                        )
                        
                        # Position row (opposite transaction type)
                        Transaction.objects.create(
                            voucher=voucher,
                            account=position_account,
                            transaction_type='Debit' if t.transaction_type.upper() == 'CREDIT' else 'Credit',
                            amount=t.amount,
                            currency='GBP',  # Use currency code string, not object
                            exchange_rate=t.exchange_rate,
                            amount_base=t.amount * t.exchange_rate
                        )
                        
                        # Change USD row (same transaction type)
                        Transaction.objects.create(
                            voucher=voucher,
                            account=change_usd_account,
                            transaction_type=t.transaction_type,
                            amount=t.amount * t.exchange_rate,
                            currency='USD',  # Use currency code string
                            exchange_rate=Decimal('1.00'),
                            amount_base=t.amount * t.exchange_rate
                        )

                # Final validation after creating all rows
                final_credit = voucher.transactions.filter(transaction_type__iexact='Credit').aggregate(
                    total=models.Sum('amount_base'))['total'] or Decimal('0.00')
                final_debit = voucher.transactions.filter(transaction_type__iexact='Debit').aggregate(
                    total=models.Sum('amount_base'))['total'] or Decimal('0.00')

                if abs(final_credit - final_debit) > Decimal('0.01'):
                    messages.error(request, f'Final voucher not balanced: Credit ({final_credit}) ≠ Debit ({final_debit})')
                    transaction.set_rollback(True)
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)
                
                if has_usd:
                    messages.success(request, 'Mixed currency voucher with USD saved successfully! Position and Change USD rows created automatically.')
                else:
                    messages.success(request, 'Multi-currency voucher saved successfully! Position and Change USD rows created automatically.')

            return redirect('voucher_list')
        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        voucher_form = VoucherForm()
        formset = TransactionFormSet()

    context = {'voucher_form': voucher_form, 'formset': formset}
    return render(request, 'voucher_form.html', context)



def voucher_list(request):
    vouchers = Voucher.objects.all()
    return render(request, 'voucher_list.html', {'vouchers': vouchers})

def edit_voucher(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    if request.method == 'POST':
        form = VoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            form.save()
            messages.success(request, "Voucher updated successfully!")
            return redirect('voucher_list')  # Replace with your list view name
    else:
        form = VoucherForm(instance=voucher)
    

def delete_voucher(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    voucher.delete()
    messages.success(request, f"Voucher {voucher.journal_number} deleted successfully!")
    return redirect('voucher_list')



def registeration(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return redirect('register')

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Registration successful! You can log in now.')
        return redirect('login')

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        response = requests.post('http://127.0.0.1:8000/api/token/', data={'username': username, 'password': password})
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access']
            refresh_token = token_data['refresh']
            request.session['access_token'] = access_token
            request.session['refresh_token'] = refresh_token
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'login.html')
#--------------------------------------------------------------------------------- 


@jwt_required
def home(request):
    return render(request, 'home.html')

@jwt_required
def account_gr_list(request):
    accounts = AccountGroup.objects.all()
    return render(request,'account_group_list.html', {'accounts': accounts})

@jwt_required
def account_gr_create(request):
    form = AccountGroupForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('account_list')
    return render(request, 'account_group_form.html', {'form': form})

@jwt_required
def account_gr_update(request, pk):
    account = get_object_or_404(AccountGroup, pk=pk)
    form = AccountGroupForm(request.POST or None, instance=account)
    if form.is_valid():
        form.save()
        return redirect('account_gr_list')
    return render(request, 'account_group_form.html', {'form': form})

@jwt_required
def account_gr_delete(request, pk):
    account = get_object_or_404(AccountGroup, pk=pk)
    account.delete()
    return redirect('account_gr_list')
#--------------------------------------------------------------------------

@jwt_required
def account_list(request):
    accounts = Account.objects.all()
    return render(request,'account_list.html', {'accounts': accounts})

@jwt_required
def account_create(request):
    form = AccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('account_list')
    return render(request, 'account_form.html', {'form': form})

@jwt_required
def account_update(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = AccountForm(request.POST or None, instance=account)
    if form.is_valid():
        form.save()
        return redirect('account_list')
    return render(request, 'account_form.html', {'form': form})

@jwt_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    account.delete()
    return redirect('account_list')
#--------------------------------------------------------------------------

@jwt_required
def subaccount_list(request):
    subs = SubAccount.objects.all()
    return render(request, 'subaccount_list.html', {'subs': subs})

@jwt_required
def subaccount_create(request):
    form = SubAccountForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('subaccount_list')
    return render(request, 'subaccount_form.html', {'form': form})

@jwt_required
def subaccount_update(request, pk):
    sub = get_object_or_404(SubAccount, pk=pk)
    form = SubAccountForm(request.POST or None, instance=sub)
    if form.is_valid():
        form.save()
        return redirect('subaccount_list')
    return render(request, 'subaccount_form.html', {'form': form})

@jwt_required
def subaccount_delete(request, pk):
    sub = get_object_or_404(SubAccount, pk=pk)
    sub.delete()
    return redirect('subaccount_list')
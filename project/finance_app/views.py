import requests
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect
from .decorators import jwt_required
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Sum
from .models import  AccountGroup, Account, SubAccount,Voucher,Transaction,Currency,Attribute
from django.contrib.auth.models import User
from .forms import AccountForm,AccountGroupForm,SubAccountForm,VoucherForm,TransactionForm,TransactionFormSet
from decimal import Decimal
from django.db import transaction, models
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import VoucherForm, TransactionFormSet
from .models import Transaction, Currency,ExchangeRate
from django.http import JsonResponse
from django.db.models import Q
from collections import defaultdict

def get_exchange_rate(request):
    currency = request.GET.get('currency')
    try:
        rate = ExchangeRate.objects.filter(
            from_currency__code=currency,
            to_currency__code='USD'
        ).latest('effective_date').exchange_rate
        return JsonResponse({'rate': str(rate)})
    except:
        return JsonResponse({'rate': '1.0000'})
    
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
            
            if not transactions_data or len(transactions_data) < 2:
                messages.error(request, 'At least two transaction is required.')
                context = {'voucher_form': voucher_form, 'formset': formset}
                return render(request, 'voucher_form.html', context)
            
            # Check currency types
            currencies = set(str(t['currency']).upper() for t in transactions_data)
            all_usd = currencies == {'USD'}
            has_usd = 'USD' in currencies
            
            # Case 1: All USD transactions
            if all_usd:
                # Calculate total credits
                exchange_rate=1
                credit_transactions = [t for t in transactions_data if t['transaction_type'].upper() == 'CREDIT']
                total_credit = sum(t['amount'] * exchange_rate for t in credit_transactions)
                
                # Calculate total debits
                debit_transactions = [t for t in transactions_data if t['transaction_type'].upper() == 'DEBIT']
                total_debit = sum(t['amount'] * exchange_rate for t in debit_transactions)
                
                if total_credit != total_debit:
                    messages.error(request, f'USD transactions not balanced: Credit ({total_credit}) ≠ Debit ({total_debit})')
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)
            
            # Case 2: (USD + other currency)
            elif has_usd:
                non_usd_credits = [t for t in transactions_data 
                                if t['transaction_type'].upper() == 'CREDIT' and str(t['currency']).upper() != 'USD']
                non_usd_debits = [t for t in transactions_data 
                                if t['transaction_type'].upper() == 'DEBIT' and str(t['currency']).upper() != 'USD']
                usd_credits = [t for t in transactions_data 
                            if t['transaction_type'].upper() == 'CREDIT' and str(t['currency']).upper() == 'USD']
                usd_debits = [t for t in transactions_data 
                            if t['transaction_type'].upper() == 'DEBIT' and str(t['currency']).upper() == 'USD']
                
                # Convert to base currency (USD)
                non_usd_credit_base = sum(t['amount'] * t['exchange_rate'] for t in non_usd_credits)
                non_usd_debit_base = sum(t['amount'] * t['exchange_rate'] for t in non_usd_debits)
                usd_credit = sum(t['amount'] * t['exchange_rate'] for t in usd_credits)
                usd_debit = sum(t['amount'] * t['exchange_rate'] for t in usd_debits)

                
                expected_total_credit = non_usd_credit_base + usd_credit
                expected_total_debit = non_usd_debit_base + usd_debit
                
                if abs(expected_total_credit - expected_total_debit) > Decimal('0.01'):
                    messages.error(request, f'Mixed currency transactions not balanced: Total Credit ({expected_total_credit}) ≠ Total Debit ({expected_total_debit})')
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)

            
            # Case 3:(both other currency)
            else:
                total_credit_base = sum(
                (t['amount'] * t['exchange_rate']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                for t in transactions_data if t['transaction_type'].upper() == 'CREDIT')

                total_debit_base = sum(
                (t['amount'] * t['exchange_rate']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                for t in transactions_data if t['transaction_type'].upper() == 'DEBIT')

                difference = (total_credit_base - total_debit_base).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                # Allow small rounding difference up to 0.05 USD
                print(abs(difference),"000000")
                if abs(difference) > Decimal('0.70'):
                    messages.error(
                        request,
                        f'Multi-currency transactions not balanced: Credit ({total_credit_base}) ≠ Debit ({total_debit_base})'
                    )
                    context = {'voucher_form': voucher_form, 'formset': formset}
                    return render(request, 'voucher_form.html', context)
                else:
                    # Auto-adjust if the difference is small (rounding or FX residual)
                    if abs(difference) > Decimal('0.00'):
                        messages.info(request, f'Rounding adjustment of {difference} USD applied automatically.')
                
                # if abs(total_credit_base - total_debit_base) > Decimal('0.01'):
                #     messages.error(request, f'Multi-currency transactions not balanced: Credit ({total_credit_base}) ≠ Debit ({total_debit_base})')
                #     context = {'voucher_form': voucher_form, 'formset': formset}
                #     return render(request, 'voucher_form.html', context)
            
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
                # usd_currency, _ = Currency.objects.get_or_create(code='USD')
                
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
                            currency=currency_code,  
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

                if abs(final_credit - final_debit) > Decimal('0.7'):
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
            print("Voucher errors:", voucher_form.errors)
            print("Formset errors:", formset.errors)
            # Replace this entire else block with the new error handling
            missing_fields = []
            
            # Check voucher form required fields
            if voucher_form.errors:
                for field in voucher_form.errors:
                    if 'required' in str(voucher_form.errors[field]):
                        missing_fields.append(f"Voucher {field}")
            
            # Check formset required fields
            for i, form in enumerate(formset):
                if form.errors:
                    for field in form.errors:
                        if 'required' in str(form.errors[field]):
                            missing_fields.append(f"Transaction {i+1} {field}")
            
            if missing_fields:
                messages.error(request, f"Required fields missing: {', '.join(missing_fields)}")
            else:
                messages.error(request, 'Please correct the errors below.')

            # Debug: Print form errors
            # print("Voucher form errors:", voucher_form.errors)
            # print("Formset errors:", formset.errors)
            # print("Formset non-form errors:", formset.non_form_errors())
            # for i, form in enumerate(formset):
            #     if form.errors:
            #         print(f"Form {i} errors:", form.errors)

    else:
        voucher_form = VoucherForm()
        formset = TransactionFormSet()

    context = {'voucher_form': voucher_form, 'formset': formset}
    return render(request, 'voucher_form.html', context)

def voucher_detail(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    transactions = voucher.transactions.all()
    return render(request, 'voucher_detail.html', {'voucher': voucher, 'transactions': transactions})

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

@jwt_required
def balance_sheet_report(request):
    from django.db.models import Sum, Q
    from django.utils import timezone
    from collections import defaultdict
    
    # Get Assets and Liabilities account groups only
    asset_groups = AccountGroup.objects.filter(group_type='Assets')
    liability_groups = AccountGroup.objects.filter(group_type='Liabilities')
    
    def calculate_group_data(groups, is_asset=True):
        groups_data = []
        grand_total = Decimal('0.00')
        
        for group in groups:
            # Get all accounts in this group
            accounts = Account.objects.filter(Q(cr_group=group) | Q(dr_group=group))
            
            accounts_data = []
            group_total = Decimal('0.00')
            
            for account in accounts:
                # Get all transactions for this account
                transactions = Transaction.objects.filter(account=account)
                
                if not transactions.exists():
                    continue
                
                # Group by SubAccount
                subaccounts_data = []
                account_total = Decimal('0.00')
                
                # Get unique SubAccounts for this account
                subaccounts = transactions.values_list('sub_account', flat=True).distinct()
                
                for sub_id in subaccounts:
                    if sub_id is None:
                        sub_name = "No SubAccount"
                        sub_transactions = transactions.filter(sub_account__isnull=True)
                    else:
                        sub_account = SubAccount.objects.get(id=sub_id)
                        sub_name = sub_account.name
                        sub_transactions = transactions.filter(sub_account=sub_account)
                    
                    # Group by Currency and Attribute combination
                    currency_attr_data = []
                    sub_total = Decimal('0.00')
                    
                    # Get unique Currency-Attribute combinations
                    combinations = sub_transactions.values('currency', 'attribute').distinct()
                    
                    for combo in combinations:
                        currency = combo['currency']
                        attribute_id = combo['attribute']
                        
                        if attribute_id:
                            attribute_name = Attribute.objects.get(id=attribute_id).name
                        else:
                            attribute_name = "No Attribute"
                        
                        # Calculate balance for this combination
                        combo_transactions = sub_transactions.filter(
                            currency=currency,
                            attribute_id=attribute_id
                        )
                        
                        balance = combo_transactions.aggregate(
                            debit=Sum('amount_base', filter=Q(transaction_type__iexact='Debit')),
                            credit=Sum('amount_base', filter=Q(transaction_type__iexact='Credit'))
                        )
                        
                        debit_total = balance['debit'] or Decimal('0.00')
                        credit_total = balance['credit'] or Decimal('0.00')
                        
                        if is_asset:
                            net_balance = debit_total - credit_total
                        else:
                            net_balance = credit_total - debit_total
                        
                        if net_balance != 0:  # Only show non-zero balances
                            currency_attr_data.append({
                                'currency': currency,
                                'attribute': attribute_name,
                                'balance': net_balance
                            })
                            sub_total += net_balance
                    
                    if currency_attr_data:  # Only add if there's data
                        subaccounts_data.append({
                            'name': sub_name,
                            'currency_attributes': currency_attr_data,
                            'total': sub_total
                        })
                        account_total += sub_total
                
                if subaccounts_data:  # Only add if there's data
                    accounts_data.append({
                        'name': account.name,
                        'subaccounts': subaccounts_data,
                        'total': account_total
                    })
                    group_total += account_total
            
            if accounts_data:  # Only add if there's data
                groups_data.append({
                    'name': group.name,
                    'accounts': accounts_data,
                    'total': group_total
                })
                grand_total += group_total
        
        return groups_data, grand_total
    
    # Calculate Assets and Liabilities
    assets_data, total_assets = calculate_group_data(asset_groups, is_asset=True)
    liabilities_data, total_liabilities = calculate_group_data(liability_groups, is_asset=False)
    
    context = {
        'assets_data': assets_data,
        'liabilities_data': liabilities_data,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'report_date': timezone.now().date()
    }
    
    return render(request, 'balance_sheet.html', context)

    

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
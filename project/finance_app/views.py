import requests
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import render, redirect
from .decorators import jwt_required
from .models import  AccountGroup, Account, SubAccount
from django.contrib.auth.models import User
from .forms import AccountForm,AccountGroupForm,SubAccountForm



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

        user = User.objects.create_user(username=username, email=email, password=password)
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
    return render(request, 'master/subaccount_form.html', {'form': form})

@jwt_required
def subaccount_delete(request, pk):
    sub = get_object_or_404(SubAccount, pk=pk)
    sub.delete()
    return redirect('subaccount_list')
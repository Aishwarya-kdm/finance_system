from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('vouchers/', views.voucher_list, name='voucher_list'),
    path('vouchers/add/', views.voucher_create, name='add_voucher'),
    path('vouchers/<int:pk>/edit/', views.edit_voucher, name='edit_voucher'),
    path('vouchers/<int:pk>/delete/', views.delete_voucher, name='delete_voucher'),
    path('vouchers/<int:pk>/', views.voucher_detail, name='voucher_detail'),
    # path('vouchers/<int:voucher_id>/transactions/', views.voucher_transactions, name='voucher_transactions'),


    path('accounts_gr/', views.account_gr_list, name='account_gr_list'),
    path('accounts_gr/add/', views.account_gr_create, name='account_gr_create'),
    path('accounts_gr/edit/<int:pk>/', views.account_gr_update, name='account_gr_update'),
    path('accounts_gr/delete/<int:pk>/', views.account_gr_delete, name='account_gr_delete'),

    path('accounts/', views.account_list, name='account_list'),
    path('accounts/add/', views.account_create, name='account_create'),
    path('accounts/edit/<int:pk>/', views.account_update, name='account_update'),
    path('accounts/delete/<int:pk>/', views.account_delete, name='account_delete'),


    path('subaccounts/', views.subaccount_list, name='subaccount_list'),
    path('subaccounts/add/', views.subaccount_create, name='subaccount_create'),
    path('subaccounts/edit/<int:pk>/', views.subaccount_update, name='subaccount_update'),
    path('subaccounts/delete/<int:pk>/', views.subaccount_delete, name='subaccount_delete'), 


    path('get-exchange-rate/', views.get_exchange_rate, name='get_exchange_rate'),
    path('balance-sheet/', views.balance_sheet_report, name='balance_sheet_report'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),

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

]
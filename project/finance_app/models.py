from django.db import models

class Voucher(models.Model):
    journal_number = models.CharField(max_length=50, unique=True)
    value_date = models.DateField()
    remarks = models.TextField(blank=True, null=True)
    base_currency = models.CharField(max_length=3, default='USD')

    class Meta:
        db_table = 'voucher' 

    def __str__(self):
        return f"Voucher {self.journal_number}"
    
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('Credit', 'Credit'),
        ('Debit', 'Debit'),
    ]

    voucher = models.ForeignKey(Voucher, related_name='transactions', on_delete=models.CASCADE)
    account = models.ForeignKey('Account', on_delete=models.CASCADE)
    sub_account = models.ForeignKey('SubAccount', on_delete=models.SET_NULL, null=True, blank=True)
    cashflow = models.ForeignKey('Cashflow', on_delete=models.SET_NULL, null=True, blank=True)
    attribute = models.ForeignKey('Attribute', on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.CharField(max_length=3)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1)
    amount_base = models.DecimalField(max_digits=15, decimal_places=2, editable=False)

    class Meta:
        db_table = 'voucher_transaction' 

    def __str__(self):
        return f"Transaction{self.voucher}"

#---------------------------------------------                                                                                                                                                           ------------------------------------------------------------------
class AccountGroup(models.Model):
    GROUP_TYPE_CHOICES = [
        ('Assets', 'Assets'),
        ('Liabilities', 'Liabilities'),
        ('Income', 'Income'),
        ('Expenses', 'Expenses'),
    ]

    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=20)
    group_type = models.CharField(
        max_length=20,
        choices=GROUP_TYPE_CHOICES,
        
    )
    class Meta:
        db_table = 'account_group' 

    def __str__(self):
        return f"{self.name} ({self.group_type})"


class Account(models.Model):
    name = models.CharField(max_length=100)
    
    # CR Group and DR Group are both foreign keys to AccountGroup
    cr_group = models.ForeignKey(
        AccountGroup,
        on_delete=models.CASCADE,
        related_name='credit_accounts'
    )
    dr_group = models.ForeignKey(
        AccountGroup,
        on_delete=models.CASCADE,
        related_name='debit_accounts'
    )

    class Meta:
        db_table = 'account'  # Custom table name (optional)

    def __str__(self):
        return self.name


class SubAccount(models.Model):
    name = models.CharField(max_length=100)

    # Interest Account dropdown → ForeignKey to Account
    interest_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='sub_accounts'
    )

    class Meta:
        db_table = 'sub_account'

    def __str__(self):
        return f"{self.name} (Interest: {self.interest_account.name})"




class Attribute(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'attribute'

    def __str__(self):
        return self.name



class Cashflow(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'cashflow'

    def __str__(self):
        return self.name


class Currency(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        db_table = 'currency'

    def __str__(self):
        return f"{self.name}"

class ExchangeRate(models.Model):
    effective_date = models.DateField()
    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='exchange_from')
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='exchange_to')
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6)

    class Meta:
        db_table = 'exchange_rate'
    def __str__(self):
        return f"{self.from_currency.code}"



    
    


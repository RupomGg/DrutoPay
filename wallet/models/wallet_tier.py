from django.db import models


class WalletTier(models.Model):
    # Limits by KYC level. Kept as data so they can change without a migration.
    code = models.CharField(
        max_length=32, 
        unique=True
    )
    name = models.CharField(max_length=64)

    max_balance = models.DecimalField(
        max_digits=19, 
        decimal_places=2
    )

    daily_credit_limit = models.DecimalField(
        max_digits=19, 
        decimal_places=2
    )
    daily_debit_limit = models.DecimalField(
        max_digits=19, 
        decimal_places=2
    )
    monthly_credit_limit = models.DecimalField(
        max_digits=19, 
        decimal_places=2
    )

    monthly_debit_limit = models.DecimalField(
        max_digits=19, 
        decimal_places=2
    )
    daily_txn_count_limit = models.PositiveIntegerField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.code})"

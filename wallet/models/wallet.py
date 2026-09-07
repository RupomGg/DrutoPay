from decimal import Decimal

from django.conf import settings
from django.db import models

from .wallet_tier import WalletTier


class Wallet(models.Model):
    # Balance fields are a cache; ledger entries are the source of truth.

    class WalletType(models.TextChoices):
        PRIMARY = 'primary', 'Primary'
        AGENT_FLOAT = 'agent_float', 'Agent float'
        AGENT_COMMISSION = 'agent_commission', 'Agent commission'
        MERCHANT_SETTLEMENT = 'merchant_settlement', 'Merchant settlement'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending activation'
        ACTIVE = 'active', 'Active'
        DORMANT = 'dormant', 'Dormant'
        FROZEN = 'frozen', 'Frozen'
        SUSPENDED = 'suspended', 'Suspended'
        CLOSED = 'closed', 'Closed'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='wallets'
    )
    wallet_type = models.CharField(
        max_length=20, 
        choices=WalletType.choices, 
        default=WalletType.PRIMARY
    )

    wallet_number = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False
    )
    
    tier = models.ForeignKey(
        WalletTier,
        on_delete=models.PROTECT, 
        related_name='wallets'
    )

    currency = models.CharField(
        max_length=3, 
        default='BDT'
    )

    balance = models.DecimalField(
        max_digits=19, 
        decimal_places=2, 
        default=Decimal('0.00')
    )

    reserved = models.DecimalField(
        max_digits=19,
        decimal_places=2, 
        default=Decimal('0.00')
    )

    overdraft_limit = models.DecimalField(
        max_digits=19,
        decimal_places=2, 
        default=Decimal('0.00')
    )

    status = models.CharField(
        max_length=12, 
        choices=Status.choices, 
        default=Status.PENDING
    )

    status_reason = models.CharField(
        max_length=255, 
        blank=True, 
        default=''
    )

    status_changed_at = models.DateTimeField(
        null=True, 
        blank=True
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    closed_at = models.DateTimeField(
        null=True, 
        blank=True
    )
    
    last_activity_at = models.DateTimeField(
        null=True, 
        blank=True
    )

    version = models.PositiveBigIntegerField(
        default=0
    )  # bumped on every balance change

    metadata = models.JSONField(
        default=dict, 
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'wallet_type'], name='uniq_customer_wallet_type'
            ),
            models.CheckConstraint(
                condition=models.Q(reserved__gte=0), name='wallet_reserved_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(balance__gte=models.F('overdraft_limit') * -1),
                name='wallet_balance_within_overdraft',
            ),
            models.CheckConstraint(
                condition=models.Q(reserved__lte=models.F('balance') + models.F('overdraft_limit')),
                name='wallet_reserved_within_balance',
            ),
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['last_activity_at']),
        ]

    @property
    def available_balance(self) -> Decimal:
        return self.balance - self.reserved

    @property
    def spendable_balance(self) -> Decimal:
        return self.balance - self.reserved + self.overdraft_limit

    def __str__(self):
        return f"{self.wallet_number} [{self.wallet_type}] {self.balance} {self.currency}"

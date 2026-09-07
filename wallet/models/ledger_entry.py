from django.db import models

from .wallet import Wallet
from .transaction import Transaction


class LedgerEntry(models.Model):
    class Direction(models.TextChoices):
        DEBIT = 'debit', 'Debit'
        CREDIT = 'credit', 'Credit'

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name='entries',
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='entries',
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    direction = models.CharField(
        max_length=6,
        choices=Direction.choices,
    )

    balance_after = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='ledgerentry_amount_positive',
            ),
        ]

    def save(self, *args, **kwargs):
        # Append-only: insert once, never update.
        if self.pk is not None:
            raise ValueError("LedgerEntry rows are immutable and cannot be updated")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.direction} {self.amount} on wallet {self.wallet_id}"

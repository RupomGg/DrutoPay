import uuid

from django.db import models

from wallet.reference import allocate_reference


class Transaction(models.Model):
    class Type(models.TextChoices):
        P2P_TRANSFER = 'p2p_transfer', 'P2P Transfer'
        CASH_IN = 'cash_in', 'Cash In'
        CASH_OUT = 'cash_out', 'Cash Out'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Human-facing reference (TX + 10 opaque digits). Internal FKs still use id.
    reference = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
    )

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    idempotency_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = allocate_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} {self.type} [{self.status}]"

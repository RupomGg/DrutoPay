from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Wallet, Transaction, LedgerEntry


class TransactionError(Exception):
    pass


class WalletNotActive(TransactionError):
    pass

class InsufficientBalance(TransactionError):
    pass

class LimitExceeded(TransactionError):
    pass


def _sum(wallet, direction, since):
    return wallet.entries.filter(
        direction = direction,
        created_at__gte = since
    ).aggregate(
        s=Sum('amount')
    )['s'] or Decimal('0')

    
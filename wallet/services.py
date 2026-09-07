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

def send_money(*, sender_wallet, recipient, amount, idempotency_key):
    existing = Transaction.objects.filter(
        idempotency_key = idempotency_key
    ).first()
    if existing:
        return existing
    
    if amount <= 0:
        raise TransferError("Amount must be positive")

    try:
        recipient_wallet = Wallet.objects.get(
            wallet_number = recipient,
            wallet_type = Wallet.WalletType.PRIMARY
        )
    
    except Wallet.DoesNotExist:
        raise TransferError("Recipient wallet not found")
    

    if sender_wallet.pk == recipient_wallet.pk:
        raise TransferError("Cannot send money to your own wallet")

    ids = sorted([sender_wallet.pk, recipient_wallet.pk])


    try:

        with transaction.atomic():
            locked = {
                w.pk: w
                for w in Wallet.objects.select_for_update()
                .select_related('tier')
                .filter(pk__in=ids)
            }

            sender = locked[sender_wallet.pk]
            receiver = locked[recipient_wallet.pk]

            if sender.status != Wallet.Status.ACTIVE:
                raise WalletNotActive("Sender wallet is not active")
            if receiver.status != Wallet.Status.ACTIVE:
                raise WalletNotActive("Recipient wallet  is not active")
            
            if sender.available_balance < amount:
                raise InsufficientBalance("Insufficient balance")
                
            
            now = timezone.now()
            day = now.replace(
                hour=0, 
                minute=0, 
                second=0, 
                microsecond=0
            )

            month = day.replace(day=1)

            st = sender.tier

            if _sum(sender,'debit', day) +amount > st.daily_debit_limit:
                raise LimitExceeded("Daily send money limit exceeded")

            if _sum(sender, "debit", month) + amount > st.monthly_debit_limit:
                raise LimitExceeded("Monthly send money limit exceeded")

            if sender.entries.filter(direction="debit", created_at__gte=day).count() >= st.daily_txn_count_limit:
                raise LimitExceeded("Daily transaction count exceeded")

            rt = receiver.tier

            if _sum(receiver, "credit", day) + amount > rt.daily_credit_limit:
                raise LimitExceeded("Recipient daily receive limit exceeded")
                
            if receiver.balance + amount > rt.max_balance:
                raise LimitExceeded("Recipient balance limit exceeded")

            txn = Transaction.objects.create(
                type=Transaction.Type.P2P_TRANSFER,
                status=Transaction.Status.PENDING,
                idempotency_key=idempotency_key,
            )

            sender.balance -= amount
            sender.version += 1
            sender.last_activity_at = now
            sender.save(update_fields=["balance", "version", "last_activity_at", "updated_at"])

            receiver.balance += amount
            receiver.version += 1
            receiver.last_activity_at = now
            receiver.save(update_fields=["balance", "version", "last_activity_at", "updated_at"])

            LedgerEntry.objects.create(
                transaction=txn, wallet=sender, amount=amount,
                direction=LedgerEntry.Direction.DEBIT, balance_after=sender.balance,
            )
            LedgerEntry.objects.create(
                transaction=txn, wallet=receiver, amount=amount,
                direction=LedgerEntry.Direction.CREDIT, balance_after=receiver.balance,
            )

            txn.status = Transaction.Status.COMPLETED
            txn.save(update_fields=["status"])

            txn.new_balance = sender.balance
            return txn

    except IntegrityError:
        existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        raise
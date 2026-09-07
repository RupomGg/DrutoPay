from decimal import Decimal

from django.test import TestCase
from accounts.models import User
from wallet.models import Wallet, Transaction, LedgerEntry
from wallet.services import send_money, InsufficientBalance, LimitExceeded, TransactionError


class SendMoneyTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(phone_number="01710000001", password="123456")
        self.b = User.objects.create_user(phone_number="01710000002", password="123456")
        self.wa = self.a.wallets.get()
        self.wb = self.b.wallets.get()
        Wallet.objects.filter(pk=self.wa.pk).update(balance=Decimal("500.00"))
        self.wa.refresh_from_db()

    def test_happy_path(self):
        t = send_money(sender_wallet=self.wa, recipient=self.wb.wallet_number,
                       amount=Decimal("200.00"), idempotency_key="k1")
        self.wa.refresh_from_db(); self.wb.refresh_from_db()
        self.assertEqual(self.wa.balance, Decimal("300.00"))
        self.assertEqual(self.wb.balance, Decimal("200.00"))
        self.assertEqual(t.status, Transaction.Status.COMPLETED)
        entries = LedgerEntry.objects.filter(transaction=t)
        net = sum((e.amount if e.direction == "credit" else -e.amount) for e in entries)
        self.assertEqual(net, Decimal("0"))

    def test_idempotent_retry(self):
        t1 = send_money(sender_wallet=self.wa, recipient=self.wb.wallet_number,
                        amount=Decimal("200.00"), idempotency_key="same")
        t2 = send_money(sender_wallet=self.wa, recipient=self.wb.wallet_number,
                        amount=Decimal("200.00"), idempotency_key="same")
        self.assertEqual(t1.pk, t2.pk)
        self.wa.refresh_from_db()
        self.assertEqual(self.wa.balance, Decimal("300.00"))

    def test_insufficient_funds(self):
        with self.assertRaises(InsufficientBalance):
            send_money(sender_wallet=self.wa, recipient=self.wb.wallet_number,
                       amount=Decimal("9999.00"), idempotency_key="k")
        self.wa.refresh_from_db()
        self.assertEqual(self.wa.balance, Decimal("500.00"))
        self.assertFalse(LedgerEntry.objects.exists())

    def test_daily_limit(self):
        Wallet.objects.filter(pk=self.wa.pk).update(balance=Decimal("100000"))
        self.wa.refresh_from_db()
        with self.assertRaises(LimitExceeded):
            send_money(sender_wallet=self.wa, recipient=self.wb.wallet_number,
                       amount=Decimal("30000"), idempotency_key="k")

    def test_self_transfer(self):
        with self.assertRaises(TransactionError):
            send_money(sender_wallet=self.wa, recipient=self.wa.wallet_number,
                       amount=Decimal("10.00"), idempotency_key="k")

    def test_ledger_immutable(self):
        t = send_money(sender_wallet=self.wa, recipient=self.wb.wallet_number,
                       amount=Decimal("50.00"), idempotency_key="k")
        row = LedgerEntry.objects.filter(transaction=t).first()
        row.amount = Decimal("1.00")
        with self.assertRaises(ValueError):
            row.save()
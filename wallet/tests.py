import threading
from decimal import Decimal

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APITestCase

from accounts.models import User
from wallet.models import Wallet, WalletTier, Transaction, LedgerEntry
from wallet.services import (
    send_money,
    TransactionError,
    WalletNotActive,
    InsufficientBalance,
    LimitExceeded,
)


def make_user(phone, pin="123456", balance="0"):
    user = User.objects.create_user(phone_number=phone, password=pin)
    user.is_phone_verified = True
    user.save(update_fields=["is_phone_verified"])
    wallet = user.wallets.get()
    if Decimal(balance):
        Wallet.objects.filter(pk=wallet.pk).update(balance=Decimal(balance))
        wallet.refresh_from_db()
    return user, wallet


class SendMoneyServiceTests(TestCase):
    def setUp(self):
        self.a_user, self.a = make_user("01710000001", balance="500.00")
        self.b_user, self.b = make_user("01710000002")

    def transfer(self, amount, key):
        return send_money(
            sender_wallet=self.a,
            recipient=self.b.wallet_number,
            amount=Decimal(amount),
            idempotency_key=key,
        )

    def test_happy_path(self):
        txn = self.transfer("200.00", "k1")
        self.a.refresh_from_db()
        self.b.refresh_from_db()

        self.assertEqual(self.a.balance, Decimal("300.00"))
        self.assertEqual(self.b.balance, Decimal("200.00"))
        self.assertEqual(txn.status, Transaction.Status.COMPLETED)
        self.assertTrue(txn.reference.startswith("TX"))
        self.assertEqual(txn.new_balance, Decimal("300.00"))

        entries = LedgerEntry.objects.filter(transaction=txn)
        self.assertEqual(entries.count(), 2)
        net = sum(
            (e.amount if e.direction == LedgerEntry.Direction.CREDIT else -e.amount)
            for e in entries
        )
        self.assertEqual(net, Decimal("0"))
        debit = entries.get(direction=LedgerEntry.Direction.DEBIT)
        self.assertEqual(debit.wallet_id, self.a.pk)
        self.assertEqual(debit.balance_after, Decimal("300.00"))

    def test_version_and_activity_bump(self):
        v_before = self.a.version
        self.transfer("50.00", "k1")
        self.a.refresh_from_db()
        self.assertEqual(self.a.version, v_before + 1)
        self.assertIsNotNone(self.a.last_activity_at)

    def test_idempotent_retry(self):
        first = self.transfer("200.00", "same-key")
        second = self.transfer("200.00", "same-key")
        self.assertEqual(first.pk, second.pk)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.balance, Decimal("300.00"))
        self.assertEqual(self.b.balance, Decimal("200.00"))
        self.assertEqual(LedgerEntry.objects.count(), 2)

    def test_insufficient_funds(self):
        with self.assertRaises(InsufficientBalance):
            self.transfer("9999.00", "k1")
        self.a.refresh_from_db()
        self.assertEqual(self.a.balance, Decimal("500.00"))
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(LedgerEntry.objects.exists())

    def test_self_transfer(self):
        with self.assertRaises(TransactionError):
            send_money(
                sender_wallet=self.a,
                recipient=self.a.wallet_number,
                amount=Decimal("10.00"),
                idempotency_key="k1",
            )

    def test_negative_amount(self):
        with self.assertRaises(TransactionError):
            self.transfer("-10.00", "k1")

    def test_recipient_not_found(self):
        with self.assertRaises(TransactionError):
            send_money(
                sender_wallet=self.a,
                recipient="0000000000",
                amount=Decimal("10.00"),
                idempotency_key="k1",
            )

    def test_frozen_sender(self):
        Wallet.objects.filter(pk=self.a.pk).update(status=Wallet.Status.FROZEN)
        with self.assertRaises(WalletNotActive):
            self.transfer("10.00", "k1")

    def test_daily_debit_limit(self):
        # customer_lite daily_debit_limit is 25000
        Wallet.objects.filter(pk=self.a.pk).update(balance=Decimal("100000.00"))
        self.a.refresh_from_db()
        with self.assertRaises(LimitExceeded):
            self.transfer("30000.00", "k1")

    def test_daily_txn_count_limit(self):
        WalletTier.objects.filter(code="customer_lite").update(daily_txn_count_limit=2)
        self.transfer("10.00", "k1")
        self.transfer("10.00", "k2")
        with self.assertRaises(LimitExceeded):
            self.transfer("10.00", "k3")

    def test_recipient_balance_cap(self):
        # recipient on customer_lite (max_balance 50000), already near the cap
        Wallet.objects.filter(pk=self.b.pk).update(balance=Decimal("49000.00"))
        Wallet.objects.filter(pk=self.a.pk).update(
            balance=Decimal("100000.00"),
            tier=WalletTier.objects.get(code="customer_full"),
        )
        self.a.refresh_from_db()
        with self.assertRaises(LimitExceeded):
            self.transfer("2000.00", "k1")

    def test_ledger_entry_is_immutable(self):
        txn = self.transfer("50.00", "k1")
        row = LedgerEntry.objects.filter(transaction=txn).first()
        row.amount = Decimal("1.00")
        with self.assertRaises(ValueError):
            row.save()


class WalletAPITests(APITestCase):
    def setUp(self):
        self.a_user, self.a = make_user("01710000001", balance="500.00")
        self.b_user, self.b = make_user("01710000002")
        token = self.client.post(
            "/api/auth/login/",
            {"phone_number": "01710000001", "pin": "123456"},
            format="json",
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def send(self, **over):
        body = {
            "recipient": self.b.wallet_number,
            "amount": "200.00",
            "pin": "123456",
            "idempotency_key": "api-1",
        }
        body.update(over)
        return self.client.post("/api/wallet/send/", body, format="json")

    def test_requires_auth(self):
        self.client.credentials()  # drop the token
        self.assertEqual(self.client.get("/api/wallet/").status_code, 401)

    def test_wallet_detail(self):
        r = self.client.get("/api/wallet/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["wallet_number"], self.a.wallet_number)
        self.assertNotIn("id", r.data)
        self.assertIn("limits", r.data)

    def test_balance(self):
        r = self.client.get("/api/wallet/balance/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(str(r.data["available_balance"])), Decimal("500.00"))

    def test_send_ok(self):
        r = self.send()
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data["reference"].startswith("TX"))
        self.assertEqual(Decimal(r.data["new_balance"]), Decimal("300.00"))
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.balance, Decimal("300.00"))
        self.assertEqual(self.b.balance, Decimal("200.00"))

    def test_send_wrong_pin(self):
        r = self.send(pin="000000")
        self.assertEqual(r.status_code, 401)
        self.a.refresh_from_db()
        self.assertEqual(self.a.balance, Decimal("500.00"))

    def test_send_insufficient(self):
        r = self.send(amount="9999.00", idempotency_key="api-2")
        self.assertEqual(r.status_code, 422)

    def test_send_self(self):
        r = self.send(recipient=self.a.wallet_number)
        self.assertEqual(r.status_code, 400)

    def test_send_idempotent(self):
        r1 = self.send()
        r2 = self.send()
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.data["reference"], r2.data["reference"])
        self.a.refresh_from_db()
        self.assertEqual(self.a.balance, Decimal("300.00"))

    def test_statement(self):
        self.send()
        r = self.client.get("/api/wallet/statement/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)
        row = r.data["results"][0]
        self.assertNotIn("id", row)
        self.assertTrue(row["reference"].startswith("TX"))
        self.assertEqual(row["direction"], LedgerEntry.Direction.DEBIT)


class TransferConcurrencyTests(TransactionTestCase):
    """Needs real committed transactions across threads, so TransactionTestCase
    (not TestCase) and a real locking DB (Postgres). On SQLite these pass by
    luck because writes serialize globally."""

    def test_no_double_spend(self):
        _, a = make_user("01710000001", balance="300.00")
        _, b = make_user("01710000002")

        results = []

        def go(key):
            try:
                send_money(
                    sender_wallet=a,
                    recipient=b.wallet_number,
                    amount=Decimal("200.00"),
                    idempotency_key=key,
                )
                results.append("ok")
            except InsufficientBalance:
                results.append("rejected")
            finally:
                connection.close()

        t1 = threading.Thread(target=go, args=("c1",))
        t2 = threading.Thread(target=go, args=("c2",))
        t1.start(); t2.start()
        t1.join(); t2.join()

        a.refresh_from_db()
        b.refresh_from_db()

        self.assertEqual(sorted(results), ["ok", "rejected"])   # exactly one wins
        self.assertEqual(a.balance, Decimal("100.00"))          # never oversold
        self.assertEqual(b.balance, Decimal("200.00"))
        self.assertEqual(Transaction.objects.filter(status=Transaction.Status.COMPLETED).count(), 1)
        self.assertEqual(LedgerEntry.objects.count(), 2)

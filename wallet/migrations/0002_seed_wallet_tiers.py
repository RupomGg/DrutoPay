from decimal import Decimal

from django.db import migrations


# Placeholder limits. Replace with the current Bangladesh Bank circular figures.
TIERS = [
    {
        "code": "customer_lite",
        "name": "Customer — limited KYC",
        "max_balance": Decimal("50000.00"),
        "daily_credit_limit": Decimal("50000.00"),
        "daily_debit_limit": Decimal("25000.00"),
        "monthly_credit_limit": Decimal("300000.00"),
        "monthly_debit_limit": Decimal("200000.00"),
        "daily_txn_count_limit": 20,
    },
    {
        "code": "customer_full",
        "name": "Customer — full KYC",
        "max_balance": Decimal("450000.00"),
        "daily_credit_limit": Decimal("500000.00"),
        "daily_debit_limit": Decimal("50000.00"),
        "monthly_credit_limit": Decimal("1500000.00"),
        "monthly_debit_limit": Decimal("500000.00"),
        "daily_txn_count_limit": 50,
    },
    {
        "code": "agent",
        "name": "Agent",
        "max_balance": Decimal("10000000.00"),
        "daily_credit_limit": Decimal("10000000.00"),
        "daily_debit_limit": Decimal("10000000.00"),
        "monthly_credit_limit": Decimal("200000000.00"),
        "monthly_debit_limit": Decimal("200000000.00"),
        "daily_txn_count_limit": 2000,
    },
    {
        "code": "merchant",
        "name": "Merchant",
        "max_balance": Decimal("5000000.00"),
        "daily_credit_limit": Decimal("5000000.00"),
        "daily_debit_limit": Decimal("2000000.00"),
        "monthly_credit_limit": Decimal("100000000.00"),
        "monthly_debit_limit": Decimal("50000000.00"),
        "daily_txn_count_limit": 1000,
    },
]


def seed(apps, schema_editor):
    WalletTier = apps.get_model("wallet", "WalletTier")
    for row in TIERS:
        WalletTier.objects.update_or_create(code=row["code"], defaults=row)


def unseed(apps, schema_editor):
    WalletTier = apps.get_model("wallet", "WalletTier")
    WalletTier.objects.filter(code__in=[r["code"] for r in TIERS]).delete()


class Migration(migrations.Migration):
    dependencies = [("wallet", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]

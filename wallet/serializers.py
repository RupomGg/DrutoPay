from decimal import Decimal , ROUND_DOWN

from rest_framework import serializers

from .models import Wallet , WalletTier, LedgerEntry, Transaction


class TierLimitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTier

        fields = [
            'code','name',
            'max_balance',
            'daily_credit_limit',
            'daily_debit_limit',
            'monthly_debit_limit',
            'monthly_credit_limit',
            'daily_txn_count_limit',
        ]

        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(
        max_digits = 19,
        decimal_places = 2,
        read_only = True
    )

    spendable_balance = serializers.DecimalField(
        max_digits= 19,
        decimal_places = 2,
        read_only = True
    )

    limits = TierLimitsSerializer(
        source = 'tier',
        read_only = True
    )


    class Meta:
        model = Wallet
        fields = [
            'wallet_number',
            'wallet_type',
            'currency',
            'balance',
            'reserved',
            'available_balance',
            'spendable_balance',
            'status',
            'limits',
        ]

        read_only_fields = fields

class LedgerEntrySerializer(serializers.ModelSerializer):
    
    transaction_id = serializers.UUIDField(
        source = 'transaction.id',
        read_only = True
    )

    transaction_type = serializers.CharField(
        source = 'transaction.type',
        read_only = True
    )

    class Meta:
        model = LedgerEntry
        fields = [
            'id', 
            'transaction_id',
            'transaction_type',
            'direction',
            'amount',
            'balance_after',
            'created_at'
        ]

        read_only_fields = fields


class SendMoneySerializer(serializers.Serializer):
    recipient = serializers.CharField()           # recipient account_number
    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=2, 
        min_value=Decimal("0.01")
    )
    pin = serializers.CharField(
        write_only=True
    )# transaction PIN, re-checked per transfer

    idempotency_key = serializers.CharField(
        max_length=64
    )

    def validate_amount(self, value):
        if value != value.quantize(Decimal("0.01"), rounding=ROUND_DOWN):
            raise serializers.ValidationError("Amount supports at most 2 decimal places.")
        return value

    def validate(self, attrs):
        sender = self.context["request"].user.wallets.get(wallet_type=Wallet.WalletType.PRIMARY)
        if attrs["recipient"] == sender.account_number:
            raise serializers.ValidationError("Cannot send to your own wallet.")
        attrs["sender_wallet"] = sender
        return attrs


class TransactionResultSerializer(serializers.ModelSerializer):
    new_balance = serializers.DecimalField(
        max_digits=19, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id", 
            "type", 
            "status", 
            "created_at", 
            "new_balance"
        ]

        read_only_fields = fields
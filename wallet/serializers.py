from decimal import Decimal, ROUND_DOWN

from rest_framework import serializers

from .models import Wallet, WalletTier, LedgerEntry, Transaction


class TierLimitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTier
        fields = [
            'code', 
            'name',
            'max_balance',
            'daily_debit_limit',
            'daily_credit_limit',
            'monthly_debit_limit',
            'monthly_credit_limit',
            'daily_txn_count_limit',
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(
        max_digits=19,
        decimal_places=2, 
        read_only=True
    )
    spendable_balance = serializers.DecimalField(
        max_digits=19, 
        decimal_places=2, 
        read_only=True
    )
    limits = TierLimitsSerializer(source='tier', read_only=True)

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


class LedgerEntrySerializer(serializers.ModelSerializer):
    reference = serializers.CharField(
        source='transaction.reference',
        read_only=True
    )
    transaction_type = serializers.CharField(
        source='transaction.type',
        read_only=True
    )

    class Meta:
        model = LedgerEntry
        fields = [
            'reference',
            'transaction_type',
            'direction',
            'amount',
            'balance_after',
            'created_at',
        ]


class SendMoneySerializer(serializers.Serializer):
    recipient = serializers.CharField()            # recipient wallet_number
    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )
    pin = serializers.CharField(
        write_only=True
    )  # transaction PIN, re-checked per transfer

    idempotency_key = serializers.CharField(
        max_length=64
    )

    def validate_amount(self, value):
        if value != value.quantize(Decimal('0.01'), rounding=ROUND_DOWN):
            raise serializers.ValidationError("Amount supports at most 2 decimal places.")
        return value

    def validate(self, attrs):
        sender = self.context['request'].user.wallets.get(wallet_type=Wallet.WalletType.PRIMARY)
        if attrs['recipient'] == sender.wallet_number:
            raise serializers.ValidationError("Cannot send to your own wallet.")
        attrs['sender_wallet'] = sender
        return attrs


class TransactionResultSerializer(serializers.ModelSerializer):
    # The view sets `txn.new_balance` on the instance before serializing it.
    new_balance = serializers.DecimalField(max_digits=19, decimal_places=2, read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'reference',
            'type',
            'status',
            'created_at',
            'new_balance'
        ]

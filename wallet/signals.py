from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Wallet, WalletTier


# Which tier a brand-new account lands on, by user type. Customers start on the
# limited tier and are moved to the full tier once KYC is completed.
_DEFAULT_TIER_BY_USER_TYPE = {
    'customer': 'customer_lite',
    'agent': 'agent',
    'merchant': 'merchant',
}


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_primary_wallet(sender, instance, created, **kwargs):
    if not created:
        return

    user_type = getattr(
        instance,
        'user_type',
        'customer'
    )
    tier_code = _DEFAULT_TIER_BY_USER_TYPE.get(
        user_type, 
        'customer_lite'
    )
    tier = (
        WalletTier.objects.filter(code=tier_code).first()
        or WalletTier.objects.filter(code='customer_lite').first()
    )

    now = timezone.now()
    Wallet.objects.get_or_create(
        customer=instance,
        wallet_type=Wallet.WalletType.PRIMARY,
        defaults={
            'wallet_number': instance.wallet_number,
            'tier': tier,
            'status': Wallet.Status.ACTIVE,
            'activated_at': now,
            'status_changed_at': now,
            'last_activity_at': now,
        },
    )

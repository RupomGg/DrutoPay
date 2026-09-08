from rest_framework.permissions import BasePermission

from .models import Wallet

class HasActiveWallet(BasePermission):
    message = "Your wallet is not Active"

    def has_permission(self,request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.wallets.filter(
            wallet_type = Wallet.WalletType.PRIMARY,
            status = Wallet.Status.ACTIVE,
        ).exists()
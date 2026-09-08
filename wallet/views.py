from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination

from .models import Wallet, LedgerEntry
from .permissions import HasActiveWallet
from .serializers import (
    WalletSerializer,
    LedgerEntrySerializer,
    SendMoneySerializer,
    TransactionResultSerializer
)
from  .services import (
    send_money,
    TransactionError,
    InsufficientBalance,
    LimitExceeded,
    WalletNotActive,
)


def _primary_wallet(user):
    return user.wallets.select_related('tier').get(
        wallet_type = Wallet.WalletType.PRIMARY
    )

class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            WalletSerializer(_primary_wallet(request.user)).data
        )

class BalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        w = _primary_wallet(request.user)
        return Response({
            "available_balance": w.available_balance, 
            "currency": w.currency
        })

class SendMoneyView(APIView):
    permission_classes = [IsAuthenticated, HasActiveWallet]
    throttle_scope = "wallet_send"

    def post(self, request):
        s = SendMoneySerializer(
            data = request.data,
            context = {'request': request}
        )

        s.is_valid(raise_exception = True)
        data = s.validated_data

        if not request.user.check_password(data["pin"]):
            return Response(
                {"error": "Invalid PIN."},
                status = status.HTTP_401_UNAUTHORIZED
            )

        try:
            txn = send_money(
                sender_wallet = data["sender_wallet"],
                recipient = data["recipient"],
                amount = data["amount"],
                idempotency_key = data["idempotency_key"]
            )
        except(
            InsufficientBalance,
            LimitExceeded,
            WalletNotActive
        ) as exc:
            return Response(
                {"error": str(exc)},
                status = status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except TransactionError as exc:
            return Response(
                {"error": str(exc)},
                status = status.HTTP_400_BAD_REQUEST
            )

        return Response(
            TransactionResultSerializer(txn).data,
            status = status.HTTP_201_CREATED    
        )

class LedgerPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 20

class StatementView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LedgerEntrySerializer
    pagination_class = LedgerPagination
    throttle_scope = "wallet_read"

    def get_queryset(self):
        w = _primary_wallet(self.request.user)
        return(
            LedgerEntry.objects
            .filter(wallet = w)
            .select_related("transaction")
            .order_by("-created_at")
        )



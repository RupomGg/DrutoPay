from django.urls import path

from .views import WalletDetailView, BalanceView, SendMoneyView, StatementView

urlpatterns = [
    path("",WalletDetailView.as_view(),name = "wallet-detail"),
    path("balance/",BalanceView.as_view(),name = "wallet-balance"),
    path("send/",SendMoneyView.as_view(),name = "wallet-send"),
    path("statement/",StatementView.as_view(),name = "wallet-statement")
]
import hmac
import hashlib

from django.conf import settings
from django.db import models


PREFIX = "TX"
DIGITS = 10
_DOMAIN = 10 ** DIGITS
_HALF_BITS = 17
_HALF_MASK = (1 << _HALF_BITS) - 1
_ROUNDS = 4
_INDEX_OFFSET = 1_000_000_000


class TxnCounter(models.Model):
    # Autoincrement PK is the sequence; one row per allocated reference.
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_txn_counter"


def _prf(round_no: int, half: int) -> int:
    msg = round_no.to_bytes(1, "big") + half.to_bytes(4, "big")
    digest = hmac.new(settings.TXN_REFERENCE_SECRET.encode(), msg, hashlib.sha256).digest()
    return int.from_bytes(digest[:4], "big") & _HALF_MASK


def _feistel(block: int) -> int:
    left = (block >> _HALF_BITS) & _HALF_MASK
    right = block & _HALF_MASK
    for round_no in range(_ROUNDS):
        left, right = right, left ^ _prf(round_no, right)
    return (left << _HALF_BITS) | right


def _mask(index: int) -> int:
    value = index % _DOMAIN
    while True:
        value = _feistel(value)
        if value < _DOMAIN:
            return value


def allocate_reference() -> str:
    index = TxnCounter.objects.create().pk + _INDEX_OFFSET
    return f"{PREFIX}{_mask(index):0{DIGITS}d}"

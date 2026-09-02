"""Central, monotonic allocation of the internal wallet number.

Two concerns are kept deliberately separate:

1. Uniqueness + ordering
   A database counter (``CustomerIdAllocation``). Each call inserts exactly one
   row and returns its primary key. The database serialises that insert, so
   every caller gets a distinct, monotonically increasing index with no race
   condition and no ``SELECT ... WHERE EXISTS`` retry loop. A rolled-back
   transaction consumes an index without releasing it, so the sequence has
   gaps -- that is expected and harmless.

2. Opacity
   A keyed Feistel permutation turns that sequential index into a 10-digit
   number with no visible order or rate. The permutation is a bijection, so
   two different indexes can never collide: the wallet number inherits its
   uniqueness from the counter and is never re-checked against the table.

This mirrors how a production MFS runs a customer-id / CIF allocator behind a
single identity service: one writer owns the counter, everything downstream
stores only the opaque id and never the phone number.
"""

import hmac
import hashlib

from django.conf import settings
from django.db import models


WALLET_NUMBER_DIGITS = 10
_DOMAIN = 10 ** WALLET_NUMBER_DIGITS          # valid outputs: 0 .. 9_999_999_999

# Feistel over a 2**34 block (34 > log2(_DOMAIN)); cycle-walk back into _DOMAIN.
_HALF_BITS = 17                               # 2**34 == (2**17) ** 2
_HALF_MASK = (1 << _HALF_BITS) - 1
_ROUNDS = 4

# Offset the counter so the first customers are not 0000000001, 0000000002, ...
# and so masked output reliably fills all 10 digits.
_INDEX_OFFSET = 1_000_000_000


class CustomerIdAllocation(models.Model):
    """One row per allocated wallet number.

    The autoincrement primary key *is* the central sequence. ``BigAutoField``
    gives the same atomic, monotonic guarantee on SQLite and PostgreSQL, so the
    allocator is portable without a raw ``CREATE SEQUENCE``.
    """

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_customer_id_allocation"
        verbose_name = "customer id allocation"


def _prf(round_no: int, half: int) -> int:
    """Keyed round function: HMAC-SHA256(secret, round || half) folded to 17 bits."""
    msg = round_no.to_bytes(1, "big") + half.to_bytes(4, "big")
    digest = hmac.new(settings.WALLET_NUMBER_SECRET.encode(), msg, hashlib.sha256).digest()
    return int.from_bytes(digest[:4], "big") & _HALF_MASK


def _feistel(block: int) -> int:
    """Bijective permutation of a 34-bit block."""
    left = (block >> _HALF_BITS) & _HALF_MASK
    right = block & _HALF_MASK
    for round_no in range(_ROUNDS):
        left, right = right, left ^ _prf(round_no, right)
    return (left << _HALF_BITS) | right


def mask_index(index: int) -> int:
    """Map a sequential index to an opaque value in 0 .. _DOMAIN-1.

    Cycle-walking: re-encrypt until the result lands inside the 10-digit range.
    Feistel is a bijection on [0, 2**34); restricting the walk to [0, _DOMAIN)
    keeps it a bijection there, so distinct indexes give distinct outputs.
    """
    value = index % _DOMAIN
    while True:
        value = _feistel(value)
        if value < _DOMAIN:
            return value


def allocate_wallet_number() -> str:
    """Reserve the next index centrally and return its opaque 10-digit form."""
    index = CustomerIdAllocation.objects.create().pk + _INDEX_OFFSET
    return f"{mask_index(index):0{WALLET_NUMBER_DIGITS}d}"

from django.test import TestCase
from accounts.models import User, CustomerIdAllocation
from accounts.identity import mask_index, allocate_wallet_number


class WalletNumberTests(TestCase):
    def test_format_and_uniqueness(self):
        ws = {User.objects.create_user(phone_number=f"0170000{i:04d}", password="123456").wallet_number
              for i in range(50)}
        self.assertEqual(len(ws), 50)                       # all unique
        self.assertTrue(all(len(w) == 10 and w.isdigit() for w in ws))

    def test_counter_advances_once_per_user(self):
        before = CustomerIdAllocation.objects.count()
        User.objects.create_user(phone_number="01700009999", password="123456")
        self.assertEqual(CustomerIdAllocation.objects.count(), before + 1)

    def test_mask_is_deterministic_bijection(self):
        rng = range(1_000_000_001, 1_000_020_001)
        out = [mask_index(i) for i in rng]
        self.assertEqual(len(out), len(set(out)))           # no collisions
        self.assertTrue(all(0 <= x < 10**10 for x in out))
        self.assertEqual(mask_index(42), mask_index(42))    # deterministic

    def test_not_sequential(self):
        a, b = mask_index(1_000_000_001), mask_index(1_000_000_002)
        self.assertNotEqual(abs(a - b), 1)                  # consecutive in ≠ consecutive out
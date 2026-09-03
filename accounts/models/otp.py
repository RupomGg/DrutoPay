import hmac
import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

from .user import hash_phone


def hash_otp(phone_number: str, code: str) -> str:
    """Keyed hash that binds the code to the phone number.

    A 6-digit code has only 10**6 possible values, so a bare SHA-256 of it is
    reversed instantly with a precomputed table. The secret (kept outside the
    database) makes that infeasible without the key, and mixing the phone in
    means a stolen hash cannot be replayed against a different number.
    """
    msg = f"{phone_number}:{code}".encode()
    return hmac.new(settings.OTP_HASH_SECRET.encode(), msg, hashlib.sha256).hexdigest()


class OTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        LOGIN = 'login', 'Login'
        PASSWORD_RESET = 'password_reset', 'Password Reset'

    phone_hash = models.CharField(max_length=64)
    code_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.REGISTRATION)

    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['phone_hash', 'purpose']),
        ]

    @staticmethod
    def generate_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @classmethod
    def create_for(cls, phone_number: str, purpose: str = Purpose.REGISTRATION, valid_minutes: int = 5):
        phone_hash = hash_phone(phone_number)
        # a fresh code invalidates any earlier unconsumed one for this phone + purpose
        cls.objects.filter(phone_hash=phone_hash, purpose=purpose, is_used=False).delete()
        code = cls.generate_code()
        otp = cls.objects.create(
            phone_hash=phone_hash,
            code_hash=hash_otp(phone_number, code),
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=valid_minutes),
        )
        return otp, code

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at and self.attempts < 5

    def check_code(self, phone_number: str, raw_code: str) -> bool:
        self.attempts += 1
        self.save(update_fields=['attempts'])
        if not self.is_valid():
            return False
        if hmac.compare_digest(self.code_hash, hash_otp(phone_number, raw_code)):
            self.delete()
            return True
        return False

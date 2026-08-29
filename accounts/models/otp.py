import random
import hashlib

from django.db import models
from django.utils import timezone
from datetime import timedelta


def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class OTP(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        LOGIN = 'login', 'Login'
        PASSWORD_RESET = 'password_reset', 'Password Reset'

    phone_number = models.CharField(max_length=11)
    code_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.REGISTRATION)

    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'purpose']),
        ]

    @staticmethod
    def generate_code() -> str:
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def create_for(cls, phone_number: str, purpose: str = Purpose.REGISTRATION, valid_minutes: int = 5):
        code = cls.generate_code()
        otp = cls.objects.create(
            phone_number=phone_number,
            code_hash=hash_otp(code),
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=valid_minutes),
        )
        return otp, code

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at and self.attempts < 5

    def check_code(self, raw_code: str) -> bool:
        self.attempts += 1
        self.save(update_fields=['attempts'])
        if not self.is_valid():
            return False
        if self.code_hash == hash_otp(raw_code):
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True
        return False
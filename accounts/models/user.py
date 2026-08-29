import hmac
import hashlib

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django_cryptography.fields import encrypt


def hash_nid(nid: str) -> str:
    return hmac.new(
        settings.NID_HASH_SECRET.encode(),
        nid.encode(),
        hashlib.sha256
    ).hexdigest()


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone Number is required')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, password, **extra_fields)


class UserType(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    AGENT = 'agent', 'Agent'
    MERCHANT = 'merchant', 'Merchant'


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True, null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.CUSTOMER)
    phone_number = models.CharField(max_length=11, unique=True)
    national_id_encrypted = encrypt(models.CharField(max_length=24, null=True, blank=True))
    national_id_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    kyc_approved_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def set_national_id(self, raw_nid: str):
        self.national_id_encrypted = raw_nid
        self.national_id_hash = hash_nid(raw_nid)
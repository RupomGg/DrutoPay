import hmac
import hashlib
import random

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

def hash_phone(phone: str)->str:
    return hmac.new(
    settings.PHONE_HASH_SECRET.encode(),
    phone.encode(),
    hashlib.sha256
    ).hexdigest()

def hash_email(email: str) -> str:
    return hmac.new(
        settings.EMAIL_HASH_SECRET.encode(),
        email.lower().encode(),
        hashlib.sha256
        ).hexdigest()

def generate_wallet_number() -> str:
    while True:
        number = ''.join(random.choices('0123456789', k=10))
        if not User.objects.filter(wallet_number=number).exists():
            return number


class UserManager(BaseUserManager):

    def create_user(self, password=None, **extra_fields):
        raw_phone = extra_fields.pop('phone_number_hash', None) or extra_fields.pop('phone_number', None)

        if not raw_phone:
            raise ValueError('Phone Number is required')

        user = self.model(
        phone_number_hash=hash_phone(raw_phone),
        phone_number_encrypted = raw_phone,
        wallet_number = generate_wallet_number(),
         **extra_fields
         )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(password = password, **extra_fields)

    def get_by_natural_key(self, phone_number):
        return self.get(phone_number_hash=hash_phone(phone_number))


class UserType(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    AGENT = 'agent', 'Agent'
    MERCHANT = 'merchant', 'Merchant'


class User(AbstractUser):
    username = None
    email_encrypted = encrypt(models.EmailField(null=True, blank=True))
    email_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    wallet_number = models.CharField(max_length = 15, unique = True, editable = False)
    phone_number_encrypted = encrypt(models.CharField(max_length=11))
    phone_number_hash = models.CharField(max_length=64, unique=True, verbose_name='phone number')
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.CUSTOMER)
    national_id_encrypted = encrypt(models.CharField(max_length=24, null=True, blank=True))
    national_id_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    address_encrypted = encrypt(models.TextField(null=True, blank=True))
    date_of_birth = models.DateField(null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    kyc_approved_at = models.DateTimeField(null=True, blank=True)

    failed_pin_attempts = models.PositiveSmallIntegerField(default=0)
    is_locked = models.BooleanField(default = False)
    locked_until = models.DateTimeField(null = True, blank = True)

    USERNAME_FIELD = 'phone_number_hash'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def set_national_id(self, raw_nid: str):
        self.national_id_encrypted = raw_nid
        self.national_id_hash = hash_nid(raw_nid)

    def set_email(self, raw_email: str):
        self.email_encrypted = raw_email
        self.email_hash = hash_email(raw_email)

    def __str__(self):
        return self.wallet_number
    
    
    
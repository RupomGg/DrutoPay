# DrutoPay

A mobile financial services (MFS) backend, built with Django — inspired by real-world
wallet platforms (bKash/Nagad/UPAY-style cash-in, cash-out, P2P transfer, and merchant
payments). Currently under active development, backend-first.

> Status: **Early development.** Core user/auth foundation is in place. Wallet, ledger,
> and transaction APIs are not built yet.

## Stack

- **Backend:** Django 5+ / Django REST Framework
- **Database:** SQLite (dev) → PostgreSQL (planned for staging/production)
- **Auth:** Custom phone-number-based user model (no username/email login)
- **Sensitive data:** Field-level encryption (`django-cryptography`) for NID; hashed,
  never-reversible storage for passwords and OTP codes

## What's built so far

- **Custom `User` model** (`accounts/models/user.py`)
  - Phone number as the primary login identifier (`USERNAME_FIELD`)
  - Custom `UserManager` (`create_user` / `create_superuser` by phone number)
  - `user_type`: customer / agent / merchant
  - NID stored encrypted at rest (`national_id_encrypted`), plus a separate
    deterministic hash (`national_id_hash`) used only for duplicate-registration
    lookups — the encrypted value is never used for querying
  - KYC status flags: `is_phone_verified`, `is_kyc_verified`, `kyc_approved_at`
- **`OTP` model** (`accounts/models/otp.py`)
  - Short-lived, single-use verification codes (registration / login / password reset)
  - Codes are hashed before storage — the raw code exists only transiently, in memory,
    at generation time
  - Built-in expiry and attempt-limiting (`is_valid`, `check_code`)
- **Django admin** wired up for both models, with sensitive fields marked read-only
  or excluded from raw display

## What's not built yet (in progress / planned)

- [ ] Registration API (`POST /api/auth/register/`)
- [ ] OTP send / verify API
- [ ] Login API (JWT-based, via `djangorestframework-simplejwt`)
- [ ] KYC (NID) submission API
- [ ] Wallet model — double-entry ledger design (no raw balance field; balance derived
  from ledger entries)
- [ ] Cash-in / cash-out / P2P transfer / merchant payment endpoints
- [ ] Idempotency handling on all money-moving endpoints
- [ ] Agent role: float tracking, commission
- [ ] Async jobs (Celery + Redis) for OTP/SMS delivery and settlement jobs
- [ ] Rate limiting on OTP and transaction endpoints
- [ ] Reconciliation job for pending/ambiguous transactions

## Project structure

```
digipay/                  # Django project config (settings, urls, wsgi)
accounts/
  models/
    __init__.py
    user.py                # User model, UserManager, NID hashing helper
    otp.py                 # OTP model, code hashing helper
  admin.py
  migrations/
wallet/                    # scaffolded, models not yet defined
manage.py
requirements.txt
.env                       # not committed — see Environment variables below
```

## Local setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
FIELD_ENCRYPTION_KEY=<generate with the command below>
NID_HASH_SECRET=<any long random string>
```

Generate an encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` and log in with the phone number and password
used at superuser creation.

## Security notes

- Passwords are hashed (PBKDF2), never stored or logged in plain text.
- NID is encrypted at rest, not hashed — encryption is reversible (with the key), which
  is required since KYC review and NID verification need the real value back. A
  separate deterministic hash is kept only for duplicate-detection lookups.
- OTP codes are hashed on storage and never persisted in raw form.
- `.env` (encryption keys, secrets) is excluded from version control.

## Author

Built by [Rupom](mailto:radwanrupom2001@gmail.com) as a learning project and portfolio
piece, aimed at MFS/fintech backend engineering.

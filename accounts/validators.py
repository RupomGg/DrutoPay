import re
from django.core.exceptions import ValidationError

PIN_LENGTH = 6

def validate_pin(value):
    if not re.fullmatch(r'[0-9]+', value):
        raise ValidationError("Pin must be 6 digits")
    if len(value) != PIN_LENGTH:
        raise ValidationError(f"PIN must be exactly {PIN_LENGTH} digits.")

class PinValidator:
    def validate(self, password, user=None):
        validate_pin(password)

    def get_help_text(self):
        return f"Your PIN must be exactly {PIN_LENGTH} digits (0-9 only)."
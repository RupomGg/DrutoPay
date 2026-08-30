from rest_framework import serializers
from .models import User, hash_phone
from .validators import validate_pin


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    pin = serializers.CharField(write_only=True, validators=[validate_pin])

    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError("Enter a valid 11-digit phone number.")
        if User.objects.filter(phone_number_hash=hash_phone(value)).exists():
            raise serializers.ValidationError("An account with this phone number already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['pin'],
        )


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()
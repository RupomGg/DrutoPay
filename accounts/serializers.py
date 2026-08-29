from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators = [validate_password])

    class Meta:
        model = User
        fields = ('phone_number','password')
    
    def validate_phone_number(self,value):
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError("Phone Number must be 11 digits long")
        
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("An account with this phone number already exists")

        return value

    def create(self,validate_data):
        user = User.object.create_user(
            phone_number = validate_data['phone_number'],
            password = validate_data['password']
        )
        return user


from django.utils import timezone
from datetime import timedelta



from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer

from .serializers import RegisterSerializer, VerifyOTPSerializer
from .models import OTP, User, hash_phone

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes = 30)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_phone = serializer.validated_data['phone_number']
        user = serializer.save()

        otp, code = OTP.create_for(raw_phone, purpose=OTP.Purpose.REGISTRATION)
        print(f"[DEV] OTP for {raw_phone}: {code}")

        return Response(
            {"message": "Registration successful. OTP sent to your phone number.", "wallet_number": user.wallet_number},
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        otp = OTP.objects.filter(
            phone_hash=hash_phone(phone_number),
            purpose=OTP.Purpose.REGISTRATION,
            is_used=False,
        ).order_by('-created_at').first()

        if not otp or not otp.check_code(phone_number, code):
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(phone_number_hash=hash_phone(phone_number))
        user.is_phone_verified = True
        user.save(update_fields=['is_phone_verified'])

        return Response({"message": "Phone number verified successfully."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]


    def post(self,request):
        serializer = LoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        phone_number = serializer.validated_data['phone_number']
        pin = serializer.validated_data['pin']

        try:
            user = User.objects.get(phone_number_hash = hash_phone(phone_number))
        except User.DoesNotExist:
            return Response({"error": "Invalid Phone number or Pin"}, status = status.HTTP_401_UNAUTHORIZED)

        
        if user.is_locked:
            if user.locked_until and timezone.now() < user.locked_until:
                return Response({"error": "Account temporarily locked. Try again later"}, status = status.HTTP_423_LOCKED)
            user.is_locked = False
            user.failed_pin_attempts = 0


        if not user.is_phone_verified:
            return Response({"error": "Phone number not verified yet"}, status = status.HTTP_403_FORBIDDEN)
        
        if not user.check_password(pin):
            user.failed_pin_attempts += 1

            if user.failed_pin_attempts >= MAX_FAILED_ATTEMPTS:
                user.is_locked = True
                user.locked_until = timezone.now() + LOCKOUT_DURATION
            
            user.save(update_fields = ['failed_pin_attempts', 'is_locked', 'locked_until'])

            return Response({"error": "Invalid phone numer or PIN"}, status = status.HTTP_401_UNAUTHORIZED)

        user.failed_pin_attempts = 0
        user.save(update_fields=['failed_pin_attempts'])

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "wallet_number": user.wallet_number,
        })

            
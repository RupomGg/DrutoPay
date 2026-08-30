from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .serializers import RegisterSerializer, VerifyOTPSerializer
from .models import OTP, User, hash_phone


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
            phone_number=phone_number,
            purpose=OTP.Purpose.REGISTRATION,
            is_used=False,
        ).order_by('-created_at').first()

        if not otp or not otp.check_code(code):
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(phone_number_hash=hash_phone(phone_number))
        user.is_phone_verified = True
        user.save(update_fields=['is_phone_verified'])

        return Response({"message": "Phone number verified successfully."}, status=status.HTTP_200_OK)
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .serializers import RegisterSerializer
from .models import OTP


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp, code = OTP.create_for(user.phone_number, purpose=OTP.Purpose.REGISTRATION)

        # Dev-only: print the code so you can test without a real SMS gateway
        print(f"[DEV] OTP for {user.phone_number}: {code}")

        return Response(
            {"message": "Registration successful. OTP sent to your phone number."},
            status=status.HTTP_201_CREATED,
        )
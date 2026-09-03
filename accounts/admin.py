from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP

# Register your models here.

class CustomUserAdmin(UserAdmin):
    model = User

    @admin.display(description='phone')
    def phone_masked(self,obj):
        p = obj.phone_number_encrypted or ""
        return f"{p[:3]}****{p[-2:]}" if len(p) >= 5 else "****"

    list_display = ['wallet_number', 'phone_masked', 'user_type', 'is_phone_verified', 'is_kyc_verified', 'is_staff']
    ordering = ('wallet_number',)
    readonly_fields = ('wallet_number', 'phone_number_hash', 'national_id_hash')

    fieldsets = (
        (None, {'fields': ('wallet_number', 'phone_number_encrypted', 'phone_number_hash', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'date_of_birth')}),
        ('KYC', {'fields': ('national_id_encrypted', 'national_id_hash', 'is_kyc_verified', 'kyc_approved_at')}),
        ('Verification', {'fields': ('is_phone_verified',)}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('phone_number_encrypted', 'password1', 'password2')}),
    )
    search_fields = ('wallet_number',)


admin.site.register(User, CustomUserAdmin)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('purpose', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('phone_hash',)
    readonly_fields = ('phone_hash', 'code_hash', 'created_at')
    ordering = ('-created_at',)

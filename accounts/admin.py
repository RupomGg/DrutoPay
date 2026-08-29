from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP

# Register your models here.

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['phone_number','user_type','is_phone_verified','is_kyc_verified','is_staff']
    ordering = ('phone_number',)

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'date_of_birth')}),
        ('KYC', {'fields': ('national_id_encrypted', 'is_kyc_verified', 'kyc_approved_at')}),
        ('Verification', {'fields': ('is_phone_verified',)}),
        ('Permissions', {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('phone_number', 'password1', 'password2')}),
    )
    search_fields = ('phone_number', 'national_id_hash')


admin.site.register(User, CustomUserAdmin)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'purpose', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('phone_number',)
    readonly_fields = ('code_hash', 'created_at')
    ordering = ('-created_at',)

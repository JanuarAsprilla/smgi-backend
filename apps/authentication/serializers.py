"""
SMGI Backend - Authentication Serializers
Sistema de Monitoreo Geoespacial Inteligente
Serializers profesionales para autenticación
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.authentication.models import (
    User, UserRole, Department, 
    PasswordResetToken, EmailVerificationToken,
    APIKey, LoginAttempt
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'document_type', 'document_number', 'phone', 'mobile',
            'organization', 'department', 'position', 'role',
            'email_verified', 'two_factor_enabled', 'language',
            'timezone', 'last_login', 'date_joined', 'is_active'
        ]
        read_only_fields = ['id', 'email_verified', 'last_login', 'date_joined']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'document_type', 'document_number',
            'phone', 'mobile', 'organization', 'department', 'position'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': _('Passwords do not match')
            })
        
        # Check if email already exists
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                'email': _('User with this email already exists')
            })
        
        # Check if document number already exists
        if User.objects.filter(document_number=attrs['document_number']).exists():
            raise serializers.ValidationError({
                'document_number': _('User with this document number already exists')
            })
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            role=UserRole.VIEWER,  # Default role
            **validated_data
        )
        
        # Generate email verification token
        from apps.authentication.tasks import send_verification_email
        send_verification_email.delay(user.id)
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'mobile',
            'organization', 'department', 'position',
            'language', 'timezone', 'notification_preferences'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password': _('Passwords do not match')
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_('Current password is incorrect'))
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if user exists or not
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password': _('Passwords do not match')
            })
        
        # Validate token
        try:
            reset_token = PasswordResetToken.objects.get(token=attrs['token'])
            if not reset_token.is_valid():
                raise serializers.ValidationError({
                    'token': _('Token is invalid or has expired')
                })
            attrs['reset_token'] = reset_token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({
                'token': _('Invalid token')
            })
        
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    
    token = serializers.CharField(required=True)
    
    def validate_token(self, value):
        try:
            verification_token = EmailVerificationToken.objects.get(token=value)
            if not verification_token.is_valid():
                raise serializers.ValidationError(_('Token is invalid or has expired'))
            self.context['verification_token'] = verification_token
        except EmailVerificationToken.DoesNotExist:
            raise serializers.ValidationError(_('Invalid token'))
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user data"""
    
    def validate(self, attrs):
        # Get IP address from request
        request = self.context.get('request')
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        try:
            # Attempt authentication
            data = super().validate(attrs)
            
            # Get user
            user = self.user
            
            # Check if account is locked
            if user.is_account_locked():
                raise serializers.ValidationError({
                    'detail': _('Account is temporarily locked. Please try again later.')
                })
            
            # Check if email is verified (optional - can be disabled)
            if not user.email_verified:
                raise serializers.ValidationError({
                    'detail': _('Please verify your email address before logging in.')
                })
            
            # Reset failed login attempts on successful login
            user.reset_failed_login()
            
            # Update last login IP
            user.last_login_ip = ip_address
            user.save(update_fields=['last_login_ip'])
            
            # Record successful login attempt
            LoginAttempt.objects.create(
                user=user,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            
            # Add custom claims to token
            refresh = RefreshToken.for_user(user)
            refresh['email'] = user.email
            refresh['role'] = user.role
            refresh['full_name'] = user.get_full_name()
            
            data['user'] = UserSerializer(user).data
            
            return data
            
        except serializers.ValidationError:
            # Record failed login attempt
            email = attrs.get('email', '')
            
            try:
                user = User.objects.get(email=email)
                user.increment_failed_login()
                
                LoginAttempt.objects.create(
                    user=user,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason='invalid_credentials'
                )
            except User.DoesNotExist:
                LoginAttempt.objects.create(
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason='user_not_found'
                )
            
            raise


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API Keys"""
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key', 'is_active', 'expires_at',
            'last_used', 'usage_count', 'allowed_ips',
            'rate_limit', 'scopes', 'created', 'modified'
        ]
        read_only_fields = ['id', 'key', 'last_used', 'usage_count', 'created', 'modified']
    
    def create(self, validated_data):
        import secrets
        
        # Generate secure API key
        api_key = f"smgi_{secrets.token_urlsafe(32)}"
        validated_data['key'] = api_key
        validated_data['user'] = self.context['request'].user
        
        return super().create(validated_data)


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Serializer for login attempts (admin view)"""
    
    class Meta:
        model = LoginAttempt
        fields = [
            'id', 'user', 'email', 'ip_address', 'user_agent',
            'success', 'failure_reason', 'country', 'city', 'created'
        ]
        read_only_fields = fields
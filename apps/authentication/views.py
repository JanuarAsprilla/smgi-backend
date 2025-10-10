"""
SMGI Backend - Authentication Views
Sistema de Monitoreo Geoespacial Inteligente
Views profesionales para autenticación y gestión de usuarios
"""
from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.authentication.models import User, APIKey, LoginAttempt
from apps.authentication.serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, EmailVerificationSerializer,
    CustomTokenObtainPairSerializer, APIKeySerializer, LoginAttemptSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with additional user data"""
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=['Authentication'],
    summary='User Registration',
    description='Register a new user account',
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description='Validation errors')
    }
)
class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': _('Registration successful. Please check your email to verify your account.'),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Authentication'],
    summary='Logout',
    description='Logout user and blacklist refresh token',
    responses={
        200: OpenApiResponse(description='Successfully logged out'),
        400: OpenApiResponse(description='Invalid token')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint - blacklists refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'error': _('Refresh token is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        # Logout Django session
        logout(request)
        
        return Response({
            'message': _('Successfully logged out')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': _('Invalid token')
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Get Current User Profile',
    description='Get authenticated user profile information',
    responses={200: UserSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """Get current user profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    tags=['Authentication'],
    summary='Update User Profile',
    description='Update authenticated user profile',
    responses={
        200: UserSerializer,
        400: OpenApiResponse(description='Validation errors')
    }
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """Update user profile"""
    serializer = UserUpdateSerializer(
        request.user,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(UserSerializer(request.user).data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Change Password',
    description='Change user password',
    responses={
        200: OpenApiResponse(description='Password changed successfully'),
        400: OpenApiResponse(description='Validation errors')
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change password endpoint"""
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.save()
        
        # Invalidate all existing tokens
        # User will need to login again
        
        return Response({
            'message': _('Password changed successfully. Please login again.')
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Request Password Reset',
    description='Request password reset email',
    responses={
        200: OpenApiResponse(description='Reset email sent if account exists'),
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    """Request password reset"""
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            # Generate reset token
            from apps.authentication.tasks import send_password_reset_email
            send_password_reset_email.delay(user.id)
            
        except User.DoesNotExist:
            # Don't reveal if user exists or not (security)
            pass
        
        return Response({
            'message': _('If an account exists with this email, a password reset link has been sent.')
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Confirm Password Reset',
    description='Reset password with token',
    responses={
        200: OpenApiResponse(description='Password reset successful'),
        400: OpenApiResponse(description='Invalid token or validation errors')
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    """Confirm password reset with token"""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        reset_token = serializer.validated_data['reset_token']
        new_password = serializer.validated_data['new_password']
        
        # Reset password
        user = reset_token.user
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.must_change_password = False
        user.save()
        
        # Mark token as used
        reset_token.use_token()
        
        return Response({
            'message': _('Password has been reset successfully. You can now login with your new password.')
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Verify Email',
    description='Verify email address with token',
    responses={
        200: OpenApiResponse(description='Email verified successfully'),
        400: OpenApiResponse(description='Invalid token')
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def email_verification_view(request):
    """Verify email with token"""
    serializer = EmailVerificationSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        verification_token = request.data.get('verification_token')
        verification_token.verify_email()
        
        return Response({
            'message': _('Email verified successfully. You can now login.')
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    summary='Resend Verification Email',
    description='Resend email verification link',
    responses={
        200: OpenApiResponse(description='Verification email sent'),
        400: OpenApiResponse(description='Email already verified or user not found')
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email_view(request):
    """Resend verification email"""
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': _('Email is required')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email, is_active=True)
        
        if user.email_verified:
            return Response({
                'message': _('Email is already verified')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Send verification email
        from apps.authentication.tasks import send_verification_email
        send_verification_email.delay(user.id)
        
        return Response({
            'message': _('Verification email has been sent')
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': _('User not found')
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(tags=['Users'])
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users (Admin only)
    """
    queryset = User.objects.filter(is_removed=False)
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['role', 'is_active', 'email_verified', 'department']
    search_fields = ['email', 'first_name', 'last_name', 'document_number']
    ordering_fields = ['created', 'last_login', 'email']
    ordering = ['-created']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate user account"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({
            'message': _('User activated successfully')
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate user account"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({
            'message': _('User deactivated successfully')
        })
    
    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock user account"""
        user = self.get_object()
        user.unlock_account()
        return Response({
            'message': _('User account unlocked successfully')
        })


@extend_schema(tags=['API Keys'])
class APIKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing API keys
    """
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own API keys
        if self.request.user.is_staff:
            return APIKey.objects.filter(is_removed=False)
        return APIKey.objects.filter(
            user=self.request.user,
            is_removed=False
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke API key"""
        api_key = self.get_object()
        api_key.revoke()
        return Response({
            'message': _('API key revoked successfully')
        })
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate API key"""
        import secrets
        api_key = self.get_object()
        api_key.key = f"smgi_{secrets.token_urlsafe(32)}"
        api_key.is_active = True
        api_key.usage_count = 0
        api_key.save()
        return Response(APIKeySerializer(api_key).data)


@extend_schema(tags=['Authentication'])
class LoginAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing login attempts (Admin only)
    """
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['success', 'email', 'ip_address']
    ordering = ['-created']
    
    @action(detail=False, methods=['get'])
    def recent_failures(self, request):
        """Get recent failed login attempts"""
        failures = self.get_queryset().filter(
            success=False,
            created__gte=timezone.now() - timezone.timedelta(hours=24)
        )
        serializer = self.get_serializer(failures, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def suspicious_activity(self, request):
        """Get suspicious login activity"""
        from django.db.models import Count
        
        # Find IPs with multiple failed attempts
        suspicious_ips = LoginAttempt.objects.filter(
            success=False,
            created__gte=timezone.now() - timezone.timedelta(hours=1)
        ).values('ip_address').annotate(
            attempt_count=Count('id')
        ).filter(attempt_count__gte=5)
        
        return Response({
            'suspicious_ips': list(suspicious_ips),
            'count': len(suspicious_ips)
        })
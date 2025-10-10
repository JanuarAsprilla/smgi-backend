"""
SMGI Backend - Authentication URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.authentication import views

# Create router for viewsets
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'api-keys', views.APIKeyViewSet, basename='apikey')
router.register(r'login-attempts', views.LoginAttemptViewSet, basename='loginattempt')

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile management
    path('profile/', views.current_user_view, name='current-user'),
    path('profile/update/', views.update_profile_view, name='update-profile'),
    path('profile/change-password/', views.change_password_view, name='change-password'),
    
    # Password reset
    path('password-reset/', views.password_reset_request_view, name='password-reset-request'),
    path('password-reset/confirm/', views.password_reset_confirm_view, name='password-reset-confirm'),
    
    # Email verification
    path('verify-email/', views.email_verification_view, name='verify-email'),
    path('resend-verification/', views.resend_verification_email_view, name='resend-verification'),
    
    # ViewSet routes
    path('', include(router.urls)),
]
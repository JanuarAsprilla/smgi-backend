"""
Vistas para gestión de usuarios
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from itsdangerous import URLSafeTimedSerializer

from .models import UserProfile, Role, Area, ActivityLog
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserApprovalSerializer,
    RoleSerializer,
    AreaSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de usuarios"""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Permitir registro sin autenticación"""
        if self.action == 'register':
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """
        Registro de nuevo usuario
        POST /api/v1/users/register/
        """
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generar token de verificación
            token = self._generate_verification_token(user.email)
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            
            # Enviar email de verificación
            self._send_verification_email(user, verification_url)
            
            # Notificar a administradores sobre nueva solicitud
            self._notify_admins_new_user(user)
            
            return Response({
                'message': 'Registro exitoso. Revisa tu email para verificar tu cuenta.',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify_email(self, request):
        """
        Verificar email con token
        POST /api/v1/users/verify-email/
        """
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'error': 'Token requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = self._verify_token(token)
        
        if not email:
            return Response(
                {'error': 'Token inválido o expirado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            user.profile.email_verified = True
            user.profile.save()
            
            return Response({
                'message': 'Email verificado exitosamente. Tu cuenta será revisada por un administrador.'
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """
        Listar usuarios pendientes de aprobación
        GET /api/v1/users/pending-approvals/
        Solo para admins
        """
        # Verificar que sea admin
        if not request.user.profile.has_permission('can_approve_users'):
            return Response(
                {'error': 'No tienes permisos para ver solicitudes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_users = User.objects.filter(
            profile__approval_status='pending'
        ).select_related('profile', 'profile__role', 'profile__area')
        
        serializer = UserSerializer(pending_users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve_reject(self, request, pk=None):
        """
        Aprobar o rechazar usuario
        POST /api/v1/users/{id}/approve-reject/
        """
        user = self.get_object()
        
        # Verificar permisos
        if not request.user.profile.has_permission('can_approve_users'):
            return Response(
                {'error': 'No tienes permisos para aprobar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserApprovalSerializer(data=request.data)
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            
            if action == 'approve':
                # Aprobar usuario
                role_id = serializer.validated_data['role_id']
                area_id = serializer.validated_data.get('area_id')
                
                user.is_active = True
                user.save()
                
                profile = user.profile
                profile.approval_status = 'approved'
                profile.role_id = role_id
                profile.approved_by = request.user
                profile.approved_at = timezone.now()
                
                if area_id:
                    profile.area_id = area_id
                
                profile.save()
                
                # Enviar email de aprobación
                self._send_approval_email(user)
                
                # Log
                ActivityLog.objects.create(
                    user=request.user,
                    action='approve_user',
                    description=f'Aprobó al usuario {user.username}',
                    metadata={'approved_user_id': user.id}
                )
                
                return Response({
                    'message': f'Usuario {user.username} aprobado exitosamente'
                })
            
            else:  # reject
                rejection_reason = serializer.validated_data.get('rejection_reason', '')
                
                profile = user.profile
                profile.approval_status = 'rejected'
                profile.rejection_reason = rejection_reason
                profile.save()
                
                # Enviar email de rechazo
                self._send_rejection_email(user, rejection_reason)
                
                # Log
                ActivityLog.objects.create(
                    user=request.user,
                    action='reject_user',
                    description=f'Rechazó al usuario {user.username}',
                    metadata={'rejected_user_id': user.id, 'reason': rejection_reason}
                )
                
                return Response({
                    'message': f'Usuario {user.username} rechazado'
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener perfil del usuario actual"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    # Métodos auxiliares
    def _generate_verification_token(self, email):
        """Generar token de verificación"""
        serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
        return serializer.dumps(email, salt='email-verification')
    
    def _verify_token(self, token, max_age=86400):
        """Verificar token (expira en 24 horas por defecto)"""
        serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
        try:
            email = serializer.loads(token, salt='email-verification', max_age=max_age)
            return email
        except:
            return None
    
    def _send_verification_email(self, user, verification_url):
        """Enviar email de verificación"""
        subject = 'Verifica tu cuenta SMGI'
        message = f'''
Hola {user.first_name or user.username},

Gracias por registrarte en SMGI.

Para verificar tu cuenta, haz click en el siguiente enlace:
{verification_url}

Este enlace expira en 24 horas.

Si no solicitaste esta cuenta, puedes ignorar este mensaje.

Saludos,
Equipo SMGI
'''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    
    def _send_approval_email(self, user):
        """Enviar email de aprobación"""
        subject = 'Tu cuenta SMGI ha sido aprobada'
        message = f'''
Hola {user.first_name or user.username},

¡Buenas noticias! Tu cuenta ha sido aprobada.

Ya puedes iniciar sesión en: {settings.FRONTEND_URL}/login

Rol asignado: {user.profile.role.name}
{f"Área: {user.profile.area.name}" if user.profile.area else ""}

Saludos,
Equipo SMGI
'''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    
    def _send_rejection_email(self, user, reason):
        """Enviar email de rechazo"""
        subject = 'Actualización sobre tu solicitud SMGI'
        message = f'''
Hola {user.first_name or user.username},

Lamentamos informarte que tu solicitud de acceso no ha sido aprobada.

Motivo: {reason}

Si tienes preguntas, contacta al administrador del sistema.

Saludos,
Equipo SMGI
'''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    
    def _notify_admins_new_user(self, user):
        """Notificar a administradores sobre nuevo usuario"""
        # Obtener todos los usuarios con permiso de aprobación
        admin_users = User.objects.filter(
            profile__role__can_approve_users=True,
            is_active=True
        )
        
        admin_emails = [u.email for u in admin_users if u.email]
        
        if admin_emails:
            subject = f'Nueva solicitud de acceso: {user.username}'
            message = f'''
Nueva solicitud de acceso al sistema SMGI:

Usuario: {user.username}
Nombre: {user.first_name} {user.last_name}
Email: {user.email}
Organización: {user.profile.organization}
Rol solicitado: {user.profile.role.name if user.profile.role else 'N/A'}
Justificación: {user.profile.access_justification}

Revisa y aprueba en: {settings.FRONTEND_URL}/admin/users

Saludos,
Sistema SMGI
'''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=True,
            )


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para roles (solo lectura)"""
    queryset = Role.objects.filter(is_system_role=True)
    serializer_class = RoleSerializer
    permission_classes = [AllowAny]  # Permitir ver roles para registro


class AreaViewSet(viewsets.ModelViewSet):
    """ViewSet para áreas"""
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]

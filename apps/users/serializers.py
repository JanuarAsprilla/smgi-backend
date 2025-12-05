"""
Serializers para autenticación y registro de usuarios
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, Role, Area

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'role_type', 'description']


class AreaSerializer(serializers.ModelSerializer):
    admin_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Area
        fields = ['id', 'name', 'description', 'privacy', 'admin_count', 'member_count', 'created_at']
    
    def get_admin_count(self, obj) -> int:
        return obj.admins.count()
    
    def get_member_count(self, obj) -> int:
        return obj.members.count()


class UserProfileSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True, required=False)
    area = AreaSerializer(read_only=True)
    area_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = UserProfile
        fields = [
            'phone', 'organization', 'department', 'position',
            'role', 'role_id', 'area', 'area_id',
            'approval_status', 'access_justification',
            'email_notifications', 'sms_notifications', 'push_notifications',
            'notify_analysis_complete', 'notify_analysis_failed',
            'notify_alerts_critical', 'notify_alerts_medium', 'notify_alerts_low',
            'notify_resource_shared', 'notify_weekly_report',
            'two_factor_enabled', 'last_activity'
        ]
        read_only_fields = ['approval_status', 'last_activity']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer para registro de nuevos usuarios"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    # Campos del perfil
    phone = serializers.CharField(required=False, allow_blank=True)
    organization = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)
    access_justification = serializers.CharField(required=True)
    requested_role_id = serializers.IntegerField(required=True)
    requested_area_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name',
            'phone', 'organization', 'department', 'position',
            'access_justification', 'requested_role_id', 'requested_area_id'
        ]
    
    def validate(self, data):
        """Validaciones"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        
        # Validar que el email sea único
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Este email ya está registrado"})
        
        # Validar que el rol exista
        try:
            role = Role.objects.get(id=data['requested_role_id'])
            # No permitir registro directo como super admin
            if role.role_type == 'super_admin':
                raise serializers.ValidationError({"requested_role_id": "No puedes solicitar este rol"})
        except Role.DoesNotExist:
            raise serializers.ValidationError({"requested_role_id": "Rol no válido"})
        
        # Validar área si se proporciona
        if data.get('requested_area_id'):
            if not Area.objects.filter(id=data['requested_area_id']).exists():
                raise serializers.ValidationError({"requested_area_id": "Área no válida"})
        
        return data
    
    def create(self, validated_data):
        """Crear usuario y perfil"""
        # Extraer datos del perfil
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        phone = validated_data.pop('phone', '')
        organization = validated_data.pop('organization', '')
        department = validated_data.pop('department', '')
        position = validated_data.pop('position', '')
        access_justification = validated_data.pop('access_justification', '')
        requested_role_id = validated_data.pop('requested_role_id')
        requested_area_id = validated_data.pop('requested_area_id', None)
        
        # Crear usuario (inactivo hasta aprobación)
        user = User.objects.create_user(
            **validated_data,
            password=password,
            is_active=False  # Inactivo hasta verificar email y aprobar
        )
        
        # Actualizar perfil
        profile = user.profile
        profile.phone = phone
        profile.organization = organization
        profile.department = department
        profile.position = position
        profile.access_justification = access_justification
        profile.approval_status = 'pending'
        
        # Asignar rol solicitado (se confirmará en aprobación)
        profile.role_id = requested_role_id
        
        # Asignar área si se proporciona
        if requested_area_id:
            profile.area_id = requested_area_id
        
        profile.save()
        
        return user


class UserApprovalSerializer(serializers.Serializer):
    """Serializer para aprobar/rechazar usuarios"""
    
    ACTION_CHOICES = [
        ('approve', 'Aprobar'),
        ('reject', 'Rechazar'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    role_id = serializers.IntegerField(required=False)
    area_id = serializers.IntegerField(required=False, allow_null=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                "rejection_reason": "Debes proporcionar un motivo de rechazo"
            })
        
        if data['action'] == 'approve':
            if not data.get('role_id'):
                raise serializers.ValidationError({
                    "role_id": "Debes asignar un rol al aprobar"
                })
            
            # Validar que el rol exista
            if not Role.objects.filter(id=data['role_id']).exists():
                raise serializers.ValidationError({
                    "role_id": "Rol no válido"
                })
        
        return data

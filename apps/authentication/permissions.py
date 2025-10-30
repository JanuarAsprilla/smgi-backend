# apps/authentication/permissions.py
"""
SMGI Backend - Authentication Permissions
Sistema de Monitoreo Geoespacial Inteligente
Permisos personalizados para el sistema de autenticación y autorización
"""
import logging
from rest_framework import permissions
from rest_framework.permissions import BasePermission, IsAuthenticated, IsAdminUser, AllowAny
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import User, UserRole, UserPermission

logger = logging.getLogger('apps.authentication.permissions')


class IsOwnerOrReadOnly(BasePermission):
    """
    Permite a los propietarios editar objetos, a otros solo lectura.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier solicitud
        if request.method in permissions.SAFE_METHODS:
            return True

        # Permisos de escritura solo para el propietario del objeto
        return obj.owner == request.user


class IsAdminOrReadOnly(BasePermission):
    """
    Permite a los administradores editar objetos, a otros solo lectura.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        # Permisos de lectura para cualquier usuario autenticado
        if request.method in permissions.SAFE_METHODS:
            return True

        # Permisos de escritura solo para administradores
        return request.user and request.user.is_staff


class IsStaffOrReadOnly(BasePermission):
    """
    Permite a los staff editar objetos, a otros solo lectura.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        # Permisos de lectura para cualquier usuario
        if request.method in permissions.SAFE_METHODS:
            return True

        # Permisos de escritura solo para staff
        return request.user and request.user.is_staff


class IsAuthenticatedAndActive(BasePermission):
    """
    Permite acceso solo a usuarios autenticados y activos.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active
        )


class IsSuperUser(BasePermission):
    """
    Permite acceso solo a superusuarios.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsAdminUser(BasePermission):
    """
    Permite acceso solo a usuarios con rol ADMIN.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.ADMIN
        )


class IsStaffUser(BasePermission):
    """
    Permite acceso solo a usuarios con rol STAFF.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.STAFF
        )


class IsRegularUser(BasePermission):
    """
    Permite acceso solo a usuarios con rol USER.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.USER
        )


class IsGuestUser(BasePermission):
    """
    Permite acceso solo a usuarios con rol GUEST.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.GUEST
        )


class HasPermission(BasePermission):
    """
    Permite acceso basado en permisos específicos.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        # Obtener el permiso requerido desde la vista o el método
        required_permission = getattr(view, 'required_permission', None)
        if not required_permission:
            # Si no hay permiso requerido, denegar acceso
            return False

        # Verificar si el usuario tiene el permiso
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_perm(required_permission)
        )


class HasRole(BasePermission):
    """
    Permite acceso basado en roles específicos.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        # Obtener el rol requerido desde la vista o el método
        required_role = getattr(view, 'required_role', None)
        if not required_role:
            # Si no hay rol requerido, denegar acceso
            return False

        # Verificar si el usuario tiene el rol
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == required_role
        )


class HasGroup(BasePermission):
    """
    Permite acceso basado en grupos específicos.
    """
    message = _('You do not have permission to perform this action.')

    def has_permission(self, request, view):
        # Obtener el grupo requerido desde la vista o el método
        required_group = getattr(view, 'required_group', None)
        if not required_group:
            # Si no hay grupo requerido, denegar acceso
            return False

        # Verificar si el usuario pertenece al grupo
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name=required_group).exists()
        )


class HasObjectPermission(BasePermission):
    """
    Permite acceso basado en permisos específicos sobre un objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Obtener el permiso requerido desde la vista o el método
        required_permission = getattr(view, 'required_object_permission', None)
        if not required_permission:
            # Si no hay permiso requerido, denegar acceso
            return False

        # Verificar si el usuario tiene el permiso sobre el objeto
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_perm(required_permission, obj)
        )


class HasObjectRole(BasePermission):
    """
    Permite acceso basado en roles específicos sobre un objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Obtener el rol requerido desde la vista o el método
        required_role = getattr(view, 'required_object_role', None)
        if not required_role:
            # Si no hay rol requerido, denegar acceso
            return False

        # Verificar si el usuario tiene el rol sobre el objeto
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == required_role and
            obj.owner == request.user # Ejemplo: el rol debe ser el propietario
        )


class HasObjectGroup(BasePermission):
    """
    Permite acceso basado en grupos específicos sobre un objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Obtener el grupo requerido desde la vista o el método
        required_group = getattr(view, 'required_object_group', None)
        if not required_group:
            # Si no hay grupo requerido, denegar acceso
            return False

        # Verificar si el usuario pertenece al grupo sobre el objeto
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name=required_group).exists() and
            obj.group == request.user.groups.get(name=required_group) # Ejemplo: el grupo debe ser el mismo
        )


class IsOwner(BasePermission):
    """
    Permite acceso solo al propietario del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario del objeto
        return obj.owner == request.user


class IsAssignedTo(BasePermission):
    """
    Permite acceso solo al usuario asignado al objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario está asignado al objeto
        return obj.assigned_to == request.user


class IsCreator(BasePermission):
    """
    Permite acceso solo al creador del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el creador del objeto
        return obj.created_by == request.user


class IsModifier(BasePermission):
    """
    Permite acceso solo al último modificador del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el último modificador del objeto
        return obj.modified_by == request.user


class IsApprover(BasePermission):
    """
    Permite acceso solo al aprobador del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el aprobador del objeto
        return obj.approved_by == request.user


class IsReviewer(BasePermission):
    """
    Permite acceso solo al revisor del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el revisor del objeto
        return obj.reviewed_by == request.user


class IsPublisher(BasePermission):
    """
    Permite acceso solo al publicador del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el publicador del objeto
        return obj.published_by == request.user


class IsSubscriber(BasePermission):
    """
    Permite acceso solo a subscriptores del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es subscriptor del objeto
        return request.user in obj.subscribers.all()


class IsCollaborator(BasePermission):
    """
    Permite acceso solo a colaboradores del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es colaborador del objeto
        return request.user in obj.collaborators.all()


class IsContributor(BasePermission):
    """
    Permite acceso solo a contribuyentes del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es contribuyente del objeto
        return request.user in obj.contributors.all()


class IsParticipant(BasePermission):
    """
    Permite acceso solo a participantes del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es participante del objeto
        return request.user in obj.participants.all()


class IsMember(BasePermission):
    """
    Permite acceso solo a miembros del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es miembro del objeto
        return request.user in obj.members.all()


class IsLeader(BasePermission):
    """
    Permite acceso solo al líder del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el líder del objeto
        return obj.leader == request.user


class IsManager(BasePermission):
    """
    Permite acceso solo al gerente del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el gerente del objeto
        return obj.manager == request.user


class IsDirector(BasePermission):
    """
    Permite acceso solo al director del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el director del objeto
        return obj.director == request.user


class IsCoordinator(BasePermission):
    """
    Permite acceso solo al coordinador del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el coordinador del objeto
        return obj.coordinator == request.user


class IsSupervisor(BasePermission):
    """
    Permite acceso solo al supervisor del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el supervisor del objeto
        return obj.supervisor == request.user


class IsInspector(BasePermission):
    """
    Permite acceso solo al inspector del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el inspector del objeto
        return obj.inspector == request.user


class IsAuditor(BasePermission):
    """
    Permite acceso solo al auditor del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el auditor del objeto
        return obj.auditor == request.user


class IsComplianceOfficer(BasePermission):
    """
    Permite acceso solo al oficial de cumplimiento del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el oficial de cumplimiento del objeto
        return obj.compliance_officer == request.user


class IsSecurityOfficer(BasePermission):
    """
    Permite acceso solo al oficial de seguridad del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el oficial de seguridad del objeto
        return obj.security_officer == request.user


class IsPrivacyOfficer(BasePermission):
    """
    Permite acceso solo al oficial de privacidad del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el oficial de privacidad del objeto
        return obj.privacy_officer == request.user


class IsDataSteward(BasePermission):
    """
    Permite acceso solo al steward de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el steward de datos del objeto
        return obj.data_steward == request.user


class IsDataCustodian(BasePermission):
    """
    Permite acceso solo al custodio de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el custodio de datos del objeto
        return obj.data_custodian == request.user


class IsDataOwner(BasePermission):
    """
    Permite acceso solo al propietario de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario de datos del objeto
        return obj.data_owner == request.user


class IsDataProcessor(BasePermission):
    """
    Permite acceso solo al procesador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el procesador de datos del objeto
        return obj.data_processor == request.user


class IsDataController(BasePermission):
    """
    Permite acceso solo al controlador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el controlador de datos del objeto
        return obj.data_controller == request.user


class IsDataSubject(BasePermission):
    """
    Permite acceso solo al sujeto de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el sujeto de datos del objeto
        return obj.data_subject == request.user


class IsDataRecipient(BasePermission):
    """
    Permite acceso solo al receptor de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el receptor de datos del objeto
        return obj.data_recipient == request.user


class IsDataSender(BasePermission):
    """
    Permite acceso solo al remitente de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el remitente de datos del objeto
        return obj.data_sender == request.user


class IsDataImporter(BasePermission):
    """
    Permite acceso solo al importador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el importador de datos del objeto
        return obj.data_importer == request.user


class IsDataExporter(BasePermission):
    """
    Permite acceso solo al exportador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el exportador de datos del objeto
        return obj.data_exporter == request.user


class IsDataArchiver(BasePermission):
    """
    Permite acceso solo al archivador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el archivador de datos del objeto
        return obj.data_archiver == request.user


class IsDataRestorer(BasePermission):
    """
    Permite acceso solo al restaurador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el restaurador de datos del objeto
        return obj.data_restorer == request.user


class IsDataDeleter(BasePermission):
    """
    Permite acceso solo al eliminador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el eliminador de datos del objeto
        return obj.data_deleter == request.user


class IsDataPurger(BasePermission):
    """
    Permite acceso solo al purgador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el purgador de datos del objeto
        return obj.data_purger == request.user


class IsDataValidator(BasePermission):
    """
    Permite acceso solo al validador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el validador de datos del objeto
        return obj.data_validator == request.user


class IsDataVerifier(BasePermission):
    """
    Permite acceso solo al verificador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el verificador de datos del objeto
        return obj.data_verifier == request.user


class IsDataClassifier(BasePermission):
    """
    Permite acceso solo al clasificador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el clasificador de datos del objeto
        return obj.data_classifier == request.user


class IsDataLabeler(BasePermission):
    """
    Permite acceso solo al etiquetador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el etiquetador de datos del objeto
        return obj.data_labeler == request.user


class IsDataTagger(BasePermission):
    """
    Permite acceso solo al tagger de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el tagger de datos del objeto
        return obj.data_tagger == request.user


class IsDataAnnotator(BasePermission):
    """
    Permite acceso solo al anotador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el anotador de datos del objeto
        return obj.data_annotator == request.user


class IsDataCurator(BasePermission):
    """
    Permite acceso solo al curador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el curador de datos del objeto
        return obj.data_curator == request.user


class IsDataGovernor(BasePermission):
    """
    Permite acceso solo al gobernador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el gobernador de datos del objeto
        return obj.data_governor == request.user


class IsDataAdministrator(BasePermission):
    """
    Permite acceso solo al administrador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el administrador de datos del objeto
        return obj.data_administrator == request.user


class IsDataOperator(BasePermission):
    """
    Permite acceso solo al operador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el operador de datos del objeto
        return obj.data_operator == request.user


class IsDataTechnician(BasePermission):
    """
    Permite acceso solo al técnico de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el técnico de datos del objeto
        return obj.data_technician == request.user


class IsDataAnalyst(BasePermission):
    """
    Permite acceso solo al analista de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el analista de datos del objeto
        return obj.data_analyst == request.user


class IsDataScientist(BasePermission):
    """
    Permite acceso solo al científico de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el científico de datos del objeto
        return obj.data_scientist == request.user


class IsDataEngineer(BasePermission):
    """
    Permite acceso solo al ingeniero de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el ingeniero de datos del objeto
        return obj.data_engineer == request.user


class IsDataArchitect(BasePermission):
    """
    Permite acceso solo al arquitecto de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el arquitecto de datos del objeto
        return obj.data_architect == request.user


class IsDataDesigner(BasePermission):
    """
    Permite acceso solo al diseñador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el diseñador de datos del objeto
        return obj.data_designer == request.user


class IsDataDeveloper(BasePermission):
    """
    Permite acceso solo al desarrollador de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el desarrollador de datos del objeto
        return obj.data_developer == request.user


class IsDataTester(BasePermission):
    """
    Permite acceso solo al tester de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el tester de datos del objeto
        return obj.data_tester == request.user


class IsDataDebugger(BasePermission):
    """
    Permite acceso solo al debugger de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el debugger de datos del objeto
        return obj.data_debugger == request.user


class IsDataProfiler(BasePermission):
    """
    Permite acceso solo al profiler de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el profiler de datos del objeto
        return obj.data_profiler == request.user


class IsDataMonitor(BasePermission):
    """
    Permite acceso solo al monitor de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el monitor de datos del objeto
        return obj.data_monitor == request.user


class IsDataAuditor(BasePermission):
    """
    Permite acceso solo al auditor de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el auditor de datos del objeto
        return obj.data_auditor == request.user


class IsDataComplianceOfficer(BasePermission):
    """
    Permite acceso solo al oficial de cumplimiento de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el oficial de cumplimiento de datos del objeto
        return obj.data_compliance_officer == request.user


class IsDataSecurityOfficer(BasePermission):
    """
    Permite acceso solo al oficial de seguridad de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el oficial de seguridad de datos del objeto
        return obj.data_security_officer == request.user


class IsDataPrivacyOfficer(BasePermission):
    """
    Permite acceso solo al oficial de privacidad de datos del objeto.
    """
    message = _('You do not have permission to perform this action.')

    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el oficial de privacidad de datos del objeto
        return obj.data_privacy_officer == request.user

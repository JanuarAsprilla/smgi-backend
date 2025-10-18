# apps/alerts/serializers.py
"""
SMGI Backend - Alerts Serializers
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.utils.translation import gettext_lazy as _

# Importar solo modelos de la app alerts
from apps.alerts.models import Alert, AlertAction
# Opcional: Importar modelos de otras apps si es estrictamente necesario
# y si no crea un acoplamiento inadecuado.
# from apps.notifications.models import AlertNotification # Solo si se maneja la relación aquí


class AlertListSerializer(serializers.ModelSerializer):
    """Simplified serializer for alert listing"""
    
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    assigned_to_name = serializers.SerializerMethodField()
    age_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_id', 'title', 'category', 'severity', 'status',
            'service', 'service_name', 'layer', 'layer_name',
            'affected_features_count', 'change_percentage',
            'assigned_to', 'assigned_to_name', 'first_detected',
            'acknowledged_at', 'resolved_at', 'age_hours', 'tags'
        ]
        read_only_fields = fields
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None


class AlertDetailSerializer(GeoFeatureModelSerializer):
    """
    Detailed serializer for alerts with geometry.
    Removes fields related to notifications and rules that belong to 'notifications' app.
    """
    
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    assigned_to_name = serializers.SerializerMethodField()
    acknowledged_by_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    age_hours = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    time_to_acknowledge = serializers.ReadOnlyField()
    time_to_resolve = serializers.ReadOnlyField()
    actions_count = serializers.SerializerMethodField()
    # --- REMOVED: notifications_count as AlertNotification is not in alerts app ---
    # notifications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        geo_field = 'alert_extent'
        fields = [
            'id', 'title', 'description', 'alert_id', 'category', 'severity',
            'service', 'service_name', 'layer', 'layer_name',
            'affected_features_count', 'change_percentage', 'threshold_value',
            'actual_value', 'alert_extent', 'metadata', 'tags', 'status',
            'first_detected', 'last_updated', 'acknowledged_at', 'resolved_at',
            'expires_at', 'assigned_to', 'assigned_to_name', 'acknowledged_by',
            'acknowledged_by_name', 'resolved_by', 'resolved_by_name',
            'auto_resolve', 'auto_resolve_duration', 'suppress_similar',
            'suppression_duration', 'notification_sent', 'notification_count',
            'last_notification_sent', 'external_ticket_id', 'age_hours',
            'is_expired', 'time_to_acknowledge', 'time_to_resolve',
            'actions_count', # 'notifications_count', # Removido
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'alert_id', 'first_detected', 'last_updated',
            'acknowledged_at', 'resolved_at', 'notification_sent',
            'notification_count', 'last_notification_sent',
            'created', 'modified'
        ]
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None
    
    def get_acknowledged_by_name(self, obj):
        return obj.acknowledged_by.get_full_name() if obj.acknowledged_by else None
    
    def get_resolved_by_name(self, obj):
        return obj.resolved_by.get_full_name() if obj.resolved_by else None
    
    def get_actions_count(self, obj):
        # --- MEJORA: Comentario sobre optimización ---
        # Nota: Esta llamada a obj.actions.count() genera una consulta SQL COUNT.
        # Para evitar el problema de N+1 queries cuando se serializan muchas alertas,
        # asegúrese de que la queryset en la vista use prefetch_related('actions')
        # o anote el conteo en la consulta principal.
        # Ejemplo en la vista:
        # queryset = self.get_queryset().prefetch_related('actions')
        # O usando anotaciones:
        # from django.db.models import Count
        # queryset = self.get_queryset().annotate(actions_count=Count('actions'))
        # Y luego en este método: return getattr(obj, 'actions_count', obj.actions.count())
        return obj.actions.count()

    # --- REMOVED: get_notifications_count as AlertNotification is not in alerts app ---
    # def get_notifications_count(self, obj):
    #     # Asumiendo que existe una relación 'notifications' hacia AlertNotification
    #     # que pertenece a la app 'notifications'
    #     return obj.notifications.count() # Esto fallará si la relación no existe aquí


class AlertActionSerializer(serializers.ModelSerializer):
    """Serializer for alert actions"""
    
    user_name = serializers.SerializerMethodField()
    # --- REMOVED: metadata as AlertAction model does not have it ---
    # metadata = models.JSONField(...) # No existe en el modelo
    alert_title = serializers.CharField(source='alert.title', read_only=True) # Mantenido por conveniencia
    
    class Meta:
        model = AlertAction
        fields = [
            'id', 'alert', 'alert_title', 'action_type', 'user',
            'user_name', 'notes', 'created' # Removido 'metadata'
        ]
        read_only_fields = ['id', 'created']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging alerts"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertResolveSerializer(serializers.Serializer):
    """Serializer for resolving alerts"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertDismissSerializer(serializers.Serializer):
    """Serializer for dismissing alerts"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertAssignSerializer(serializers.Serializer):
    """Serializer for assigning alerts"""
    
    user_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertCommentSerializer(serializers.Serializer):
    """Serializer for adding comments to alerts"""
    
    comment = serializers.CharField(required=True)


class AlertStatisticsSerializer(serializers.Serializer):
    """Serializer for alert statistics"""
    
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    unacknowledged_alerts = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    average_resolution_time_hours = serializers.FloatField()
    alerts_by_severity = serializers.DictField()
    alerts_by_category = serializers.DictField()
    # --- MEJORA: Precisión del tipo de lista ---
    # top_services_with_alerts = serializers.ListField()
    top_services_with_alerts = serializers.ListField(
        child=serializers.DictField() # Cada elemento es un dict {'service': str, 'count': int}
    )
    # --- FIN MEJORA ---


class BulkAlertActionSerializer(serializers.Serializer):
    """Serializer for bulk alert actions"""
    
    alert_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    action = serializers.ChoiceField(
        choices=['acknowledge', 'resolve', 'dismiss'],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)

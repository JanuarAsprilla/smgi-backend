# apps/alerts/tests/test_triggers.py
"""
Tests for scenarios within the alerts app that could be considered 'triggers'
or reactive logic based on alert state changes.
These are distinct from AlertRule evaluation which likely lives in 'monitoring' or 'notifications'.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.alerts.models import Alert, AlertAction, AlertStatus, AlertSeverity, AlertCategory, AlertActionType
# --- CORRECCIÓN: Asegurar que se importa la versión corregida de la tarea ---
# from apps.alerts.tasks import check_and_auto_resolve_alerts, check_and_expire_alerts
# Si el archivo tasks.py ha sido corregido, esta importación está bien.
# Si no, se podría usar patch.object para probar la versión específica.
from apps.alerts.tasks import check_and_auto_resolve_alerts, check_and_expire_alerts


# --- Fixtures ---

@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='trigger_test_user', email='trigger@test.com', password='testpass')

@pytest.fixture
def arcgis_service(user):
    from apps.gis_services.models import ArcGISService
    return ArcGISService.objects.create(
        name='Trigger Test Service',
        # --- CORRECCIÓN: Eliminar espacio extra en la URL ---
        # Original: base_url='https://triggertest.arcgis.com  ',
        base_url='https://triggertest.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    from apps.gis_services.models import SpatialLayer
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=888,
        name='Trigger Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )


# --- Tests for Auto-Resolve Trigger Logic ---

class TestAutoResolveTrigger:

    def test_check_and_auto_resolve_alerts_task(self, user, arcgis_service, spatial_layer):
        # Create alerts that should and should not be auto-resolved
        now = timezone.now()
        
        # Alert 1: Should auto-resolve (ACTIVE, auto_resolve=True, time passed)
        alert1 = Alert.objects.create(
            title='Auto-Resolve Me 1',
            description='Should be auto-resolved.',
            alert_id='AUTO-RESOLVE-1',
            category=AlertCategory.CHANGE_DETECTION,
            severity=AlertSeverity.MEDIUM,
            service=arcgis_service,
            layer=spatial_layer,
            status=AlertStatus.ACTIVE,
            auto_resolve=True,
            auto_resolve_duration=1, # 1 hour
            first_detected=now - timedelta(hours=2) # 2 hours ago
        )
        
        # Alert 2: Should NOT auto-resolve (DISMISSED, even though time passed)
        alert2 = Alert.objects.create(
            title='Do Not Auto-Resolve',
            description='Should not be auto-resolved because it is DISMISSED.',
            alert_id='NO-AUTO-RESOLVE',
            category=AlertCategory.DATA_QUALITY,
            severity=AlertSeverity.HIGH,
            service=arcgis_service,
            layer=spatial_layer,
            status=AlertStatus.DISMISSED,
            auto_resolve=True,
            auto_resolve_duration=1,
            first_detected=now - timedelta(hours=2)
        )
        
        # Alert 3: Should NOT auto-resolve yet (ACTIVE, auto_resolve=True, but time not passed)
        alert3 = Alert.objects.create(
            title='Not Yet Auto-Resolve',
            description='Should not be auto-resolved yet.',
            alert_id='NOT-YET-AUTO-RESOLVE',
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.LOW,
            service=arcgis_service,
            layer=spatial_layer,
            status=AlertStatus.ACKNOWLEDGED,
            auto_resolve=True,
            auto_resolve_duration=3, # 3 hours
            first_detected=now - timedelta(hours=2) # 2 hours ago
        )

        # Run the task
        result = check_and_auto_resolve_alerts()

        # Assertions
        assert result['resolved_count'] == 1
        
        # Refresh from DB
        alert1.refresh_from_db()
        alert2.refresh_from_db()
        alert3.refresh_from_db()
        
        # Alert 1 should be resolved
        assert alert1.status == AlertStatus.RESOLVED
        action1 = AlertAction.objects.filter(alert=alert1, action_type=AlertActionType.RESOLVED, notes__contains="Auto-resolved").first()
        assert action1 is not None
        
        # Alert 2 status unchanged
        assert alert2.status == AlertStatus.DISMISSED
        
        # Alert 3 status unchanged
        assert alert3.status == AlertStatus.ACKNOWLEDGED


# --- Tests for Expiration Trigger Logic ---

class TestExpirationTrigger:

    def test_check_and_expire_alerts_task(self, user, arcgis_service, spatial_layer):
        now = timezone.now()
        
        # Alert 1: Should expire (ACTIVE, expires_at in the past)
        alert1 = Alert.objects.create(
            title='Expire Me',
            description='Should be marked as expired.',
            alert_id='EXPIRE-ME',
            category=AlertCategory.SERVICE_AVAILABILITY,
            severity=AlertSeverity.HIGH,
            service=arcgis_service,
            layer=spatial_layer,
            status=AlertStatus.ACTIVE,
            expires_at=now - timedelta(minutes=30) # Expired 30 mins ago
        )
        
        # Alert 2: Should NOT expire (ACTIVE, expires_at in the future)
        alert2 = Alert.objects.create(
            title='Still Valid',
            description='Should not expire yet.',
            alert_id='STILL-VALID',
            category=AlertCategory.THRESHOLD_BREACH,
            severity=AlertSeverity.CRITICAL,
            service=arcgis_service,
            layer=spatial_layer,
            status=AlertStatus.ACTIVE,
            expires_at=now + timedelta(hours=1) # Expires in 1 hour
        )
        
        # Alert 3: Already resolved, should NOT be touched even if expires_at is past
        alert3 = Alert.objects.create(
            title='Already Resolved',
            description='Was resolved before expiring.',
            alert_id='ALREADY-RESOLVED',
            category=AlertCategory.SYSTEM_HEALTH,
            severity=AlertSeverity.MEDIUM,
            service=arcgis_service,
            layer=spatial_layer,
            status=AlertStatus.RESOLVED, # Important: already resolved
            expires_at=now - timedelta(days=1) # Expired long ago
        )

        # Run the task
        result = check_and_expire_alerts()

        # Assertions
        assert result['expired_count'] == 1
        
        # Refresh from DB
        alert1.refresh_from_db()
        alert2.refresh_from_db()
        alert3.refresh_from_db()
        
        # Alert 1 should be expired
        assert alert1.status == AlertStatus.EXPIRED
        # --- CORRECCIÓN: Alinear con la versión revisada de tasks.py ---
        # Original: action1 = AlertAction.objects.filter(alert=alert1, action_type=AlertActionType.RESOLVED, notes__contains="expired").first()
        # Revisado: check_and_expire_alerts ahora crea una AlertAction con action_type=AlertActionType.EXPIRED
        action1 = AlertAction.objects.filter(alert=alert1, action_type=AlertActionType.EXPIRED).first()
        assert action1 is not None
        # Opcional: Verificar la nota también
        # assert "expired automatically" in action1.notes
        # --- FIN CORRECCIÓN ---
        
        # Alert 2 status unchanged
        assert alert2.status == AlertStatus.ACTIVE
        
        # Alert 3 status unchanged
        assert alert3.status == AlertStatus.RESOLVED

    # Consider testing edge cases like alerts with expires_at=None

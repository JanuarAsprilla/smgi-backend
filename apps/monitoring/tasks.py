"""
Celery tasks for Monitoring app.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import (
    MonitoringProject,
    Monitor,
    Detection,
    ChangeRecord,
    MonitoringReport,
    Baseline
)
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def run_monitor_check(monitor_id):
    """
    Run a monitoring check.
    
    Args:
        monitor_id: ID of the Monitor
    """
    try:
        monitor = Monitor.objects.select_related('project', 'agent').get(id=monitor_id)
        
        logger.info(f"Running check for monitor: {monitor.name}")
        
        # Update monitor status
        monitor.last_check = timezone.now()
        monitor.check_count += 1
        
        # Run the actual monitoring logic
        if monitor.agent:
            # Use agent for analysis
            result = run_agent_monitor(monitor)
        else:
            # Use basic monitoring logic
            result = run_basic_monitor(monitor)
        
        # Process results
        if result.get('detections'):
            for detection_data in result['detections']:
                create_detection(monitor, detection_data)
        
        # Update next check
        from .utils import calculate_next_check
        monitor.next_check = calculate_next_check(monitor)
        monitor.status = 'active'
        monitor.save()
        
        logger.info(f"Check completed for monitor {monitor.name}: {len(result.get('detections', []))} detections")
        return {
            'status': 'success',
            'monitor_id': monitor_id,
            'detections_count': len(result.get('detections', []))
        }
        
    except Monitor.DoesNotExist:
        logger.error(f"Monitor {monitor_id} not found")
        return {'status': 'failed', 'error': 'Monitor not found'}
    except Exception as e:
        logger.error(f"Error running monitor check: {str(e)}")
        
        # Update monitor status to error
        try:
            monitor = Monitor.objects.get(id=monitor_id)
            monitor.status = 'error'
            monitor.save()
        except:
            pass
        
        return {'status': 'failed', 'error': str(e)}


def run_agent_monitor(monitor):
    """
    Run monitoring using an agent.
    
    Args:
        monitor: Monitor instance
        
    Returns:
        dict: Results with detections
    """
    from apps.agents.models import AgentExecution
    from apps.agents.tasks import execute_agent
    
    logger.info(f"Running agent-based monitor: {monitor.agent.name}")
    
    # Create agent execution
    execution = AgentExecution.objects.create(
        agent=monitor.agent,
        name=f"Monitor Check: {monitor.name}",
        parameters=monitor.parameters,
        created_by=monitor.created_by
    )
    
    # Set input layers
    execution.input_layers.set(monitor.layers.all())
    
    # Execute agent (synchronously for monitoring)
    # Note: In production, you might want to make this async
    result = execute_agent(execution.id)
    
    # Process agent results
    detections = []
    if result['status'] == 'success':
        output_data = execution.output_data
        
        # Extract detections from agent output
        if 'detections' in output_data:
            detections = output_data['detections']
    
    return {'detections': detections}


def run_basic_monitor(monitor):
    """
    Run basic monitoring without agent.
    
    Args:
        monitor: Monitor instance
        
    Returns:
        dict: Results with detections
    """
    logger.info(f"Running basic monitor: {monitor.name}")
    
    detections = []
    
    # Get baseline if exists
    baseline = monitor.baselines.filter(is_current=True).first()
    
    if not baseline:
        logger.warning(f"No baseline found for monitor {monitor.name}")
        return {'detections': []}
    
    # Compare current state with baseline
    for layer in monitor.layers.all():
        current_features = layer.features.filter(is_active=True)
        current_count = current_features.count()
        baseline_count = baseline.feature_count
        
        # Simple change detection based on feature count
        if abs(current_count - baseline_count) > baseline_count * 0.1:  # 10% threshold
            detections.append({
                'title': f'Cambio detectado en {layer.name}',
                'description': f'Diferencia de {abs(current_count - baseline_count)} features',
                'severity': 'medium',
                'layer': layer,
                'analysis_data': {
                    'current_count': current_count,
                    'baseline_count': baseline_count,
                    'difference': current_count - baseline_count
                }
            })
    
    return {'detections': detections}


def create_detection(monitor, detection_data):
    """
    Create a detection record.
    
    Args:
        monitor: Monitor instance
        detection_data: Dictionary with detection information
    """
    try:
        detection = Detection.objects.create(
            monitor=monitor,
            title=detection_data.get('title', 'Detección sin título'),
            description=detection_data.get('description', ''),
            severity=detection_data.get('severity', 'medium'),
            location=detection_data.get('location'),
            affected_area=detection_data.get('affected_area'),
            analysis_data=detection_data.get('analysis_data', {}),
            confidence_score=detection_data.get('confidence_score'),
            evidence=detection_data.get('evidence', {}),
            created_by=monitor.created_by
        )
        
        # Add related layers
        if 'related_layers' in detection_data:
            detection.related_layers.set(detection_data['related_layers'])
        
        # Create change records if provided
        if 'changes' in detection_data:
            for change_data in detection_data['changes']:
                ChangeRecord.objects.create(
                    detection=detection,
                    change_type=change_data.get('change_type', 'modified'),
                    feature_id=change_data.get('feature_id', ''),
                    layer=change_data.get('layer'),
                    before_geometry=change_data.get('before_geometry'),
                    after_geometry=change_data.get('after_geometry'),
                    before_attributes=change_data.get('before_attributes', {}),
                    after_attributes=change_data.get('after_attributes', {}),
                    change_magnitude=change_data.get('change_magnitude'),
                    created_by=monitor.created_by
                )
        
        # Update monitor detection count
        monitor.detection_count += 1
        monitor.save()
        
        logger.info(f"Detection created: {detection.title}")
        return detection
        
    except Exception as e:
        logger.error(f"Error creating detection: {str(e)}")
        return None


@shared_task
def process_scheduled_monitors():
    """
    Process all monitors that are due for checking.
    This task should be run periodically via Celery Beat.
    """
    logger.info("Processing scheduled monitors")
    
    now = timezone.now()
    
    # Get monitors that need checking
    monitors = Monitor.objects.filter(
        status='active',
        is_active=True,
        next_check__lte=now
    )
    
    checked_count = 0
    for monitor in monitors:
        run_monitor_check.delay(monitor.id)
        checked_count += 1
    
    logger.info(f"Triggered {checked_count} monitor checks")
    return f"Checked {checked_count} monitors"


@shared_task
def generate_monitoring_report(project_id, report_type, start_date, end_date):
    """
    Generate a monitoring report.
    
    Args:
        project_id: ID of the MonitoringProject
        report_type: Type of report
        start_date: Start date for the report
        end_date: End date for the report
    """
    try:
        from datetime import datetime
        
        project = MonitoringProject.objects.get(id=project_id)
        
        logger.info(f"Generating {report_type} report for project: {project.name}")
        
        # Parse dates
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Get data for the period
        monitors = project.monitors.filter(is_active=True)
        detections = Detection.objects.filter(
            monitor__project=project,
            detected_at__gte=start,
            detected_at__lte=end,
            is_active=True
        )
        
        # Calculate statistics
        statistics = {
            'total_monitors': monitors.count(),
            'active_monitors': monitors.filter(status='active').count(),
            'total_detections': detections.count(),
            'total_checks': sum(m.check_count for m in monitors),
            'detections_by_severity': {
                'critical': detections.filter(severity='critical').count(),
                'high': detections.filter(severity='high').count(),
                'medium': detections.filter(severity='medium').count(),
                'low': detections.filter(severity='low').count(),
            },
            'detections_by_status': {
                'new': detections.filter(status='new').count(),
                'confirmed': detections.filter(status='confirmed').count(),
                'false_positive': detections.filter(status='false_positive').count(),
                'resolved': detections.filter(status='resolved').count(),
            }
        }
        
        # Create detections summary
        detections_summary = []
        for detection in detections[:20]:  # Top 20 detections
            detections_summary.append({
                'id': detection.id,
                'title': detection.title,
                'severity': detection.severity,
                'status': detection.status,
                'detected_at': detection.detected_at.isoformat(),
                'monitor': detection.monitor.name
            })
        
        # Generate summary text
        summary = f"""
        Reporte de Monitoreo - {project.name}
        Período: {start.date()} a {end.date()}
        
        Resumen:
        - {statistics['total_monitors']} monitores totales
        - {statistics['total_checks']} verificaciones realizadas
        - {statistics['total_detections']} detecciones registradas
        
        Detecciones por severidad:
        - Críticas: {statistics['detections_by_severity']['critical']}
        - Altas: {statistics['detections_by_severity']['high']}
        - Medias: {statistics['detections_by_severity']['medium']}
        - Bajas: {statistics['detections_by_severity']['low']}
        """
        
        # Create report
        report = MonitoringReport.objects.create(
            project=project,
            title=f"Reporte {report_type} - {project.name}",
            report_type=report_type,
            start_date=start,
            end_date=end,
            summary=summary.strip(),
            statistics=statistics,
            detections_summary={'detections': detections_summary},
            created_by=project.created_by
        )
        
        # TODO: Generate PDF or other file format
        
        logger.info(f"Report generated: {report.title}")
        return {
            'status': 'success',
            'report_id': report.id
        }
        
    except MonitoringProject.DoesNotExist:
        logger.error(f"Project {project_id} not found")
        return {'status': 'failed', 'error': 'Project not found'}
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def cleanup_old_detections(days=90):
    """
    Archive old detections.
    
    Args:
        days: Number of days to keep detections
    """
    threshold_date = timezone.now() - timedelta(days=days)
    
    # Mark old resolved/ignored detections as inactive
    updated = Detection.objects.filter(
        detected_at__lt=threshold_date,
        status__in=['resolved', 'ignored', 'false_positive']
    ).update(is_active=False)
    
    logger.info(f"Archived {updated} old detections")
    return f"Archived {updated} detections"


@shared_task
def update_monitor_statistics():
    """
    Update statistics for all monitors.
    This task should be run periodically (e.g., daily).
    """
    logger.info("Updating monitor statistics")
    
    monitors = Monitor.objects.filter(is_active=True)
    updated_count = 0
    
    for monitor in monitors:
        # Recalculate detection count
        detection_count = monitor.detections.filter(is_active=True).count()
        
        if monitor.detection_count != detection_count:
            monitor.detection_count = detection_count
            monitor.save()
            updated_count += 1
    
    logger.info(f"Updated statistics for {updated_count} monitors")
    return f"Updated {updated_count} monitors"


@shared_task
def check_critical_detections():
    """
    Check for critical detections and send alerts.
    This task should be run frequently (e.g., every 5 minutes).
    """
    logger.info("Checking for critical detections")
    
    # Get new critical detections
    critical_detections = Detection.objects.filter(
        severity='critical',
        status='new',
        is_active=True,
        detected_at__gte=timezone.now() - timedelta(hours=1)
    )
    
    alert_count = 0
    for detection in critical_detections:
        # Create alert (will be handled by alerts app)
        from apps.alerts.tasks import create_alert_for_detection
        create_alert_for_detection.delay(detection.id)
        alert_count += 1
    
    logger.info(f"Created {alert_count} alerts for critical detections")
    return f"Created {alert_count} alerts"

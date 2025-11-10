"""
Utility functions for Monitoring app.
"""
from django.utils import timezone
from datetime import timedelta


def calculate_next_check(monitor):
    """
    Calculate next check time for a monitor.
    
    Args:
        monitor: Monitor instance
        
    Returns:
        datetime: Next check time
    """
    now = timezone.now()
    
    if monitor.last_check:
        next_check = monitor.last_check + timedelta(minutes=monitor.check_interval)
    else:
        next_check = now + timedelta(minutes=monitor.check_interval)
    
    # If next check is in the past, set it to now + interval
    if next_check < now:
        next_check = now + timedelta(minutes=monitor.check_interval)
    
    return next_check


def calculate_change_magnitude(before, after, change_type='modified'):
    """
    Calculate magnitude of change between two states.
    
    Args:
        before: Before state (geometry or attributes)
        after: After state (geometry or attributes)
        change_type: Type of change
        
    Returns:
        float: Magnitude of change
    """
    if change_type == 'added':
        return 1.0
    elif change_type == 'removed':
        return 1.0
    elif change_type == 'modified':
        # Simple percentage-based calculation
        # In production, this would be more sophisticated
        return 0.5
    elif change_type == 'moved':
        # Calculate distance moved
        # This would need geometric calculations
        return 0.3
    
    return 0.0


def assess_detection_severity(analysis_data, monitor_type):
    """
    Assess severity of a detection based on analysis data.
    
    Args:
        analysis_data: Dictionary with analysis results
        monitor_type: Type of monitor
        
    Returns:
        str: Severity level (low, medium, high, critical)
    """
    # This is a simplified example
    # In production, this would use more sophisticated logic
    
    confidence = analysis_data.get('confidence_score', 0.5)
    magnitude = analysis_data.get('change_magnitude', 0.5)
    
    score = (confidence + magnitude) / 2
    
    if score >= 0.8:
        return 'critical'
    elif score >= 0.6:
        return 'high'
    elif score >= 0.4:
        return 'medium'
    else:
        return 'low'


def compare_geometries(geom1, geom2):
    """
    Compare two geometries and return change information.
    
    Args:
        geom1: First geometry
        geom2: Second geometry
        
    Returns:
        dict: Change information
    """
    from django.contrib.gis.geos import GEOSGeometry
    
    if not geom1 or not geom2:
        return {
            'changed': True,
            'change_type': 'removed' if not geom2 else 'added',
            'magnitude': 1.0
        }
    
    # Calculate area or distance difference
    if geom1.geom_type in ['Polygon', 'MultiPolygon']:
        area1 = geom1.area
        area2 = geom2.area
        if area1 > 0:
            magnitude = abs(area2 - area1) / area1
        else:
            magnitude = 1.0
    else:
        # For points and lines, use distance
        magnitude = geom1.distance(geom2)
    
    changed = magnitude > 0.01  # 1% threshold
    
    return {
        'changed': changed,
        'change_type': 'modified' if changed else 'unchanged',
        'magnitude': magnitude
    }


def generate_detection_title(monitor, change_data):
    """
    Generate a descriptive title for a detection.
    
    Args:
        monitor: Monitor instance
        change_data: Dictionary with change information
        
    Returns:
        str: Detection title
    """
    monitor_type = monitor.monitor_type
    change_type = change_data.get('change_type', 'cambio')
    layer_name = change_data.get('layer_name', 'capa')
    
    titles = {
        'change_detection': f'Cambio detectado en {layer_name}',
        'threshold': f'Umbral excedido en {layer_name}',
        'anomaly': f'Anomalía detectada en {layer_name}',
        'pattern': f'Patrón detectado en {layer_name}',
        'temporal': f'Cambio temporal en {layer_name}',
        'spatial': f'Cambio espacial en {layer_name}',
    }
    
    return titles.get(monitor_type, f'Detección en {layer_name}')


def validate_monitor_configuration(monitor):
    """
    Validate monitor configuration.
    
    Args:
        monitor: Monitor instance
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if monitor has at least one layer or data source
    if not monitor.layers.exists() and not monitor.data_sources.exists():
        return False, "El monitor debe tener al menos una capa o fuente de datos"
    
    # Check if check_interval is valid
    if monitor.check_interval < 1:
        return False, "El intervalo de verificación debe ser al menos 1 minuto"
    
    # Check if agent exists and is published
    if monitor.agent:
        if monitor.agent.status != 'published':
            return False, "El agente debe estar publicado"
    
    return True, None

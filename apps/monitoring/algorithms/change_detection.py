"""
SMGI Backend - Change Detection Algorithms
Sistema de Monitoreo Geoespacial Inteligente
Implementación de algoritmos para detección de cambios en capas espaciales
"""

import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from django.contrib.gis.geos import Point, Polygon
from apps.monitoring.models import LayerSnapshot, SpatialLayer, AffectedFeature
from apps.gis_services.clients.arcgis_client import ArcGISClient

logger = logging.getLogger('apps.monitoring.algorithms')

class BaseChangeDetector(ABC):
    """
    Clase base abstracta para detectores de cambio.
    Define la interfaz común que deben implementar todos los algoritmos.
    """
    
    @abstractmethod
    def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
        """
        Método abstracto para realizar la detección de cambios.

        Args:
            current_snapshot: Instantánea actual de la capa.
            previous_snapshot: Instantánea anterior de la capa.
            layer: Instancia del modelo SpatialLayer asociada.

        Returns:
            Diccionario con los resultados de la detección de cambios.
        """
        pass

    def _compare_basic_metrics(self, current: LayerSnapshot, previous: LayerSnapshot) -> Dict[str, float]:
        """Compara métricas básicas entre snapshots."""
        feature_count_change = current.feature_count - previous.feature_count
        feature_count_change_percent = 0
        if previous.feature_count > 0:
            feature_count_change_percent = (feature_count_change / previous.feature_count) * 100

        area_change = 0
        area_change_percent = 0
        if current.total_area is not None and previous.total_area is not None:
            area_change = current.total_area - previous.total_area
            if previous.total_area != 0:
                area_change_percent = (area_change / previous.total_area) * 100

        centroid_displacement = 0
        if current.centroid and previous.centroid:
            try:
                centroid_displacement = current.centroid.distance(previous.centroid)
            except Exception:
                logger.warning("Could not calculate centroid displacement, geometries may be invalid.")

        return {
            'feature_count_change': feature_count_change,
            'feature_count_change_percent': feature_count_percent,
            'area_change': area_change,
            'area_change_percent': area_change_percent,
            'centroid_displacement': centroid_displacement
        }

    def _check_thresholds(self, metrics: Dict[str, float], layer: SpatialLayer) -> Tuple[bool, Dict[str, float]]:
        """Verifica si los cambios exceden los umbrales de la capa."""
        change_threshold = layer.change_threshold
        exceeds_threshold = False
        threshold_values = {
            'feature_count_threshold': change_threshold,
            'area_threshold': change_threshold
        }

        if abs(metrics['feature_count_change_percent']) >= change_threshold * 2:
            exceeds_threshold = True
        elif abs(metrics['area_change_percent']) >= change_threshold * 2:
            exceeds_threshold = True

        return exceeds_threshold, threshold_values


class SimpleCountChangeDetector(BaseChangeDetector):
    """
    Detector de cambios basado en conteo simple de features.
    """
    
    def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
        logger.info(f"Running SimpleCountChangeDetector for layer {layer.name}")
        
        # Comparar métricas básicas
        metrics = self._compare_basic_metrics(current_snapshot, previous_snapshot)
        
        # Determinar si hay cambios significativos
        has_changes = abs(metrics['feature_count_change_percent']) >= layer.change_threshold
        change_types = ['feature_count'] if has_changes else []
        
        # Determinar si excede el umbral
        exceeds_threshold, threshold_values = self._check_thresholds(metrics, layer)
        
        # Calcular confianza (alta para conteo simple)
        confidence_score = 0.95 if has_changes else 0.98

        # Preparar detalles
        change_details = {
            'algorithm_used': 'SimpleCountChangeDetector',
            'comparison_time': current_snapshot.created.isoformat(),
            'previous_snapshot_id': str(previous_snapshot.id),
            'current_snapshot_id': str(current_snapshot.id),
            'changes_by_category': {
                'features': {
                    'added': max(0, metrics['feature_count_change']),
                    'removed': max(0, -metrics['feature_count_change']),
                    'modified': 0  # No se determina con solo conteo
                },
                'geometry': {
                    'area_change': metrics['area_change'],
                    'centroid_displacement': metrics['centroid_displacement']
                }
            }
        }

        return {
            'has_changes': has_changes,
            'change_types': change_types,
            'feature_count_change': metrics['feature_count_change'],
            'feature_count_change_percent': metrics['feature_count_change_percent'],
            'area_change': metrics['area_change'],
            'area_change_percent': metrics['area_change_percent'],
            'centroid_displacement': metrics['centroid_displacement'],
            'new_features': max(0, metrics['feature_count_change']),
            'deleted_features': max(0, -metrics['feature_count_change']),
            'modified_features': 0, # No se determina
            'data_quality_score': 1.0, # Placeholder
            'data_quality_change': 0.0, # Placeholder
            'change_details': change_details,
            'exceeds_threshold': exceeds_threshold,
            'threshold_values': threshold_values,
            'confidence_score': confidence_score,
            'affected_feature_ids': [] # No se identifican features específicas con solo conteo
        }


class HashComparisonChangeDetector(BaseChangeDetector):
    """
    Detector de cambios basado en comparación de hashes.
    """
    
    def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
        logger.info(f"Running HashComparisonChangeDetector for layer {layer.name}")
        
        # Comparar hashes
        has_changes = current_snapshot.snapshot_hash != previous_snapshot.snapshot_hash
        change_types = ['attribute', 'geometry'] if has_changes else []
        
        # Comparar métricas básicas
        metrics = self._compare_basic_metrics(current_snapshot, previous_snapshot)
        
        # Determinar si excede el umbral
        exceeds_threshold, threshold_values = self._check_thresholds(metrics, layer)
        
        # Calcular confianza (alta si el hash cambió, media si solo métricas básicas)
        confidence_score = 0.99 if has_changes else 0.8

        # Preparar detalles
        change_details = {
            'algorithm_used': 'HashComparisonChangeDetector',
            'comparison_time': current_snapshot.created.isoformat(),
            'previous_snapshot_id': str(previous_snapshot.id),
            'current_snapshot_id': str(current_snapshot.id),
            'snapshot_hashes': {
                'current': current_snapshot.snapshot_hash,
                'previous': previous_snapshot.snapshot_hash
            }
        }

        return {
            'has_changes': has_changes,
            'change_types': change_types,
            'feature_count_change': metrics['feature_count_change'],
            'feature_count_change_percent': metrics['feature_count_change_percent'],
            'area_change': metrics['area_change'],
            'area_change_percent': metrics['area_change_percent'],
            'centroid_displacement': metrics['centroid_displacement'],
            'new_features': max(0, metrics['feature_count_change']) if has_changes else 0,
            'deleted_features': max(0, -metrics['feature_count_change']) if has_changes else 0,
            'modified_features': 0, # No se determina con solo hash
            'data_quality_score': 1.0, # Placeholder
            'data_quality_change': 0.0, # Placeholder
            'change_details': change_details,
            'exceeds_threshold': exceeds_threshold,
            'threshold_values': threshold_values,
            'confidence_score': confidence_score,
            'affected_feature_ids': [] # No se identifican features específicas con solo hash
        }


class FieldComparisonChangeDetector(BaseChangeDetector):
    """
    Detector de cambios basado en comparación campo por campo.
    Requiere acceso a los datos completos de las features.
    """
    
    def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
        logger.info(f"Running FieldComparisonChangeDetector for layer {layer.name}")
        
        # Inicializar cliente GIS
        client = ArcGISClient(layer.service)
        
        # Obtener todas las features de la capa actual y anterior
        # NOTA: Esto puede ser costoso para capas grandes
        current_features = list(client.get_all_features(layer.layer_id))
        # Para la comparación, necesitaríamos tener guardadas las features anteriores o volver a obtenerlas
        # Si solo tenemos snapshots, esta información no está disponible directamente.
        # Se asume que se puede obtener una "versión anterior" o que se compara con un estado guardado.
        # Por simplicidad en este ejemplo, solo comparamos el conteo y asumimos que si hay diferencia,
        # podría haber cambios en campos.
        
        # Comparar métricas básicas
        metrics = self._compare_basic_metrics(current_snapshot, previous_snapshot)
        has_changes_basic = abs(metrics['feature_count_change_percent']) >= layer.change_threshold
        
        # Comparar campos (simulado)
        # En una implementación real, aquí se iteraría sobre las features actuales y anteriores,
        # comparando cada campo relevante.
        # Por ahora, asumimos que si el conteo cambió o si el hash general cambió (lo cual incluye campos),
        # entonces hay cambios en campos.
        has_changes_fields = current_snapshot.snapshot_hash != previous_snapshot.snapshot_hash
        
        has_changes = has_changes_basic or has_changes_fields
        change_types = []
        if has_changes_basic:
            change_types.append('feature_count')
        if has_changes_fields:
            change_types.append('attribute')
        
        # Determinar si excede el umbral
        exceeds_threshold, threshold_values = self._check_thresholds(metrics, layer)
        
        # Calcular confianza (baja a media debido a la complejidad de la comparación real)
        confidence_score = 0.7 if has_changes else 0.95

        # Identificar features afectadas (simulado)
        # En una implementación real, aquí se determinaría qué features específicas cambiaron.
        affected_feature_ids = [] # Placeholder - Requiere lógica real de comparación de features
        if has_changes:
             # Simular que algunas features pudieron haber cambiado
             # Por ejemplo, si se agregaron o eliminaron, tomar un subconjunto
             if metrics['new_features'] > 0:
                 # Simular IDs de nuevas features (esto es una simplificación)
                 affected_feature_ids.extend([f"NEW_{i}" for i in range(min(metrics['new_features'], 5))]) # Solo primeras 5
             if metrics['deleted_features'] > 0:
                 # Simular IDs de features eliminadas (esto es una simplificación)
                 affected_feature_ids.extend([f"DEL_{i}" for i in range(min(metrics['deleted_features'], 5))]) # Solo primeras 5
             # Para modificaciones, se necesitaría un ID real de la feature y compararla


        # Preparar detalles
        change_details = {
            'algorithm_used': 'FieldComparisonChangeDetector',
            'comparison_time': current_snapshot.created.isoformat(),
            'previous_snapshot_id': str(previous_snapshot.id),
            'current_snapshot_id': str(current_snapshot.id),
            'fields_compared': layer.change_detection_fields, # Campos a monitorear según la capa
            'comparison_summary': {
                'features_compared': len(current_features), # Aproximado
                'potential_field_changes': has_changes_fields
            }
        }

        return {
            'has_changes': has_changes,
            'change_types': change_types,
            'feature_count_change': metrics['feature_count_change'],
            'feature_count_change_percent': metrics['feature_count_change_percent'],
            'area_change': metrics['area_change'],
            'area_change_percent': metrics['area_change_percent'],
            'centroid_displacement': metrics['centroid_displacement'],
            'new_features': max(0, metrics['feature_count_change']),
            'deleted_features': max(0, -metrics['feature_count_change']),
            'modified_features': 0, # Placeholder - Requiere lógica real
            'data_quality_score': 1.0, # Placeholder
            'data_quality_change': 0.0, # Placeholder
            'change_details': change_details,
            'exceeds_threshold': exceeds_threshold,
            'threshold_values': threshold_values,
            'confidence_score': confidence_score,
            'affected_feature_ids': affected_feature_ids
        }


class GeometricAnalysisChangeDetector(BaseChangeDetector):
    """
    Detector de cambios basado en análisis geométrico (área, perímetro, forma).
    """
    
    def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
        logger.info(f"Running GeometricAnalysisChangeDetector for layer {layer.name}")
        
        # Comparar métricas geométricas
        metrics = self._compare_basic_metrics(current_snapshot, previous_snapshot)
        
        # Determinar si hay cambios geométricos significativos
        # Se puede usar area_change_percent o centroid_displacement
        has_area_changes = abs(metrics['area_change_percent']) >= layer.change_threshold
        has_location_changes = metrics['centroid_displacement'] >= layer.change_threshold # Umbral debería ser en unidades espaciales
        
        has_changes = has_area_changes or has_location_changes
        change_types = []
        if has_area_changes:
            change_types.append('geometry')
        if has_location_changes:
            change_types.append('geometry') # Cambio de ubicación también es geométrico

        # Determinar si excede el umbral
        exceeds_threshold, threshold_values = self._check_thresholds(metrics, layer)
        # También verificar umbral geométrico específico si aplica
        if not exceeds_threshold and has_area_changes:
            # Suponiendo un threshold geométrico implícito basado en change_threshold
            exceeds_threshold = True # Ajustar según regla específica si es necesario

        # Calcular confianza (media a alta para cambios geométricos claros)
        confidence_score = 0.85 if has_changes else 0.95

        # Preparar detalles
        change_details = {
            'algorithm_used': 'GeometricAnalysisChangeDetector',
            'comparison_time': current_snapshot.created.isoformat(),
            'previous_snapshot_id': str(previous_snapshot.id),
            'current_snapshot_id': str(current_snapshot.id),
            'geometric_metrics': {
                'area_change': metrics['area_change'],
                'area_change_percent': metrics['area_change_percent'],
                'centroid_displacement': metrics['centroid_displacement']
            }
        }

        return {
            'has_changes': has_changes,
            'change_types': change_types,
            'feature_count_change': metrics['feature_count_change'],
            'feature_count_change_percent': metrics['feature_count_change_percent'],
            'area_change': metrics['area_change'],
            'area_change_percent': metrics['area_change_percent'],
            'centroid_displacement': metrics['centroid_displacement'],
            'new_features': max(0, metrics['feature_count_change']) if has_changes else 0,
            'deleted_features': max(0, -metrics['feature_count_change']) if has_changes else 0,
            'modified_features': 0, # Placeholder - Requiere análisis de forma detallado
            'data_quality_score': 1.0, # Placeholder
            'data_quality_change': 0.0, # Placeholder
            'change_details': change_details,
            'exceeds_threshold': exceeds_threshold,
            'threshold_values': threshold_values,
            'confidence_score': confidence_score,
            'affected_feature_ids': [] # Placeholder - Requiere análisis de forma detallado
        }


class StatisticalAnalysisChangeDetector(BaseChangeDetector):
    """
    Detector de cambios basado en análisis estadístico (promedios, varianzas, distribuciones).
    """
    
    def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
        logger.info(f"Running StatisticalAnalysisChangeDetector for layer {layer.name}")
        
        # Comparar métricas básicas
        metrics = self._compare_basic_metrics(current_snapshot, previous_snapshot)
        
        # Obtener datos estadísticos de snapshots si están disponibles
        # (Estadísticas calculadas previamente y almacenadas en attribute_stats)
        current_stats = current_snapshot.attribute_stats
        previous_stats = previous_snapshot.attribute_stats

        has_changes = False
        change_types = ['statistical'] # Asumimos que siempre es un cambio estadístico si se ejecuta este algoritmo
        
        # Ejemplo simple: Comparar promedios de campos numéricos
        significant_stat_changes = {}
        for field_name, current_field_stats in current_stats.items():
            if field_name in previous_stats:
                prev_avg = previous_stats[field_name].get('avg', 0)
                curr_avg = current_field_stats.get('avg', 0)
                if prev_avg != 0:
                    change_percentage = abs((curr_avg - prev_avg) / prev_avg) * 100
                    if change_percentage >= layer.change_threshold:
                         significant_stat_changes[field_name] = {
                             'previous_avg': prev_avg,
                             'current_avg': curr_avg,
                             'change_percentage': change_percentage
                         }
                         has_changes = True
                # Similar para otros estadísticos (varianza, etc.)

        # Determinar si excede el umbral
        exceeds_threshold, threshold_values = self._check_thresholds(metrics, layer)
        # Verificar umbrales estadísticos específicos
        if significant_stat_changes:
            exceeds_threshold = True # Si se encontraron cambios estadísticos significativos, excede

        # Calcular confianza (media a alta si se detectan cambios estadísticos)
        confidence_score = 0.8 if has_changes else 0.9

        # Preparar detalles
        change_details = {
            'algorithm_used': 'StatisticalAnalysisChangeDetector',
            'comparison_time': current_snapshot.created.isoformat(),
            'previous_snapshot_id': str(previous_snapshot.id),
            'current_snapshot_id': str(current_snapshot.id),
            'statistical_metrics': {
                'significant_changes': significant_stat_changes,
                'compared_fields': list(current_stats.keys())
            }
        }

        return {
            'has_changes': has_changes,
            'change_types': change_types,
            'feature_count_change': metrics['feature_count_change'],
            'feature_count_change_percent': metrics['feature_count_change_percent'],
            'area_change': metrics['area_change'],
            'area_change_percent': metrics['area_change_percent'],
            'centroid_displacement': metrics['centroid_displacement'],
            'new_features': max(0, metrics['feature_count_change']) if has_changes else 0,
            'deleted_features': max(0, -metrics['feature_count_change']) if has_changes else 0,
            'modified_features': 0, # Placeholder - Requiere análisis más complejo
            'data_quality_score': 1.0, # Placeholder
            'data_quality_change': 0.0, # Placeholder
            'change_details': change_details,
            'exceeds_threshold': exceeds_threshold,
            'threshold_values': threshold_values,
            'confidence_score': confidence_score,
            'affected_feature_ids': [] # Placeholder - Requiere análisis más complejo
        }


# --- Opcional: Detector de Anomalías con ML ---
# class MLAnomalyDetectionChangeDetector(BaseChangeDetector):
#     """
#     Detector de cambios basado en detección de anomalías con Machine Learning.
#     Requiere un modelo entrenado.
#     """
#     def detect(self, current_snapshot: LayerSnapshot, previous_snapshot: LayerSnapshot, layer: SpatialLayer) -> Dict[str, Any]:
#         # Lógica para cargar modelo, preprocesar datos de snapshots, predecir anomalías
#         # ...
#         pass
#     # Esta clase se implementaría cuando se tenga el modelo ML listo.

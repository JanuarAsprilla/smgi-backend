# apps/alerts/triggers/change_trigger.py
"""
SMGI Backend - Change Detection Alert Trigger
Sistema de Monitoreo Geoespacial Inteligente

Trigger for alerts based on detected changes in spatial layers.
"""
import logging
from typing import Dict, Any, Optional
from apps.alerts.triggers.base_trigger import BaseAlertTrigger, AlertTriggerEvaluationResult
from apps.alerts.models import AlertSeverity, AlertCategory
from apps.monitoring.models import ChangeDetectionResult # Assumes ChangeDetectionResult provides necessary data

logger = logging.getLogger('apps.alerts.triggers.change')


class ChangeAlertTrigger(BaseAlertTrigger):
    """
    Trigger that fires an alert when a change detection result indicates
    significant changes based on configured thresholds.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        is_active: bool = True,
        change_threshold_percent: float = 5.0, # Default 5% change
        severity_for_high_change: float = 25.0, # Threshold for HIGH severity (%)
        severity_for_critical_change: float = 50.0, # Threshold for CRITICAL severity (%)
        check_feature_count: bool = True,
        check_area: bool = False, # Optional: Check area changes
        check_geometry: bool = False, # Optional: Check geometry changes (e.g., centroid displacement)
        default_severity: str = AlertSeverity.MEDIUM
    ):
        super().__init__(name, description, is_active, default_severity)
        self.change_threshold_percent = change_threshold_percent
        self.severity_for_high_change = severity_for_high_change
        self.severity_for_critical_change = severity_for_critical_change
        self.check_feature_count = check_feature_count
        self.check_area = check_area
        self.check_geometry = check_geometry

    def evaluate(self, context: Dict[str, Any]) -> AlertTriggerEvaluationResult:
        """
        Evaluates if a ChangeDetectionResult indicates a significant change.

        Args:
            context (Dict[str, Any]): Must contain 'change_result' key with a ChangeDetectionResult instance.

        Returns:
            AlertTriggerEvaluationResult: Result indicating if an alert should be triggered.
        """
        if not self.is_active:
            self.logger.debug(f"Trigger {self.name} is inactive. Skipping evaluation.")
            return AlertTriggerEvaluationResult(should_trigger=False)

        change_result: Optional[ChangeDetectionResult] = context.get('change_result')
        if not change_result:
            self.logger.warning(f"Missing 'change_result' in context for trigger {self.name}. Evaluation skipped.")
            return AlertTriggerEvaluationResult(should_trigger=False)

        # Use the 'has_changes' and 'exceeds_threshold' flags from ChangeDetectionResult
        # as primary indicators. This assumes the monitoring process already determined significance.
        if not change_result.has_changes:
            self.logger.debug(f"No changes detected in result {change_result.id} for trigger {self.name}.")
            return AlertTriggerEvaluationResult(should_trigger=False)

        if not change_result.exceeds_threshold:
             self.logger.debug(f"Changes in result {change_result.id} do not exceed threshold for trigger {self.name}.")
             return AlertTriggerEvaluationResult(should_trigger=False)

        # If ChangeDetectionResult says there are significant changes, trigger the alert.
        # The severity can be derived from the change result itself or recalculated here.
        # Let's derive severity based on feature_count_change_percent for example.
        change_percent = abs(change_result.feature_count_change_percent) if change_result.feature_count_change_percent is not None else 0.0

        severity = self.default_severity
        if change_percent >= self.severity_for_critical_change:
            severity = AlertSeverity.CRITICAL
        elif change_percent >= self.severity_for_high_change:
            severity = AlertSeverity.HIGH
        elif change_percent >= self.change_threshold_percent:
            severity = AlertSeverity.MEDIUM # Or keep default
        else:
            # This case should ideally not happen if ChangeDetectionResult correctly sets exceeds_threshold
            # But it's good defensive programming.
            self.logger.info(f"Change percent {change_percent}% below trigger threshold {self.change_threshold_percent}% for result {change_result.id}.")
            severity = self.default_severity # Fallback

        # Prepare context and metadata for the alert
        alert_context = {
            'service': change_result.layer.service if change_result.layer else None,
            'layer': change_result.layer,
            'affected_features_count': change_result.total_features_affected,
            'change_percentage': change_result.feature_count_change_percent,
            'feature_count_change': change_result.feature_count_change,
            'area_change': change_result.area_change,
            'centroid_displacement': change_result.centroid_displacement,
        }
        alert_metadata = {
            'trigger_name': self.name,
            'change_result_id': str(change_result.id),
            'algorithm_used': change_result.algorithm_used,
            'confidence_score': change_result.confidence_score,
            'change_types': change_result.change_types,
            'calculated_change_percent': change_percent,
        }

        self.logger.info(
            f"Change trigger '{self.name}' fired for layer {change_result.layer.name} "
            f"(Change: {change_percent:.2f}%, Severity: {severity})."
        )

        return AlertTriggerEvaluationResult(
            should_trigger=True,
            context=alert_context,
            severity=severity,
            metadata=alert_metadata
        )

    def get_alert_data(self, evaluation_result: AlertTriggerEvaluationResult) -> Dict[str, Any]:
        """
        Overrides base method to provide change-specific alert data.
        """
        base_data = super().get_alert_data(evaluation_result)
        # Override category
        base_data['category'] = AlertCategory.CHANGE_DETECTION
        # Add specific data from context
        base_data.update(evaluation_result.context)
        # Add title based on context
        layer = evaluation_result.context.get('layer')
        layer_name = layer.name if layer else "Unknown Layer"
        change_percent = evaluation_result.context.get('change_percentage', 0)
        base_data['title'] = f"Significant Change Detected in {layer_name} ({change_percent:.1f}%)"
        base_data['description'] = (
            f"A significant change ({change_percent:.1f}%) was detected in layer '{layer_name}'. "
            f"Features affected: {evaluation_result.context.get('affected_features_count', 'N/A')}."
        )
        return base_data

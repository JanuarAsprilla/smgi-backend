# apps/alerts/triggers/threshold_trigger.py
"""
SMGI Backend - Threshold Alert Trigger
Sistema de Monitoreo Geoespacial Inteligente

Trigger for alerts based on exceeding configured threshold values.
This can be used for various metrics like performance counters, data quality scores, etc.
"""
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable, Union
from apps.alerts.triggers.base_trigger import BaseAlertTrigger, AlertTriggerEvaluationResult
from apps.alerts.models import AlertSeverity, AlertCategory

logger = logging.getLogger('apps.alerts.triggers.threshold')


class ThresholdOperator(Enum):
    """Operators for comparing values against thresholds."""
    GREATER_THAN = 'gt'
    LESS_THAN = 'lt'
    GREATER_THAN_OR_EQUAL = 'gte'
    LESS_THAN_OR_EQUAL = 'lte'
    EQUAL = 'eq'
    NOT_EQUAL = 'ne'

    def evaluate(self, value: float, threshold: float) -> bool:
        """Evaluate the comparison."""
        if self == ThresholdOperator.GREATER_THAN:
            return value > threshold
        elif self == ThresholdOperator.LESS_THAN:
            return value < threshold
        elif self == ThresholdOperator.GREATER_THAN_OR_EQUAL:
            return value >= threshold
        elif self == ThresholdOperator.LESS_THAN_OR_EQUAL:
            return value <= threshold
        elif self == ThresholdOperator.EQUAL:
            return value == threshold
        elif self == ThresholdOperator.NOT_EQUAL:
            return value != threshold
        else:
            raise ValueError(f"Unsupported operator: {self}")


class ThresholdAlertTrigger(BaseAlertTrigger):
    """
    Trigger that fires an alert when a specified metric value crosses a threshold.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        is_active: bool = True,
        metric_name: str = "value", # Name of the metric being checked (for context/alert title)
        value_getter: Optional[Callable[[Dict[str, Any]], float]] = None, # Function to extract value from context
        value_key: Optional[str] = None, # Key in context dict to get the value (alternative to value_getter)
        operator: Union[str, ThresholdOperator] = ThresholdOperator.GREATER_THAN,
        threshold_value: float = 0.0,
        severity_levels: Optional[Dict[str, float]] = None, # e.g., {'HIGH': 80.0, 'CRITICAL': 95.0}
        default_severity: str = AlertSeverity.MEDIUM,
        category: str = AlertCategory.SYSTEM_HEALTH # Default category
    ):
        super().__init__(name, description, is_active, default_severity)
        self.metric_name = metric_name
        self.value_getter = value_getter
        self.value_key = value_key
        self.operator = ThresholdOperator(operator) if isinstance(operator, str) else operator
        self.threshold_value = threshold_value
        self.severity_levels = severity_levels or {}
        self.category = category

        if not self.value_getter and not self.value_key:
            raise ValueError("Either 'value_getter' function or 'value_key' string must be provided.")

    def evaluate(self, context: Dict[str, Any]) -> AlertTriggerEvaluationResult:
        """
        Evaluates if a metric value in the context meets the threshold condition.

        Args:
            context (Dict[str, Any]): Dictionary containing the metric value.
                                      Must contain the key specified by `value_key` or be processable
                                      by `value_getter`.

        Returns:
            AlertTriggerEvaluationResult: Result indicating if an alert should be triggered.
        """
        if not self.is_active:
            self.logger.debug(f"Trigger {self.name} is inactive. Skipping evaluation.")
            return AlertTriggerEvaluationResult(should_trigger=False)

        try:
            # Get the value to evaluate
            if self.value_getter:
                current_value = self.value_getter(context)
            elif self.value_key and self.value_key in context:
                current_value = context[self.value_key]
            else:
                raise KeyError(f"Value key '{self.value_key}' not found in context or no getter provided.")

            # Ensure value is numeric
            current_value = float(current_value)

            # Evaluate threshold condition
            is_triggered = self.operator.evaluate(current_value, self.threshold_value)

            if not is_triggered:
                self.logger.debug(
                    f"Metric '{self.metric_name}' ({current_value}) did not meet condition "
                    f"'{self.operator.value}' {self.threshold_value} for trigger {self.name}."
                )
                return AlertTriggerEvaluationResult(should_trigger=False)

            # Determine severity based on value and severity_levels
            severity = self.default_severity
            sorted_levels = sorted(self.severity_levels.items(), key=lambda item: item[1], reverse=True) # Sort by threshold descending
            for level_name, level_threshold in sorted_levels:
                # Assume severity levels are for 'exceeding' a value (e.g., HIGH if > 80)
                # Adjust logic if operator is LT/LTE
                level_operator = ThresholdOperator.GREATER_THAN_OR_EQUAL
                if level_operator.evaluate(current_value, level_threshold):
                     severity = level_name
                     break # First match (highest threshold met) wins

            # Prepare context and metadata
            alert_context = {
                'metric_name': self.metric_name,
                'current_value': current_value,
                'threshold_value': self.threshold_value,
                'operator': self.operator.value,
            }
            # Attempt to get service/layer from context if available
            alert_context['service'] = context.get('service')
            alert_context['layer'] = context.get('layer')

            alert_metadata = {
                'trigger_name': self.name,
                'evaluated_at': context.get('evaluated_at'), # Timestamp if provided
                'additional_context_keys': list(context.keys()),
            }

            self.logger.info(
                f"Threshold trigger '{self.name}' fired for metric '{self.metric_name}'. "
                f"Value: {current_value}, Condition: '{self.operator.value}' {self.threshold_value}, Severity: {severity}."
            )

            return AlertTriggerEvaluationResult(
                should_trigger=True,
                context=alert_context,
                severity=severity,
                metadata=alert_metadata
            )

        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Error evaluating threshold trigger {self.name}: {e}")
            # Depending on policy, could return False or raise
            return AlertTriggerEvaluationResult(should_trigger=False)
        except Exception as e:
            self.logger.error(f"Unexpected error in threshold trigger {self.name} evaluation: {e}")
            return AlertTriggerEvaluationResult(should_trigger=False)

    def get_alert_data(self, evaluation_result: AlertTriggerEvaluationResult) -> Dict[str, Any]:
        """
        Overrides base method to provide threshold-specific alert data.
        """
        base_data = super().get_alert_data(evaluation_result)
        # Override category
        base_data['category'] = self.category
        # Add specific data from context
        base_data.update(evaluation_result.context)
        # Add title based on context
        metric_name = evaluation_result.context.get('metric_name', 'Metric')
        current_value = evaluation_result.context.get('current_value', 'N/A')
        threshold_value = evaluation_result.context.get('threshold_value', 'N/A')
        operator = evaluation_result.context.get('operator', 'N/A')
        base_data['title'] = f"Threshold Breached: {metric_name}"
        base_data['description'] = (
            f"Metric '{metric_name}' value ({current_value}) breached threshold "
            f"('{operator}' {threshold_value})."
        )
        return base_data

# --- Ejemplo de uso (no incluido en el archivo final) ---
# def get_cpu_usage(context):
#     return context.get('system_metrics', {}).get('cpu_percent', 0)
#
# cpu_trigger = ThresholdAlertTrigger(
#     name="High CPU Usage",
#     metric_name="CPU Usage (%)",
#     value_getter=get_cpu_usage,
#     operator=ThresholdOperator.GREATER_THAN,
#     threshold_value=85.0,
#     severity_levels={AlertSeverity.HIGH: 85.0, AlertSeverity.CRITICAL: 95.0},
#     default_severity=AlertSeverity.MEDIUM,
#     category=AlertCategory.SYSTEM_HEALTH
# )
#
# context = {'system_metrics': {'cpu_percent': 90.5}, 'evaluated_at': timezone.now()}
# result = cpu_trigger.evaluate(context)
# if result.should_trigger:
#     alert_data = cpu_trigger.get_alert_data(result)
#     # Crear Alert con alert_data...

# apps/alerts/triggers/base_trigger.py
"""
SMGI Backend - Base Alert Trigger
Sistema de Monitoreo Geoespacial Inteligente

Defines the base class and interface for alert triggers.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from django.utils.translation import gettext_lazy as _
from apps.alerts.models import Alert, AlertSeverity, AlertCategory

logger = logging.getLogger('apps.alerts.triggers')


class AlertTriggerEvaluationResult:
    """
    Encapsulates the result of evaluating an AlertTrigger.
    """
    def __init__(self, should_trigger: bool, context: Optional[Dict[str, Any]] = None, severity: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.should_trigger = should_trigger
        self.context = context or {}
        self.severity = severity
        self.metadata = metadata or {}


class BaseAlertTrigger(ABC):
    """
    Abstract base class for all alert triggers.
    Defines the interface that specific triggers must implement.
    """

    def __init__(self, name: str, description: str = "", is_active: bool = True, default_severity: str = AlertSeverity.MEDIUM):
        self.name = name
        self.description = description
        self.is_active = is_active
        self.default_severity = default_severity
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> AlertTriggerEvaluationResult:
        """
        Evaluates the trigger condition based on the provided context.

        Args:
            context (Dict[str, Any]): A dictionary containing data relevant to the trigger evaluation.
                                      The structure depends on the specific trigger type.
                                      Common keys might include 'service', 'layer', 'current_value',
                                      'previous_value', 'snapshot', 'monitoring_result', etc.

        Returns:
            AlertTriggerEvaluationResult: The result of the evaluation indicating whether
                                           an alert should be triggered and associated data.
        """
        pass

    def get_alert_data(self, evaluation_result: AlertTriggerEvaluationResult) -> Dict[str, Any]:
        """
        Provides default data for creating an Alert instance based on the evaluation result.
        Subclasses can override this to provide trigger-specific alert data.

        Args:
            evaluation_result (AlertTriggerEvaluationResult): The result from evaluate().

        Returns:
            Dict[str, Any]: A dictionary of data suitable for Alert model instantiation.
        """
        alert_data = {
            'title': f"Alert from {self.name}",
            'description': self.description or f"Trigger '{self.name}' condition met.",
            'severity': evaluation_result.severity or self.default_severity,
            'category': AlertCategory.SYSTEM_HEALTH, # Default, subclasses should ideally set this
            'metadata': evaluation_result.metadata,
            # Specific triggers should populate 'service', 'layer', 'affected_features_count', etc.
        }
        # Merge context data into alert_data if needed, or let the caller handle it
        # alert_data.update(evaluation_result.context)
        return alert_data

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.name}>"

    def __repr__(self):
        return self.__str__()

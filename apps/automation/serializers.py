"""
Serializers for Automation app.
"""
from rest_framework import serializers
from .models import (
    Workflow,
    WorkflowTask,
    WorkflowExecution,
    TaskExecution,
    AutomationRule,
    WorkflowSchedule
)


class WorkflowTaskSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowTask model."""
    
    class Meta:
        model = WorkflowTask
        fields = [
            'id',
            'workflow',
            'name',
            'description',
            'task_type',
            'configuration',
            'order',
            'depends_on',
            'timeout_minutes',
            'retry_on_failure',
            'continue_on_failure',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class WorkflowSerializer(serializers.ModelSerializer):
    """Serializer for Workflow model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    task_count = serializers.SerializerMethodField()
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Workflow
        fields = [
            'id',
            'name',
            'description',
            'status',
            'workflow_definition',
            'trigger_type',
            'trigger_config',
            'timeout_minutes',
            'retry_count',
            'execution_count',
            'success_count',
            'failure_count',
            'success_rate',
            'last_execution',
            'tags',
            'metadata',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
            'task_count',
        ]
        read_only_fields = [
            'id',
            'execution_count',
            'success_count',
            'failure_count',
            'last_execution',
            'created_at',
            'updated_at'
        ]
    
    def get_task_count(self, obj):
        """Get number of tasks in this workflow."""
        return obj.tasks.filter(is_active=True).count()


class WorkflowDetailSerializer(WorkflowSerializer):
    """Detailed serializer for Workflow with tasks."""
    tasks = WorkflowTaskSerializer(many=True, read_only=True)
    
    class Meta(WorkflowSerializer.Meta):
        fields = WorkflowSerializer.Meta.fields + ['tasks']


class TaskExecutionSerializer(serializers.ModelSerializer):
    """Serializer for TaskExecution model."""
    task_name = serializers.CharField(source='task.name', read_only=True)
    duration = serializers.ReadOnlyField()
    
    class Meta:
        model = TaskExecution
        fields = [
            'id',
            'workflow_execution',
            'task',
            'task_name',
            'status',
            'started_at',
            'completed_at',
            'duration',
            'input_data',
            'output_data',
            'logs',
            'error_message',
            'retry_count',
        ]
        read_only_fields = ['id', 'started_at', 'completed_at']


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowExecution model."""
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    duration = serializers.ReadOnlyField()
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id',
            'workflow',
            'workflow_name',
            'status',
            'started_at',
            'completed_at',
            'duration',
            'input_data',
            'output_data',
            'trigger_source',
            'trigger_data',
            'logs',
            'error_message',
            'tasks_total',
            'tasks_completed',
            'tasks_failed',
            'progress',
            'task_id',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'started_at',
            'completed_at',
            'output_data',
            'logs',
            'error_message',
            'tasks_total',
            'tasks_completed',
            'tasks_failed',
            'task_id',
            'created_at'
        ]
    
    def get_progress(self, obj):
        """Calculate execution progress percentage."""
        if obj.tasks_total == 0:
            return 0.0
        return round((obj.tasks_completed / obj.tasks_total) * 100, 2)


class WorkflowExecutionDetailSerializer(WorkflowExecutionSerializer):
    """Detailed serializer for WorkflowExecution with task executions."""
    task_executions = TaskExecutionSerializer(many=True, read_only=True)
    
    class Meta(WorkflowExecutionSerializer.Meta):
        fields = WorkflowExecutionSerializer.Meta.fields + ['task_executions']


class AutomationRuleSerializer(serializers.ModelSerializer):
    """Serializer for AutomationRule model."""
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AutomationRule
        fields = [
            'id',
            'name',
            'description',
            'status',
            'trigger_event',
            'conditions',
            'workflow',
            'workflow_name',
            'workflow_input',
            'monitors',
            'data_sources',
            'throttle_minutes',
            'trigger_count',
            'last_triggered',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'trigger_count', 'last_triggered', 'created_at', 'updated_at']


class WorkflowScheduleSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowSchedule model."""
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = WorkflowSchedule
        fields = [
            'id',
            'workflow',
            'workflow_name',
            'name',
            'description',
            'schedule_type',
            'interval_minutes',
            'cron_expression',
            'scheduled_time',
            'input_data',
            'is_enabled',
            'is_active',
            'last_run',
            'next_run',
            'run_count',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_run', 'next_run', 'run_count', 'created_at', 'updated_at']


class AutomationStatisticsSerializer(serializers.Serializer):
    """Serializer for automation statistics."""
    total_workflows = serializers.IntegerField()
    active_workflows = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    running_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    average_success_rate = serializers.FloatField()
    recent_executions = serializers.ListField()
    top_workflows = serializers.ListField()

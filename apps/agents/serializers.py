"""
Serializers for Agents app.
"""
from rest_framework import serializers
from .models import (
    AgentCategory,
    Agent,
    AgentExecution,
    AgentSchedule,
    AgentRating,
    AgentTemplate
)
from .validators import validate_parameters


class AgentCategorySerializer(serializers.ModelSerializer):
    """Serializer for AgentCategory model."""
    agent_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentCategory
        fields = [
            'id',
            'name',
            'description',
            'icon',
            'color',
            'is_active',
            'created_at',
            'agent_count',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_agent_count(self, obj) -> int:
        """Get number of agents in this category."""
        return obj.agents.filter(is_active=True, status='published').count()


class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent model."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Agent
        fields = [
            'id',
            'name',
            'description',
            'category',
            'category_name',
            'agent_type',
            'version',
            'status',
            'parameters_schema',
            'default_parameters',
            'tags',
            'execution_count',
            'success_count',
            'failure_count',
            'success_rate',
            'is_public',
            'is_verified',
            'downloads',
            'rating',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'execution_count',
            'success_count',
            'failure_count',
            'downloads',
            'rating',
            'is_verified',
            'created_at',
            'updated_at'
        ]


class AgentDetailSerializer(AgentSerializer):
    """Detailed serializer for Agent with code."""
    category = AgentCategorySerializer(read_only=True)
    
    class Meta(AgentSerializer.Meta):
        fields = AgentSerializer.Meta.fields + [
            'code',
            'requirements',
            'metadata',
        ]


class AgentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating agents."""
    
    class Meta:
        model = Agent
        fields = [
            'name',
            'description',
            'category',
            'agent_type',
            'version',
            'code',
            'requirements',
            'parameters_schema',
            'default_parameters',
            'tags',
            'metadata',
        ]


class AgentExecutionSerializer(serializers.ModelSerializer):
    """Serializer for AgentExecution model."""
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    duration = serializers.ReadOnlyField()
    
    class Meta:
        model = AgentExecution
        fields = [
            'id',
            'agent',
            'agent_name',
            'name',
            'parameters',
            'status',
            'started_at',
            'completed_at',
            'duration',
            'output_data',
            'output_layers',
            'logs',
            'error_message',
            'processing_time',
            'memory_usage',
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
            'output_layers',
            'logs',
            'error_message',
            'processing_time',
            'memory_usage',
            'task_id',
            'created_at'
        ]


class AgentExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating agent executions."""
    
    class Meta:
        model = AgentExecution
        fields = [
            'agent',
            'name',
            'input_layers',
            'input_datasets',
            'parameters',
        ]
    
    def validate(self, data):
        """Validate execution data."""
        agent = data.get('agent')
        parameters = data.get('parameters', {})
        
        # Validate parameters against agent schema
        if agent and agent.parameters_schema:
            try:
                validate_parameters(parameters, agent.parameters_schema)
            except serializers.ValidationError:
                raise
            except Exception as e:
                raise serializers.ValidationError({
                    'parameters': f'Error validando parámetros: {str(e)}'
                })
        
        return data


class AgentScheduleSerializer(serializers.ModelSerializer):
    """Serializer for AgentSchedule model."""
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AgentSchedule
        fields = [
            'id',
            'agent',
            'agent_name',
            'name',
            'description',
            'schedule_type',
            'interval_minutes',
            'cron_expression',
            'scheduled_time',
            'input_layers',
            'input_datasets',
            'parameters',
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
        read_only_fields = [
            'id',
            'last_run',
            'next_run',
            'run_count',
            'created_at',
            'updated_at'
        ]
    
    def validate(self, data):
        """Validate schedule configuration based on type."""
        schedule_type = data.get('schedule_type')
        
        if schedule_type == 'interval' and not data.get('interval_minutes'):
            raise serializers.ValidationError({
                'interval_minutes': 'Este campo es requerido para tipo interval.'
            })
        
        if schedule_type == 'cron' and not data.get('cron_expression'):
            raise serializers.ValidationError({
                'cron_expression': 'Este campo es requerido para tipo cron.'
            })
        
        if schedule_type == 'once' and not data.get('scheduled_time'):
            raise serializers.ValidationError({
                'scheduled_time': 'Este campo es requerido para tipo once.'
            })
        
        return data


class AgentRatingSerializer(serializers.ModelSerializer):
    """Serializer for AgentRating model."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AgentRating
        fields = [
            'id',
            'agent',
            'user',
            'user_username',
            'rating',
            'comment',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AgentRatingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating agent ratings."""
    
    class Meta:
        model = AgentRating
        fields = ['agent', 'rating', 'comment']
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5."""
        if value < 1 or value > 5:
            raise serializers.ValidationError('La calificación debe estar entre 1 y 5.')
        return value


class AgentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for AgentTemplate model."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AgentTemplate
        fields = [
            'id',
            'name',
            'description',
            'category',
            'category_name',
            'agent_type',
            'code_template',
            'parameters_schema',
            'default_parameters',
            'tags',
            'thumbnail',
            'usage_count',
            'is_featured',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'usage_count', 'created_at']


class AgentStatisticsSerializer(serializers.Serializer):
    """Serializer for agent statistics."""
    total_agents = serializers.IntegerField()
    public_agents = serializers.IntegerField()
    verified_agents = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    average_success_rate = serializers.FloatField()
    most_used_agents = serializers.ListField()
    executions_by_type = serializers.DictField()

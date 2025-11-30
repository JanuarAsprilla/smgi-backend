"""
Helper functions and utilities for Agents app.
"""
from typing import Dict, List, Any, Optional
import re
from datetime import datetime, timedelta
from django.utils import timezone


def format_execution_time(seconds: float) -> str:
    """
    Format execution time in human-readable format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted string (e.g., "2m 30s", "1h 15m")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_memory_size(mb: float) -> str:
    """
    Format memory size in human-readable format.
    
    Args:
        mb: Memory in MB
        
    Returns:
        Formatted string (e.g., "512 MB", "2.5 GB")
    """
    if mb < 1024:
        return f"{mb:.0f} MB"
    else:
        gb = mb / 1024
        return f"{gb:.1f} GB"


def sanitize_agent_code(code: str) -> str:
    """
    Sanitize agent code by removing potentially dangerous patterns.
    
    Args:
        code: Python code string
        
    Returns:
        Sanitized code
    """
    # Remove comments that might hide malicious code
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    
    # Remove excessive whitespace
    code = '\n'.join(line.rstrip() for line in code.splitlines())
    
    return code.strip()


def extract_imports(code: str) -> List[str]:
    """
    Extract all import statements from code.
    
    Args:
        code: Python code string
        
    Returns:
        List of imported module names
    """
    imports = []
    
    # Find 'import module' statements
    import_pattern = r'^\s*import\s+(\w+)'
    for match in re.finditer(import_pattern, code, re.MULTILINE):
        imports.append(match.group(1))
    
    # Find 'from module import' statements
    from_pattern = r'^\s*from\s+(\w+)\s+import'
    for match in re.finditer(from_pattern, code, re.MULTILINE):
        imports.append(match.group(1))
    
    return list(set(imports))


def calculate_success_rate(success_count: int, failure_count: int) -> float:
    """
    Calculate success rate percentage.
    
    Args:
        success_count: Number of successful executions
        failure_count: Number of failed executions
        
    Returns:
        Success rate as percentage (0-100)
    """
    total = success_count + failure_count
    if total == 0:
        return 0.0
    return (success_count / total) * 100


def estimate_execution_time(agent, parameters: Dict[str, Any] = None) -> Optional[float]:
    """
    Estimate execution time based on historical data.
    
    Args:
        agent: Agent instance
        parameters: Execution parameters
        
    Returns:
        Estimated time in seconds, or None if no data
    """
    from django.db.models import Avg
    from .models import AgentExecution
    
    # Get recent successful executions
    recent_executions = AgentExecution.objects.filter(
        agent=agent,
        status='success',
        processing_time__isnull=False
    ).order_by('-created_at')[:10]
    
    if not recent_executions.exists():
        return None
    
    avg_time = recent_executions.aggregate(
        avg=Avg('processing_time')
    )['avg']
    
    return avg_time


def get_next_schedule_run(schedule) -> Optional[datetime]:
    """
    Calculate next scheduled run time.
    
    Args:
        schedule: AgentSchedule instance
        
    Returns:
        Next run datetime, or None if disabled
    """
    if not schedule.is_enabled:
        return None
    
    from .utils import calculate_next_run
    return calculate_next_run(schedule)


def format_cron_description(cron_expression: str) -> str:
    """
    Convert cron expression to human-readable description.
    
    Args:
        cron_expression: Cron expression string
        
    Returns:
        Human-readable description
    """
    try:
        from cron_descriptor import get_description
        return get_description(cron_expression)
    except Exception:
        return cron_expression


def validate_schedule_time(scheduled_time: datetime) -> bool:
    """
    Validate that scheduled time is in the future.
    
    Args:
        scheduled_time: Datetime to validate
        
    Returns:
        True if valid, False otherwise
    """
    return scheduled_time > timezone.now()


def get_agent_complexity_score(agent) -> int:
    """
    Calculate complexity score for an agent (1-10).
    
    Args:
        agent: Agent instance
        
    Returns:
        Complexity score (1=simple, 10=complex)
    """
    score = 1
    
    # Code length
    code_lines = len(agent.code.splitlines())
    if code_lines > 50:
        score += 2
    elif code_lines > 20:
        score += 1
    
    # Number of parameters
    param_count = len(agent.parameters_schema.get('properties', {}))
    if param_count > 5:
        score += 2
    elif param_count > 2:
        score += 1
    
    # Requirements
    if len(agent.requirements) > 3:
        score += 2
    elif len(agent.requirements) > 0:
        score += 1
    
    # Imports
    imports = extract_imports(agent.code)
    if len(imports) > 5:
        score += 2
    elif len(imports) > 2:
        score += 1
    
    return min(score, 10)


def get_recommended_agents(user, limit: int = 5) -> List:
    """
    Get recommended agents for a user.
    
    Args:
        user: User instance
        limit: Maximum number of recommendations
        
    Returns:
        List of recommended Agent instances
    """
    from .models import Agent
    
    # For now, just return top-rated public agents
    # TODO: Implement ML-based recommendations
    return Agent.objects.filter(
        is_public=True,
        status='published',
        is_active=True
    ).order_by('-rating', '-execution_count')[:limit]


def parse_agent_tags(tags_input: str) -> List[str]:
    """
    Parse tags from comma-separated string.
    
    Args:
        tags_input: Comma-separated tags
        
    Returns:
        List of cleaned tag strings
    """
    if not tags_input:
        return []
    
    tags = [tag.strip() for tag in tags_input.split(',')]
    tags = [tag for tag in tags if tag]  # Remove empty
    tags = list(set(tags))  # Remove duplicates
    
    return tags[:10]  # Limit to 10 tags


def generate_agent_slug(name: str) -> str:
    """
    Generate URL-friendly slug from agent name.
    
    Args:
        name: Agent name
        
    Returns:
        URL-safe slug
    """
    import unicodedata
    
    # Normalize unicode characters
    slug = unicodedata.normalize('NFKD', name)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase and replace spaces
    slug = slug.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    
    return slug[:50]  # Limit length

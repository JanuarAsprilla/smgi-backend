"""
Configuration file for Agents app.
Place this in your Django settings or load from environment.
"""

# Agent execution settings
AGENT_EXECUTION_TIMEOUT = 1800  # 30 minutes (in seconds)
AGENT_MEMORY_LIMIT = 512  # Memory limit in MB
AGENT_MAX_CODE_LENGTH = 10000  # Maximum characters in agent code
AGENT_MAX_CONCURRENT_EXECUTIONS = 5  # Per user

# Cleanup settings
AGENT_EXECUTION_RETENTION_DAYS = 30  # Days to keep old executions
AGENT_AUTO_CLEANUP_ENABLED = True

# Security settings
AGENT_ENABLE_CODE_VALIDATION = True
AGENT_ENABLE_IMPORT_RESTRICTIONS = True
AGENT_ENABLE_SANDBOX = True

# Allowed imports for agent code (whitelist)
AGENT_ALLOWED_IMPORTS = [
    'logging',
    'json',
    'datetime',
    'math',
    'statistics',
    'collections',
    're',
    'numpy',
    'pandas',
    'geopandas',
    'shapely',
]

# Marketplace settings
AGENT_MARKETPLACE_ENABLED = True
AGENT_REQUIRE_VERIFICATION = False  # Require admin verification for public agents

# Rating settings
AGENT_ENABLE_RATINGS = True
AGENT_MIN_RATING = 1
AGENT_MAX_RATING = 5

# Schedule settings
AGENT_SCHEDULE_ENABLED = True
AGENT_MIN_SCHEDULE_INTERVAL = 5  # Minimum minutes between executions

# Notification settings
AGENT_NOTIFY_ON_CREATION = True
AGENT_NOTIFY_ON_PUBLISH = True
AGENT_NOTIFY_ON_EXECUTION_COMPLETE = True
AGENT_NOTIFY_ON_EXECUTION_FAILED = True

# Statistics settings
AGENT_UPDATE_STATS_INTERVAL = 3600  # Update stats every hour (in seconds)
AGENT_CALCULATE_RATINGS_INTERVAL = 3600  # Recalculate ratings every hour

# API settings
AGENT_API_PAGE_SIZE = 20
AGENT_API_MAX_PAGE_SIZE = 100

# Template settings
AGENT_ENABLE_TEMPLATES = True
AGENT_MAX_TEMPLATES_PER_USER = 10

# Development settings (set to False in production)
AGENT_DEBUG_MODE = False
AGENT_VERBOSE_LOGGING = False

# Frontend URL (for email links)
FRONTEND_URL = 'http://localhost:3000'  # Update in production

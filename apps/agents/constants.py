"""
Constants for Agents app.
"""

# Agent Types
AGENT_TYPE_CHANGE_DETECTION = 'change_detection'
AGENT_TYPE_CLASSIFICATION = 'classification'
AGENT_TYPE_SEGMENTATION = 'segmentation'
AGENT_TYPE_PREDICTION = 'prediction'
AGENT_TYPE_STATISTICS = 'statistics'
AGENT_TYPE_CUSTOM = 'custom'

# Agent Status
AGENT_STATUS_DRAFT = 'draft'
AGENT_STATUS_PUBLISHED = 'published'
AGENT_STATUS_ARCHIVED = 'archived'

# Execution Status
EXECUTION_STATUS_PENDING = 'pending'
EXECUTION_STATUS_RUNNING = 'running'
EXECUTION_STATUS_SUCCESS = 'success'
EXECUTION_STATUS_FAILED = 'failed'
EXECUTION_STATUS_CANCELLED = 'cancelled'

# Schedule Types
SCHEDULE_TYPE_INTERVAL = 'interval'
SCHEDULE_TYPE_CRON = 'cron'
SCHEDULE_TYPE_ONCE = 'once'

# Default parameters
DEFAULT_EXECUTION_TIMEOUT = 1800  # 30 minutes
DEFAULT_MEMORY_LIMIT = 512  # MB
DEFAULT_CLEANUP_DAYS = 30

# Security restrictions
DANGEROUS_IMPORTS = [
    'subprocess',
    'os.system',
    'eval',
    'exec',
    '__import__',
    'open',
    'file',
    'input',
    'raw_input',
]

DANGEROUS_PACKAGES = [
    'os',
    'subprocess',
    'sys',
    'importlib',
    '__builtin__',
    'builtins',
]

# Allowed imports for agent code
ALLOWED_IMPORTS = [
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

# Rating limits
MIN_RATING = 1
MAX_RATING = 5

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Execution limits
MAX_CONCURRENT_EXECUTIONS = 5
MAX_EXECUTIONS_PER_USER_PER_DAY = 100

# Notification types
NOTIFICATION_AGENT_CREATED = 'agent_created'
NOTIFICATION_AGENT_PUBLISHED = 'agent_published'
NOTIFICATION_EXECUTION_SUCCESS = 'execution_success'
NOTIFICATION_EXECUTION_FAILED = 'execution_failed'
NOTIFICATION_SCHEDULE_ENABLED = 'schedule_enabled'
NOTIFICATION_SCHEDULE_DISABLED = 'schedule_disabled'

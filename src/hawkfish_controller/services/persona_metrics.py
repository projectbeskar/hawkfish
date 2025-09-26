"""
Metrics for persona system tracking.
"""

from prometheus_client import Counter, Histogram

# Persona request metrics
PERSONA_REQUESTS_TOTAL = Counter(
    'hawkfish_persona_requests_total',
    'Total number of requests to persona endpoints',
    ['persona', 'endpoint', 'method', 'status']
)

PERSONA_ERRORS_TOTAL = Counter(
    'hawkfish_persona_errors_total', 
    'Total number of persona endpoint errors',
    ['persona', 'endpoint', 'error_code']
)

PERSONA_RESPONSE_TIME = Histogram(
    'hawkfish_persona_response_seconds',
    'Response time for persona endpoints',
    ['persona', 'endpoint']
)

# HPE iLO specific metrics
ILO_VIRTUALMEDIA_OPERATIONS = Counter(
    'hawkfish_ilo_virtualmedia_operations_total',
    'Total VirtualMedia operations via iLO endpoints',
    ['operation', 'result']
)

ILO_CONSOLE_SESSIONS = Counter(
    'hawkfish_ilo_console_sessions_total',
    'Total console sessions created via iLO endpoints',
    ['protocol', 'result']
)

ILO_BIOS_OPERATIONS = Counter(
    'hawkfish_ilo_bios_operations_total',
    'Total BIOS operations via iLO endpoints',
    ['operation', 'apply_time', 'result']
)

ILO_JOBS_ACCESSED = Counter(
    'hawkfish_ilo_jobs_accessed_total',
    'Total HPE Jobs endpoint accesses',
    ['endpoint']
)

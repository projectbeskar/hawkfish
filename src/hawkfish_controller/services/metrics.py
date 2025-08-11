from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("hawkfish_requests_total", "Total HTTP requests", ["path", "method", "status"])
REQUEST_LATENCY = Histogram("hawkfish_request_latency_seconds", "Request latency", ["path", "method"])
TASK_DURATION = Histogram("hawkfish_task_duration_seconds", "Task durations", ["name"])
BYTES_DOWNLOADED = Counter("hawkfish_bytes_downloaded_total", "Downloaded bytes", ["source"]) 
POWER_ACTIONS = Counter("hawkfish_power_actions_total", "Power actions", ["reset_type", "result"]) 
MEDIA_ACTIONS = Counter("hawkfish_media_actions_total", "Media actions", ["action", "result"]) 
TASKS_CREATED = Counter("hawkfish_tasks_created_total", "Tasks created", ["name"]) 



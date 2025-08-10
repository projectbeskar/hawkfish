from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("hawkfish_requests_total", "Total HTTP requests", ["path", "method", "status"])
REQUEST_LATENCY = Histogram("hawkfish_request_latency_seconds", "Request latency", ["path", "method"])
TASK_DURATION = Histogram("hawkfish_task_duration_seconds", "Task durations", ["name"]) 
BYTES_DOWNLOADED = Counter("hawkfish_bytes_downloaded_total", "Downloaded bytes", ["source"]) 



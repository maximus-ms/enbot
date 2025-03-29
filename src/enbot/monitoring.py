"""Monitoring configuration for the bot."""
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Bot metrics
active_users = Gauge(
    "enbot_active_users",
    "Number of active users currently using the bot",
)

total_users = Counter(
    "enbot_total_users",
    "Total number of users who have interacted with the bot",
)

# Learning metrics
words_learned = Counter(
    "enbot_words_learned_total",
    "Total number of words learned by users",
    ["user_id"],
)

learning_sessions = Counter(
    "enbot_learning_sessions_total",
    "Total number of learning sessions started",
    ["user_id"],
)

session_duration = Histogram(
    "enbot_session_duration_seconds",
    "Duration of learning sessions in seconds",
    ["user_id"],
    buckets=[60, 300, 600, 1800, 3600],  # 1min, 5min, 10min, 30min, 1hour
)

# Word management metrics
words_added = Counter(
    "enbot_words_added_total",
    "Total number of words added to dictionaries",
    ["user_id"],
)

words_updated = Counter(
    "enbot_words_updated_total",
    "Total number of words updated in dictionaries",
    ["user_id"],
)

# Error metrics
error_count = Counter(
    "enbot_errors_total",
    "Total number of errors encountered",
    ["error_type"],
)

# Performance metrics
request_duration = Histogram(
    "enbot_request_duration_seconds",
    "Duration of bot requests in seconds",
    ["handler"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

# Database metrics
db_operations = Counter(
    "enbot_db_operations_total",
    "Total number of database operations",
    ["operation_type"],
)

db_errors = Counter(
    "enbot_db_errors_total",
    "Total number of database errors",
    ["error_type"],
)


def start_monitoring(port: int = 9090) -> None:
    """Start the Prometheus metrics server."""
    start_http_server(port) 
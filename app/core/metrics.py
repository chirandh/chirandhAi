from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)
COMPILE_OUTCOMES = Counter(
    "compile_jobs_total",
    "Compile job outcomes",
    ["status"],
)
LLM_CALLS = Counter(
    "llm_calls_total",
    "LLM API calls",
    ["model", "outcome"],
)

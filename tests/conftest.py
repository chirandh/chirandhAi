import os

# Must run before `app` imports so Settings, rate limiter, and DB URL resolve for tests.
os.environ["ENVIRONMENT"] = "test"
os.environ["API_KEYS"] = "testkey"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = ""
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["S3_ENDPOINT_URL"] = ""

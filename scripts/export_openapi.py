#!/usr/bin/env python3
"""Emit OpenAPI 3.x JSON to stdout for Custom GPT Actions import."""

import json
import os
import sys

# Ensure non-test defaults when run manually
os.environ.setdefault("ENVIRONMENT", "development")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    schema = app.openapi()
    json.dump(schema, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

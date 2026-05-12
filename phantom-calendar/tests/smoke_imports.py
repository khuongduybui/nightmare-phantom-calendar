#!/usr/bin/env python3
"""Smoke test: verify all required packages can be imported."""

import sys

PACKAGES = [
    ("rumps", "rumps"),
    ("googleapiclient", "googleapiclient"),
    ("google_auth_oauthlib", "google_auth_oauthlib"),
    ("apscheduler", "apscheduler"),
    ("pytz", "pytz"),
    ("pyyaml", "yaml"),
]

failed = False
for display_name, module_name in PACKAGES:
    try:
        __import__(module_name)
        print(f"OK: {display_name}")
    except ImportError as exc:
        print(f"FAIL: {display_name} — {exc}", file=sys.stderr)
        failed = True

sys.exit(1 if failed else 0)

#!/usr/bin/env python3
"""
Smoke test against a running Gonghaebun API server.

Usage:
    python scripts/smoke_local.py
    python scripts/smoke_local.py --base-url http://0.0.0.0:8000

Exits 0 if all checks pass, 1 if any fail.
Requires no third-party libraries — stdlib urllib.request only.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from argparse import ArgumentParser


def check(label: str, url: str, expect_key: str | None = None, expect_value=None) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] {label}: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        return False

    if status != 200:
        print(f"  [FAIL] {label}: status {status}")
        return False

    if expect_key is not None:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print(f"  [FAIL] {label}: response is not JSON")
            return False
        if data.get(expect_key) != expect_value:
            print(f"  [FAIL] {label}: expected {expect_key}={expect_value!r}, got {data.get(expect_key)!r}")
            return False

    print(f"  [PASS] {label}")
    return True


def main() -> int:
    parser = ArgumentParser(description="Smoke test the Gonghaebun API server.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running server (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Smoke testing: {base}\n")

    checks = [
        ("GET /api/health → status=ok",     f"{base}/api/health",         "status",  "ok"),
        ("GET /api/ready → ready=true",      f"{base}/api/ready",          "ready",   True),
        ("GET /api/project/status → 200",    f"{base}/api/project/status", None,      None),
        ("GET /api/sources → 200",           f"{base}/api/sources",        None,      None),
        ("GET /api/concepts → 200",          f"{base}/api/concepts",       None,      None),
        ("GET /api/weak → 200",              f"{base}/api/weak",           None,      None),
        ("GET /api/study/validate → 200",    f"{base}/api/study/validate", None,      None),
    ]

    results = [check(label, url, key, val) for label, url, key, val in checks]
    passed = sum(results)
    total = len(results)

    print(f"\n{passed}/{total} checks passed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

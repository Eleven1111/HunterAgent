#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log into the local HuntFlow API and print a bearer token for OpenClaw/Hermes.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="Base API URL")
    parser.add_argument("--email", default="owner@huntflow.local", help="Login email")
    parser.add_argument("--password", default="hunter-owner", help="Login password")
    parser.add_argument("--token-only", action="store_true", help="Print only the bearer token")
    parser.add_argument("--shell", action="store_true", help="Print shell exports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.dumps({"email": args.email, "password": args.password}).encode()
    request = urllib.request.Request(
        f"{args.api_url.rstrip('/')}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode() or exc.reason
        print(f"login failed: {detail}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"login failed: {exc}", file=sys.stderr)
        return 1

    token = body["access_token"]
    if args.token_only:
        print(token)
        return 0
    if args.shell:
        print(f'export HUNTFLOW_API_URL="{args.api_url.rstrip("/")}"')
        print(f'export HUNTFLOW_BEARER_TOKEN="{token}"')
        return 0
    print(
        json.dumps(
            {
                "api_url": args.api_url.rstrip("/"),
                "bearer_token": token,
                "user": body["user"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

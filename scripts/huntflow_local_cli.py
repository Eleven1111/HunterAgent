#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_EMAIL = os.getenv("HUNTFLOW_EMAIL", "owner@huntflow.local")
DEFAULT_PASSWORD = os.getenv("HUNTFLOW_PASSWORD", "hunter-owner")


def api_request(
    path: str,
    *,
    method: str = "GET",
    api_url: str,
    token: str | None = None,
    payload: dict | None = None,
) -> dict | list | str | None:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode() or exc.reason
        raise RuntimeError(detail) from exc
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def login(api_url: str, email: str, password: str) -> str:
    payload = api_request(
        "/api/v1/auth/login",
        method="POST",
        api_url=api_url,
        payload={"email": email, "password": password},
    )
    assert isinstance(payload, dict)
    return payload["access_token"]


def parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    for chunk in text.split("\n\n"):
        if chunk.startswith("data: "):
            events.append(json.loads(chunk[6:]))
    return events


def agent_chat(api_url: str, token: str, message: str, session_id: str) -> dict:
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/v1/agent/chat",
        data=json.dumps({"session_id": session_id, "message": message}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode() or exc.reason
        raise RuntimeError(detail) from exc
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc
    events = parse_sse(raw)
    assistant_text = "\n".join(event["content"] for event in events if event.get("type") == "text")
    render = next((event for event in events if event.get("type") == "render"), None)
    return {"text": assistant_text, "render": render, "events": events}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local HuntFlow CLI bridge for OpenClaw/Hermes.")
    parser.add_argument("--api-url", default=os.getenv("HUNTFLOW_API_URL", DEFAULT_API_URL))
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--token", default=os.getenv("HUNTFLOW_BEARER_TOKEN", ""))
    parser.add_argument("--session-id", default="local-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health")
    subparsers.add_parser("dashboard")
    subparsers.add_parser("today")
    subparsers.add_parser("login")

    score = subparsers.add_parser("score")
    score.add_argument("job_id")
    score.add_argument("candidate_id")

    draft = subparsers.add_parser("draft")
    draft.add_argument("job_id")
    draft.add_argument("candidate_id")

    create_client = subparsers.add_parser("create-client")
    create_client.add_argument("--name", required=True)
    create_client.add_argument("--industry", required=True)
    create_client.add_argument("--size", default=None)
    create_client.add_argument("--notes", default=None)

    create_job = subparsers.add_parser("create-job")
    create_job.add_argument("--client-id", required=True)
    create_job.add_argument("--title", required=True)
    create_job.add_argument("--level", default=None)
    create_job.add_argument("--jd", default=None)
    create_job.add_argument("--must-have", action="append", default=[])
    create_job.add_argument("--nice-to-have", action="append", default=[])

    import_candidate = subparsers.add_parser("import-candidate")
    import_candidate.add_argument("--job-order-id", default=None)
    import_candidate.add_argument("--full-name", required=True)
    import_candidate.add_argument("--resume-text", required=True)
    import_candidate.add_argument("--current-company", default=None)
    import_candidate.add_argument("--current-title", default=None)
    import_candidate.add_argument("--city", default=None)
    import_candidate.add_argument("--email-address", default=None)
    import_candidate.add_argument("--phone", default=None)

    return parser


def ensure_token(args: argparse.Namespace) -> str:
    return args.token or login(args.api_url, args.email, args.password)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "health":
            print(json.dumps(api_request("/health", api_url=args.api_url), indent=2))
            return 0
        if args.command == "login":
            print(ensure_token(args))
            return 0

        token = ensure_token(args)

        if args.command == "dashboard":
            print(json.dumps(api_request("/api/v1/dashboard/summary", api_url=args.api_url, token=token), indent=2))
            return 0
        if args.command == "today":
            print(json.dumps(agent_chat(args.api_url, token, "/today", args.session_id), indent=2))
            return 0
        if args.command == "score":
            print(json.dumps(agent_chat(args.api_url, token, f"/score {args.job_id} {args.candidate_id}", args.session_id), indent=2))
            return 0
        if args.command == "draft":
            print(json.dumps(agent_chat(args.api_url, token, f"/draft {args.job_id} {args.candidate_id}", args.session_id), indent=2))
            return 0
        if args.command == "create-client":
            payload = {
                "name": args.name,
                "industry": args.industry,
                "size": args.size,
                "notes": args.notes,
            }
            print(json.dumps(api_request("/api/v1/clients", method="POST", api_url=args.api_url, token=token, payload=payload), indent=2))
            return 0
        if args.command == "create-job":
            payload = {
                "client_id": args.client_id,
                "title": args.title,
                "level": args.level,
                "jd": args.jd,
                "must_have": args.must_have,
                "nice_to_have": args.nice_to_have,
            }
            print(json.dumps(api_request("/api/v1/job-orders", method="POST", api_url=args.api_url, token=token, payload=payload), indent=2))
            return 0
        if args.command == "import-candidate":
            payload = {
                "job_order_id": args.job_order_id,
                "full_name": args.full_name,
                "resume_text": args.resume_text,
                "current_company": args.current_company,
                "current_title": args.current_title,
                "city": args.city,
                "email": args.email_address,
                "phone": args.phone,
            }
            print(json.dumps(api_request("/api/v1/candidates/import", method="POST", api_url=args.api_url, token=token, payload=payload), indent=2))
            return 0
    except RuntimeError as exc:
        print(f"huntflow-local-cli: {exc}", file=sys.stderr)
        return 1

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Safe Ask client example.

A minimal client that routes LLM requests through the Safe Ask privacy
gateway. The gateway redacts PII before forwarding to the provider and
restores placeholders in the response.

Usage:
    export SAFEASK_URL=http://localhost:8787
    python ask.py "Your prompt here"
    echo "Your prompt" | python ask.py --tier frontier
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description="Ask a model through Safe Ask.")
    parser.add_argument(
        "--tier",
        choices=("flash", "frontier", "deep"),
        default="flash",
        help="Model tier: flash for routine, frontier for hard reasoning, deep for complex tasks",
    )
    parser.add_argument("--system", help="Optional system message")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("prompt", nargs="?", help="Prompt text (reads stdin if omitted)")
    args = parser.parse_args()

    base_url = os.getenv("SAFEASK_URL", "http://localhost:8787")

    prompt = args.prompt if args.prompt is not None else sys.stdin.read()

    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": args.tier,
        "messages": messages,
        "stream": False,
    }

    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    default_timeout = 1800 if args.tier == "deep" else 300

    try:
        with urllib.request.urlopen(req, timeout=args.timeout or default_timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"Safe Ask error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Connection error: {exc.reason}") from exc

    # Print any redaction warnings to stderr
    for warning in data.get("safe_ask_warnings", []):
        print("SAFE-ASK WARNING:", json.dumps(warning, ensure_ascii=False), file=sys.stderr)

    # Print the response content
    try:
        print(data["choices"][0]["message"]["content"])
    except (KeyError, TypeError):
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

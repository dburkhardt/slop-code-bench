#!/usr/bin/env python3
"""Lightweight reverse proxy that rewrites model names for NVIDIA NIM.

Claude Code CLI rejects model names like ``aws/anthropic/bedrock-claude-sonnet-4-6``
because they aren't in its internal allowlist.  The NVIDIA inference endpoint
rejects standard Anthropic model names like ``claude-sonnet-4-6``.

This proxy sits between Claude Code and the NVIDIA endpoint, rewriting the
model field in request bodies so both sides are happy.

Usage::

    python nvidia_proxy.py --port 8199 &
    ANTHROPIC_BASE_URL=http://127.0.0.1:8199/v1 \\
    ANTHROPIC_API_KEY=$NVIDIA_INFERENCE_KEY \\
    claude --model claude-sonnet-4-6 -p "hello"
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import urllib.request
import urllib.error

NVIDIA_BASE = "https://inference-api.nvidia.com"
LISTEN_PORT = int(os.environ.get("NVIDIA_PROXY_PORT", "8199"))

# Map Claude Code model names -> NVIDIA NIM model names
MODEL_MAP = {
    "claude-sonnet-4-6": "aws/anthropic/bedrock-claude-sonnet-4-6",
    "claude-sonnet-4-6-20250514": "aws/anthropic/bedrock-claude-sonnet-4-6",
    "claude-opus-4-6": "aws/anthropic/bedrock-claude-opus-4-6",
    "claude-opus-4-6-20250514": "aws/anthropic/bedrock-claude-opus-4-6",
    "claude-haiku-4-5": "aws/anthropic/bedrock-claude-haiku-4-5",
    "claude-haiku-4-5-20241022": "aws/anthropic/bedrock-claude-haiku-4-5",
    "claude-sonnet-4-5-20241022": "azure/anthropic/claude-sonnet-4-5",
    "claude-opus-4-5-20250514": "azure/anthropic/claude-opus-4-5",
}


def _strip_cache_control(data: dict) -> None:
    """Remove ``cache_control`` from messages and system blocks.

    The NVIDIA NIM endpoint returns 400 when it receives
    Anthropic-specific ``cache_control`` fields (e.g.
    ``{"type": "ephemeral", "scope": ...}``).  This
    function recursively strips them.
    """
    for msg in data.get("system", []):
        if isinstance(msg, dict):
            msg.pop("cache_control", None)
    for msg in data.get("messages", []):
        if isinstance(msg, dict):
            msg.pop("cache_control", None)
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block.pop("cache_control", None)


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        # Rewrite model name and strip unsupported params
        try:
            data = json.loads(body)
            original_model = data.get("model", "")
            if original_model in MODEL_MAP:
                data["model"] = MODEL_MAP[original_model]
            # Strip cache_control from system/messages
            # (NVIDIA NIM rejects Anthropic-specific
            # caching parameters).
            _strip_cache_control(data)
            body = json.dumps(data).encode()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        # Forward to NVIDIA endpoint
        target_url = f"{NVIDIA_BASE}{self.path}"
        headers = {}
        for key in self.headers:
            if key.lower() not in ("host", "content-length", "transfer-encoding"):
                headers[key] = self.headers[key]
        headers["Content-Length"] = str(len(body))

        req = urllib.request.Request(
            target_url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() not in (
                        "transfer-encoding",
                        "connection",
                        "content-length",
                    ):
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as exc:
            resp_body = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as exc:
            error = json.dumps({"error": str(exc)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error)))
            self.end_headers()
            self.wfile.write(error)

    def do_GET(self):
        target_url = f"{NVIDIA_BASE}{self.path}"
        headers = {}
        for key in self.headers:
            if key.lower() not in ("host",):
                headers[key] = self.headers[key]

        req = urllib.request.Request(target_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() not in (
                        "transfer-encoding",
                        "connection",
                        "content-length",
                    ):
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as exc:
            resp_body = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)

    def log_message(self, format, *args):
        # Suppress request logging
        pass


def start_proxy(port: int = LISTEN_PORT) -> HTTPServer:
    """Start the proxy server and return it."""
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


if __name__ == "__main__":
    port = LISTEN_PORT
    if len(sys.argv) > 1 and sys.argv[1] == "--port":
        port = int(sys.argv[2])
    print(f"NVIDIA model-name proxy listening on 0.0.0.0:{port}")
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

"""One bounded, authenticated loopback schema probe; never send model prompts."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import queue
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request


SELECTED = (
    "/permission", "/permission/{requestID}/reply",
    "/session/{sessionID}/permissions/{permissionID}",
    "/session", "/session/{sessionID}/prompt_async",
    "/session/{sessionID}/abort", "/session/status",
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_denied")


def shape(schema: object) -> object:
    """Retain public structural identifiers only, not examples/defaults/descriptions."""
    if not isinstance(schema, dict):
        return {}
    result = {}
    for key in ("type", "$ref"):
        value = schema.get(key)
        if isinstance(value, str) and len(value) < 200:
            result[key] = value
    properties = schema.get("properties")
    if isinstance(properties, dict):
        result["properties"] = {k: shape(v) for k, v in properties.items()}
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            result[key] = shape(schema[key])
    for key in ("oneOf", "anyOf", "allOf"):
        if isinstance(schema.get(key), list):
            result[key] = [shape(v) for v in schema[key]]
    if isinstance(schema.get("required"), list):
        result["required"] = schema["required"]
    return result


def summarize(document: object) -> dict:
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise ValueError("invalid_schema")
    selected = {}
    for path in SELECTED:
        methods = document["paths"].get(path)
        if not isinstance(methods, dict):
            continue
        operations = {}
        for method in ("get", "post"):
            operation = methods.get(method)
            if not isinstance(operation, dict):
                continue
            body = operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            responses = operation.get("responses", {})
            operations[method] = {
                "request": shape(body),
                "responses": {code: shape(value.get("content", {}).get("application/json", {}).get("schema", {}))
                              for code, value in responses.items()},
            }
        if any(any(operation["responses"].values()) for operation in operations.values()):
            selected[path] = operations
    if not selected:
        raise ValueError("no_selected_endpoints")
    return selected


def read_json(response, deadline: float) -> object:
    chunks = []
    size = 0
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError()
        # read1 performs at most one underlying read: a trickling response
        # cannot hide an unbounded sequence of socket reads inside read().
        chunk = response.read1(65536)
        if time.monotonic() >= deadline:
            raise TimeoutError()
        if not chunk:
            return json.loads(b"".join(chunks))
        size += len(chunk)
        if size > 8 * 1024 * 1024:
            raise ValueError("response_too_large")
        chunks.append(chunk)


def bounded_get(opener, request, deadline: float) -> object:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError()
    result = queue.Queue(maxsize=1)

    def fetch():
        try:
            with opener.open(request, timeout=min(2, remaining)) as response:
                result.put((True, read_json(response, deadline)))
        except Exception as error:
            result.put((False, error))

    # Bound headers as well as body reads. A stuck read cannot prevent the
    # main thread from terminating the owned server; no worker performs writes.
    threading.Thread(target=fetch, daemon=True).start()
    try:
        success, value = result.get(timeout=max(0, deadline - time.monotonic()))
    except queue.Empty:
        raise TimeoutError() from None
    if not success:
        raise value
    return value


def probe(executable: Path, expected_digest: str) -> dict:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != expected_digest or len(expected_digest) != 64:
        return {"decision": "denied_binary_digest"}
    # A freed ephemeral port may race; random authentication and health/version
    # verification prevent accepting another service. There is no spawn retry.
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    password = secrets.token_urlsafe(32)
    env = os.environ.copy()
    env["OPENCODE_SERVER_PASSWORD"] = password
    env["OPENCODE_SERVER_USERNAME"] = "opencode"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    authorization = "Basic " + base64.b64encode(("opencode:" + password).encode()).decode()
    # 33s I/O budget, up to 2s in the last socket read, 10s for teardown.
    deadline = time.monotonic() + 33
    child = None
    result = {"decision": "stopped_probe", "binary_sha256": digest}

    def get(path):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers={"Authorization": authorization})
        return bounded_get(opener, request, deadline)

    try:
        child = subprocess.Popen(
            [str(executable), "serve", "--pure", "--hostname", "127.0.0.1", "--port", str(port)],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        while child.poll() is None and time.monotonic() < deadline:
            try:
                health = get("/global/health")
                break
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.2)
        else:
            raise TimeoutError()
        if health != {"healthy": True, "version": "1.18.32"}:
            raise ValueError("unexpected_health")
        endpoints = summarize(get("/doc"))
        result.update(decision="schema_observed", version="1.18.32", endpoints=endpoints)
    except Exception as error:
        result["error_class"] = type(error).__name__
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    if os.name == "nt":
                        subprocess.run(["taskkill.exe", "/PID", str(child.pid), "/T", "/F"],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=5, check=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        child.terminate()
                child.wait(timeout=5)
                result["server_stopped"] = True
            except Exception:
                result["server_stopped"] = False
                result["decision"] = "stopped_teardown_failure"
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    output = probe(args.executable, args.sha256)
    print(json.dumps(output, ensure_ascii=True))
    raise SystemExit(0 if output["decision"] == "schema_observed" else 1)

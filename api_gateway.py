"""api-gateway: the only service of the frontend app that may call the backend app.

BACKEND_URL (and REVIEWS_URL, when the global config connects the reviews app) are set by the global
deployment: those apps run in another data center, and each address is the Linkerd mirror of their service in this
data center.
"""
import json
import os
import socket
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 3000
TIMEOUT_SECONDS = 10


def call(url):
    """Calls the next service; the answer carries how long the call took, or why it failed."""
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            answer = json.loads(response.read())
        ok = True
    except Exception as error:  # the page shows why the call failed
        answer = {"error": f"{type(error).__name__}: {error}"}
        ok = False
    return answer, round((time.monotonic() - started) * 1000), ok


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        backend_url = os.environ.get("BACKEND_URL")
        backend, elapsed_ms, ok = call(backend_url)
        body = {
            "service": "api-gateway",
            "app": "frontend",
            "data_center": os.environ.get("GLOBAL_DEPLOYMENT_DATA_CENTER", "?"),
            "pod": socket.gethostname(),
            "backend_url": backend_url,
            "elapsed_ms": elapsed_ms,
            "next": backend,
        }
        # Only set when the global config connects api-gateway to the reviews app.
        reviews_url = os.environ.get("REVIEWS_URL")
        if reviews_url:
            reviews, reviews_ms, reviews_ok = call(reviews_url)
            body["also"] = [{**reviews, "called_url": reviews_url, "elapsed_ms": reviews_ms}]
            ok = ok and reviews_ok
        self.send_response(200 if ok else 502)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


HTTPServer(("", PORT), Handler).serve_forever()

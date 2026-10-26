"""api-gateway: the only service of the frontend app that may call the backend app.

BACKEND_URL is set by the global deployment: the backend runs in another data center, and the
address is the Linkerd mirror of its inference service in this data center.
"""
import json
import os
import socket
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 3000
TIMEOUT_SECONDS = 10


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        backend_url = os.environ.get("BACKEND_URL")
        started = time.monotonic()
        try:
            with urllib.request.urlopen(backend_url, timeout=TIMEOUT_SECONDS) as response:
                backend = json.loads(response.read())
            status = 200
        except Exception as error:  # the page shows why the call failed
            backend = {"error": f"{type(error).__name__}: {error}"}
            status = 502
        body = json.dumps({
            "service": "api-gateway",
            "app": "frontend",
            "data_center": os.environ.get("GLOBAL_DEPLOYMENT_DATA_CENTER", "?"),
            "pod": socket.gethostname(),
            "backend_url": backend_url,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "next": backend,
        })
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())


HTTPServer(("", PORT), Handler).serve_forever()

"""web: the public storefront page. Asks api-gateway, in the same landscape, to recognize a product."""
import html
import json
import os
import socket
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 3000
TIMEOUT_SECONDS = 15

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Storefront</title>
<style>
  body {{ font-family: -apple-system, Helvetica, sans-serif; background: #f6f5fb; color: #1b1a2e; margin: 0; }}
  header {{ background: #1b1a2e; color: #fff; padding: 18px 40px; font-size: 22px; font-weight: 700; }}
  header span {{ color: #a99cff; font-weight: 400; font-size: 16px; margin-left: 12px; }}
  main {{ padding: 32px 40px; max-width: 900px; }}
  button {{ font-size: 18px; padding: 12px 22px; border: 0; border-radius: 10px; background: #7c5cff; color: #fff; cursor: pointer; }}
  ol {{ padding: 0; list-style: none; }}
  li {{ background: #fff; border-radius: 12px; padding: 14px 18px; margin: 10px 0; border-left: 6px solid #3ccf8e; }}
  li.error {{ border-left-color: #e5484d; }}
  .dc {{ font-weight: 700; }}
  .muted {{ color: #6b6a80; font-size: 14px; }}
</style></head>
<body><header>Storefront <span>web runs in data center {dc}</span></header>
<main>
  <form action="/ask"><button>Recognize product</button></form>
  {result}
</main></body></html>"""


def api_gateway_url():
    return f"http://ws-server-{os.environ['WORKSPACE_ID']}-api-gateway:{PORT}/"


def hop_item(hop):
    if "error" in hop:
        return f'<li class="error">{html.escape(hop["error"])}</li>'
    extra = ""
    if "prediction" in hop:
        extra = f' recognized <b>{html.escape(hop["prediction"])}</b>'
    if "rating" in hop:
        extra = f' rated it <b>{html.escape(hop["rating"])}</b>'
    if "data" in hop:
        extra += f' <span class="muted">{html.escape(hop["data"])}</span>'
    if "backend_url" in hop:
        extra = (f' <span class="muted">called {html.escape(str(hop["backend_url"]))}'
                 f' in {hop["elapsed_ms"]} ms</span>')
    if "called_url" in hop:
        extra += (f' <span class="muted">called by api-gateway via {html.escape(hop["called_url"])}'
                  f' in {hop["elapsed_ms"]} ms</span>')
    return (f'<li><b>{html.escape(hop["app"])}/{html.escape(hop["service"])}</b> in '
            f'<span class="dc">data center {html.escape(hop["data_center"])}</span>{extra}'
            f'<br><span class="muted">{html.escape(hop["pod"])}</span></li>')


def hop_items(hop):
    """The call chain in order, then the services api-gateway called besides the backend."""
    also = []
    while hop:
        yield hop_item(hop)
        if "error" in hop:
            break
        also += hop.get("also", [])
        hop = hop.get("next")
    for extra in also:
        yield hop_item(extra)


def ask():
    try:
        with urllib.request.urlopen(api_gateway_url(), timeout=TIMEOUT_SECONDS) as response:
            chain = json.loads(response.read())
    except urllib.error.HTTPError as error:
        chain = json.loads(error.read())
    except Exception as error:  # shown on the page
        chain = {"error": f"api-gateway did not answer: {error}"}
    first = {
        "service": "web", "app": "frontend", "pod": socket.gethostname(),
        "data_center": os.environ.get("GLOBAL_DEPLOYMENT_DATA_CENTER", "?"), "next": chain,
    }
    return "<ol>" + "".join(hop_items(first)) + "</ol>"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = ask() if self.path.startswith("/ask") else ""
        page = PAGE.format(dc=html.escape(os.environ.get("GLOBAL_DEPLOYMENT_DATA_CENTER", "?")), result=result)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode())


HTTPServer(("", PORT), Handler).serve_forever()

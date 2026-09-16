"""Authenticated loopback-only HTML transport. No command execution endpoints."""
from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .html_ui import HtmlController, html_document
from .questions import AnswerError


class ChoiceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, controller: HtmlController, port: int = 0):
        self.controller = controller
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), ChoiceHandler)

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"

    @property
    def url(self):
        # Fragment is never sent in an HTTP request or Referer header.
        return f"{self.origin}/#token={self.token}"


class ChoiceHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not persist device context, choices or bearer credentials in logs.

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status, payload, *, html=False):
        body = payload.encode() if html else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, *, public=False):
        origin = self.server.origin
        if self.headers.get("Host") != origin.removeprefix("http://"):
            return False
        if self.headers.get("Origin") not in (None, origin):
            return False
        return public or secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.server.token)

    def do_GET(self):
        if not self.authorized(public=self.path == "/"):
            return self.reply(403, {"error": "页面连接凭据无效，请使用 Agent 提供的本地链接重新打开。"})
        if self.path == "/":
            return self.reply(200, html_document(), html=True)
        if self.path == "/state":
            return self.reply(200, self.server.controller.snapshot())
        self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if not self.authorized():
            return self.reply(403, {"error": "Unauthorized"})
        if self.path != "/answer":
            return self.reply(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(400, {"error": "Invalid request body"})
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Answer must be an object")
            self.reply(200, self.server.controller.submit(payload))
        except AnswerError as error:
            self.reply(409, {"error": str(error)})
        except (ValueError, UnicodeError):
            self.reply(400, {"error": "Invalid JSON request"})


def serve(store, *, port=0, open_browser=False):
    server = ChoiceServer(HtmlController(store), port)
    print(json.dumps({"url": server.url, "revision": server.controller.snapshot()["revision"],
                      "instruction": "Keep this process running; use wait-ui to receive clicks."}), flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

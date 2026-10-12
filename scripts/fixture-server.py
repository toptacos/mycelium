import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/status":
            body = json.dumps(
                {"ok": True, "region": "us-east-1", "uptime_s": 9042}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/":
            html = b"<html><body><h1>Fixture Home</h1><p>This is the local fixture page served for the research sample.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9799
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"fixture server on http://127.0.0.1:{port} (/status, /)", flush=True)
    server.serve_forever()

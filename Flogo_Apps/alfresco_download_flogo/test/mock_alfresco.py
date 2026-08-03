#!/usr/bin/env python3
"""
Mock Alfresco download server for testing alfresco_download_flogo end-to-end.

  Listens on 127.0.0.1:9090
  Requires Basic Auth  SVC.ofcs.qa / changeit
  GET  .../SpacesStore/<uuid>            -> 200 + file bytes + Content-Disposition
  GET  .../SpacesStore/<uuid with 'notfound'> -> 404
  wrong/missing credentials             -> 401

Run:  python mock_alfresco.py
"""
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer

USER, PWD = "SVC.ofcs.qa", "changeit"
EXPECTED_AUTH = "Basic " + base64.b64encode(f"{USER}:{PWD}".encode()).decode()

# a tiny fake "PDF" (arbitrary binary bytes prove Base64 is lossless)
FILE_BYTES = b"%PDF-1.4 mock invoice content \x00\x01\x02\xff\xfe end-of-file"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("  [mock]", self.command, self.path, "->", fmt % args)

    def do_GET(self):
        if self.headers.get("Authorization", "") != EXPECTED_AUTH:
            self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"unauthorized")
            return
        if "notfound" in self.path:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"document not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", 'attachment; filename="invoice.pdf"')
        self.send_header("Content-Length", str(len(FILE_BYTES)))
        self.end_headers()
        self.wfile.write(FILE_BYTES)


if __name__ == "__main__":
    print("Mock Alfresco listening on http://127.0.0.1:9090")
    print("Expected file Base64:", base64.b64encode(FILE_BYTES).decode())
    HTTPServer(("127.0.0.1", 9090), Handler).serve_forever()

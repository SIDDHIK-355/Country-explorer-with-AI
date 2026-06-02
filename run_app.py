"""
Travel Guide — combined server.
Serves the Prefab search page, background photos, and triggers the agent.

Run:
    python run_app.py
"""
import base64
import json
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from prefab_app import build_html

HERE = Path(__file__).parent
PHOTO_DIR = HERE / "Photo"
PORT = 5175


def _load_photos() -> list[str]:
    """Load all photos from the Photo/ folder as base64 data URIs."""
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    photos = []
    for p in sorted(PHOTO_DIR.iterdir()):
        if p.suffix.lower() in extensions:
            mime = "image/jpeg" if p.suffix.lower() in {".jpg", ".jpeg"} else f"image/{p.suffix[1:].lower()}"
            b64 = base64.b64encode(p.read_bytes()).decode()
            photos.append(f"data:{mime};base64,{b64}")
    return photos


print("Loading photos...", end=" ", flush=True)
photos = _load_photos()
print(f"{len(photos)} found.")

print("Building search page...", end=" ", flush=True)
HTML = build_html(photos)
print("done.")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", ""):
            data = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/run":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            country = body.get("country", "").strip()

            if country:
                subprocess.Popen(
                    ["python", str(HERE / "agent.py"), country],
                    cwd=str(HERE),
                )
                resp = json.dumps({"message": f"🗺️  Opening travel guide for {country}..."})
            else:
                resp = json.dumps({"message": "Please enter a country name."})

            data = resp.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress access logs


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"\n🌍  Travel Guide is running at {url}")
    print("   Press Ctrl+C to stop.\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()

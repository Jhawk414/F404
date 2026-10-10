"""Embedded local HTTP server for the F404 cycle deck interactive GUI.

Serves the standalone browser application and provides a lightweight REST API
for deck discovery, deck data export, and operating point interpolation.
"""
from __future__ import annotations

import cgi
import http.server
import json
import logging
import mimetypes
import os
from pathlib import Path
import socket
import socketserver
import sys
import threading
from typing import Any, Dict, List, Optional
import urllib.parse
import webbrowser

from F404_pycycle.deck_interpolator import DeckInterpolator

logger = logging.getLogger(__name__)


def get_static_dir() -> Path:
    """Return the path to the bundled GUI static web assets."""
    # Look next to this file: src/F404_pycycle/gui/static/
    pkg_static = Path(__file__).parent / "gui" / "static"
    if pkg_static.exists():
        return pkg_static
    # Fallback to current directory or repo root
    cwd_static = Path.cwd() / "gui" / "static"
    if cwd_static.exists():
        return cwd_static
    raise FileNotFoundError(f"GUI static directory not found at {pkg_static}")


def discover_decks(search_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Scan search paths for cycle deck CSV files."""
    candidates: List[Path] = []
    if search_path is not None:
        p = Path(search_path)
        if p.is_file() and p.suffix.lower() == ".csv":
            candidates.append(p)
        elif p.is_dir():
            candidates.extend(sorted(p.glob("*.csv")))

    # Standard discovery locations
    standard_dirs = [Path("deck"), Path("decks"), Path(".")]
    for d in standard_dirs:
        if d.exists() and d.is_dir():
            candidates.extend(sorted(d.glob("cycle_deck_*.csv")))
            if not candidates:
                candidates.extend(sorted(d.glob("*.csv")))

    seen = set()
    unique_decks = []
    for f in candidates:
        abs_p = f.resolve()
        if abs_p not in seen and f.is_file():
            seen.add(abs_p)
            # Peek at header to verify it's a cycle deck
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    header = fp.readline()
                if "alt" in header and "dTs" in header:
                    unique_decks.append({
                        "name": f.name,
                        "path": str(f),
                        "rel_path": str(f),
                        "size_bytes": f.stat().st_size,
                    })
            except Exception:
                continue

    return unique_decks


class DeckGuiHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler serving GUI assets and cycle deck APIs."""

    interpolator: Optional[DeckInterpolator] = None
    active_deck_path: Optional[str] = None
    static_dir: Path = Path(".")

    def log_message(self, format: str, *args: Any) -> None:
        # Quiet standard HTTP access logs in terminal unless debug
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._serve_file(self.static_dir / "index.html", "text/html")
        elif path == "/api/decks":
            self._api_list_decks()
        elif path == "/api/deck-data":
            self._api_deck_data(query)
        elif path == "/api/interpolate":
            self._api_interpolate(query)
        else:
            # Static file fallback
            rel_path = path.lstrip("/")
            file_path = (self.static_dir / rel_path).resolve()
            # Security check: ensure within static_dir
            if str(file_path).startswith(str(self.static_dir.resolve())) and file_path.is_file():
                mime, _ = mimetypes.guess_type(str(file_path))
                self._serve_file(file_path, mime or "application/octet-stream")
            else:
                self.send_error(404, f"File not found: {path}")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/select-deck":
            self._api_select_deck()
        else:
            self.send_error(404, "Unknown endpoint")

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def _api_list_decks(self) -> None:
        decks = discover_decks()
        self._send_json({
            "decks": decks,
            "active_deck": self.active_deck_path,
        })

    def _api_deck_data(self, query: Dict[str, List[str]]) -> None:
        req_path = query.get("path", [None])[0]
        if req_path and req_path != self.active_deck_path:
            try:
                self.interpolator = DeckInterpolator(req_path)
                self.active_deck_path = req_path
            except Exception as e:
                self._send_json({"error": f"Failed to load deck {req_path}: {e}"}, status=400)
                return

        if self.interpolator is None:
            self._send_json({"error": "No deck loaded"}, status=404)
            return

        deck_payload = self.interpolator.export_deck_data()
        deck_payload["deck_file"] = self.active_deck_path
        self._send_json(deck_payload)

    def _api_interpolate(self, query: Dict[str, List[str]]) -> None:
        if self.interpolator is None:
            self._send_json({"error": "No deck loaded"}, status=404)
            return

        try:
            mode = query.get("mode", [self.interpolator.get_modes()[0]])[0]
            alt = float(query.get("alt", [0.0])[0])
            dts = float(query.get("dTs", [0.0])[0])
            thr = float(query.get("throttle", [3800.0 if mode == "wet" else 3100.0])[0])
            mn = float(query.get("MN", [0.001])[0]) if "MN" in query else None

            result = self.interpolator.interpolate(mode=mode, alt=alt, dTs=dts, throttle=thr, mn=mn)
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": str(e)}, status=400)

    def _api_select_deck(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        try:
            data = json.loads(body)
            deck_path = data.get("path")
            if not deck_path or not Path(deck_path).exists():
                self._send_json({"error": f"Deck file does not exist: {deck_path}"}, status=404)
                return
            self.interpolator = DeckInterpolator(deck_path)
            self.active_deck_path = deck_path
            self._send_json({"status": "ok", "active_deck": deck_path})
        except Exception as e:
            self._send_json({"error": str(e)}, status=400)


def find_free_port(preferred_port: int = 8080, host: str = "127.0.0.1") -> int:
    """Find a free TCP port starting at preferred_port."""
    for port in range(preferred_port, preferred_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    # Let OS assign ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def start_server(
    deck_path: Optional[Union[str, Path]] = None,
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = True,
    block: bool = True,
) -> Tuple[http.server.HTTPServer, int, str]:
    """Start the F404 cycle deck GUI server."""
    static_dir = get_static_dir()
    DeckGuiHandler.static_dir = static_dir

    # Resolve initial deck
    if deck_path is None:
        discovered = discover_decks()
        if discovered:
            deck_path = discovered[0]["path"]
        else:
            raise FileNotFoundError("No cycle deck CSV files discovered. Run 'f404 sweep' first or specify --deck.")

    deck_path_resolved = Path(deck_path).resolve()
    DeckGuiHandler.interpolator = DeckInterpolator(deck_path_resolved)
    DeckGuiHandler.active_deck_path = str(deck_path_resolved)

    actual_port = find_free_port(port, host=host)
    server = http.server.ThreadingHTTPServer((host, actual_port), DeckGuiHandler)
    url = f"http://{host}:{actual_port}"

    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()

    if block:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()

    return server, actual_port, url

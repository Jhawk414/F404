"""Tests for the embedded GUI web server and REST API."""
import io
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from F404_pycycle.deck_interpolator import DeckInterpolator
from F404_pycycle.gui_server import (
    DeckGuiHandler,
    discover_decks,
    find_free_port,
    get_static_dir,
)


def test_get_static_dir_exists():
    static_dir = get_static_dir()
    assert static_dir.exists()
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "style.css").exists()


def test_discover_decks_finds_wet_deck():
    decks = discover_decks()
    assert len(decks) >= 1
    names = [d["name"] for d in decks]
    assert "cycle_deck_wet.csv" in names


def test_find_free_port():
    port = find_free_port(8080)
    assert 1024 <= port <= 65535


class DummyHandler(DeckGuiHandler):
    """In-memory subclass to test HTTP handler without network sockets."""

    def __init__(self, path: str):
        self.path = path
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.headers = {}
        self._headers_buffer = []
        self.responses = []
        self.close_connection = True

    def send_response(self, code, message=None):
        self.responses.append(code)

    def send_header(self, keyword, value):
        self._headers_buffer.append((keyword, value))

    def end_headers(self):
        pass

    def send_error(self, code, message=None, explain=None):
        self.responses.append(code)


def test_handler_serves_index_html():
    static_dir = get_static_dir()
    DeckGuiHandler.static_dir = static_dir

    handler = DummyHandler("/")
    handler.do_GET()

    assert handler.responses == [200]
    output = handler.wfile.getvalue().decode("utf-8")
    assert "GE F404 Turbofan Cycle Deck Explorer" in output


def test_handler_serves_app_js():
    static_dir = get_static_dir()
    DeckGuiHandler.static_dir = static_dir

    handler = DummyHandler("/app.js")
    handler.do_GET()

    assert handler.responses == [200]
    output = handler.wfile.getvalue().decode("utf-8")
    assert "ClientDeckInterpolator" in output


def test_handler_api_decks():
    static_dir = get_static_dir()
    DeckGuiHandler.static_dir = static_dir

    handler = DummyHandler("/api/decks")
    handler.do_GET()

    assert handler.responses == [200]
    data = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "decks" in data
    assert any(d["name"] == "cycle_deck_wet.csv" for d in data["decks"])


def test_handler_api_deck_data_and_interpolate():
    deck_path = Path("deck/cycle_deck_wet.csv")
    if not deck_path.exists():
        pytest.skip("deck/cycle_deck_wet.csv not found")

    DeckGuiHandler.static_dir = get_static_dir()
    DeckGuiHandler.interpolator = DeckInterpolator(deck_path)
    DeckGuiHandler.active_deck_path = str(deck_path.resolve())

    # Test /api/deck-data
    h_data = DummyHandler("/api/deck-data")
    h_data.do_GET()
    assert h_data.responses == [200]
    data = json.loads(h_data.wfile.getvalue().decode("utf-8"))
    assert "deck_data" in data
    assert "wet" in data["deck_data"]

    # Test /api/interpolate
    h_interp = DummyHandler("/api/interpolate?alt=0&dTs=0&throttle=3800&mode=wet")
    h_interp.do_GET()
    assert h_interp.responses == [200]
    interp_res = json.loads(h_interp.wfile.getvalue().decode("utf-8"))
    assert "outputs" in interp_res
    assert interp_res["outputs"]["Fn"] > 15000.0

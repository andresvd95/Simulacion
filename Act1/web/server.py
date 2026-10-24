"""Servidor web local para visualizar Yahtzee y las simulaciones Montecarlo."""

from __future__ import annotations

import json
import random
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = ACTIVITY_DIR.parent
sys.path.insert(0, str(ACTIVITY_DIR))

from yahtzee import game, simulate  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    """Sirve los archivos estáticos y expone dos endpoints JSON."""

    def _send_json(self, payload: dict, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            target = ACTIVITY_DIR / "web" / "index.html"
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404, "Ruta no encontrada")
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._read_json()
            if self.path == "/api/game":
                policy1 = body.get("player1", "mc")
                policy2 = body.get("player2", "greedy")
                samples = max(1, min(int(body.get("samples", 24)), 200))
                seed = body.get("seed")
                result = game(policy1, policy2, random.Random(seed), samples)
                self._send_json(result)
                return
            if self.path == "/api/simulate":
                games = max(1, min(int(body.get("games", 100)), 5000))
                samples = max(1, min(int(body.get("samples", 24)), 200))
                seed = int(body.get("seed", 2026))
                self._send_json(simulate(games, samples, seed))
                return
            self.send_error(404, "Endpoint no encontrado")
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": f"Parámetros inválidos: {error}"}, 400)
        except Exception as error:  # pragma: no cover - mensaje útil para el navegador
            self._send_json({"error": str(error)}, 500)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {format % args}")


def main() -> None:
    host, port = "127.0.0.1", 8000
    print(f"Yahtzee web disponible en http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()

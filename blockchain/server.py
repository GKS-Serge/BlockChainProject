"""Local HTTP API and dashboard for the finance blockchain."""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from . import Blockchain

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_ROOT = PROJECT_ROOT / "assets"
CHAIN_FILE = PROJECT_ROOT / "data" / "blockchain.json"
MAX_REQUEST_BYTES = 16_384


def load_blockchain() -> Blockchain:
    if not CHAIN_FILE.exists():
        return Blockchain()
    try:
        serialized = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
        chain = Blockchain.from_dict(serialized)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Impossible de charger la chaîne locale : {error}") from error
    problems = chain.validate()
    if problems:
        raise RuntimeError("La chaîne locale est invalide : " + " ".join(problems))
    return chain


def save_blockchain(chain: Blockchain) -> None:
    CHAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=CHAIN_FILE.parent,
            prefix="blockchain-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(chain.to_dict(), temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, CHAIN_FILE)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


class BlockchainHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], chain: Blockchain) -> None:
        super().__init__(address, BlockchainRequestHandler)
        self.chain = chain
        self.chain_lock = threading.RLock()


class BlockchainRequestHandler(BaseHTTPRequestHandler):
    server: BlockchainHTTPServer

    def log_message(self, format_string: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format_string % args}")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static_file(self, file_path: Path) -> None:
        try:
            body = file_path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        content_type = "text/javascript" if file_path.suffix == ".js" else None
        if content_type is None:
            import mimetypes

            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == "/api/state":
            with self.server.chain_lock:
                chain = self.server.chain
                self._send_json(
                    200,
                    {
                        **chain.to_dict(),
                        "valid": chain.is_valid(),
                        "errors": chain.validate(),
                        "difficulty": chain.difficulty,
                        "total_work": chain.total_work(),
                    },
                )
            return

        if path in {"/", "/index.html"}:
            self._send_static_file(PROJECT_ROOT / "index.html")
            return
        if path == "/styles.css":
            self._send_static_file(PROJECT_ROOT / "styles.css")
            return
        if path == "/app.js":
            self._send_static_file(PROJECT_ROOT / "app.js")
            return
        if path.startswith("/assets/"):
            asset = (ASSETS_ROOT / path.removeprefix("/assets/")).resolve()
            if asset.is_relative_to(ASSETS_ROOT.resolve()) and asset.is_file():
                self._send_static_file(asset)
                return
        if path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/transactions":
            self._send_json(404, {"error": "Route inconnue."})
            return

        content_length = self.headers.get("Content-Length")
        try:
            size = int(content_length) if content_length is not None else -1
        except ValueError:
            size = -1
        if size < 0 or size > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Taille de requête invalide ou trop importante."})
            return

        try:
            payload = json.loads(self.rfile.read(size))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Le corps doit contenir un objet JSON valide."})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Le corps doit être un objet JSON."})
            return

        sender = payload.get("sender")
        receiver = payload.get("receiver")
        currency = payload.get("currency", "EUR")
        amount_value = payload.get("amount")
        if not isinstance(sender, str) or not sender.strip() or len(sender.strip()) > 200:
            self._send_json(400, {"error": "L’expéditeur est obligatoire (200 caractères maximum)."})
            return
        if not isinstance(receiver, str) or not receiver.strip() or len(receiver.strip()) > 200:
            self._send_json(400, {"error": "Le destinataire est obligatoire (200 caractères maximum)."})
            return
        if not isinstance(currency, str) or not currency.strip() or len(currency.strip()) > 12:
            self._send_json(400, {"error": "La devise est obligatoire (12 caractères maximum)."})
            return
        if isinstance(amount_value, bool):
            self._send_json(400, {"error": "Le montant doit être un nombre positif."})
            return
        try:
            amount = float(amount_value)
        except (TypeError, ValueError):
            self._send_json(400, {"error": "Le montant doit être un nombre positif."})
            return
        if not math.isfinite(amount) or amount <= 0:
            self._send_json(400, {"error": "Le montant doit être un nombre positif fini."})
            return

        with self.server.chain_lock:
            previous_length = len(self.server.chain.chain)
            try:
                block = self.server.chain.add_transaction(
                    sender.strip(),
                    receiver.strip(),
                    amount,
                    currency.strip().upper(),
                )
                save_blockchain(self.server.chain)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return
            except OSError as error:
                del self.server.chain.chain[previous_length:]
                self._send_json(500, {"error": f"Impossible d’enregistrer la transaction : {error}"})
                return
            self._send_json(201, {"block": block.to_dict()})


def main() -> None:
    port = int(os.environ.get("BLOCKCHAIN_PORT", "8080"))
    chain = load_blockchain()
    server = BlockchainHTTPServer(("127.0.0.1", port), chain)
    print(f"Blockchain locale : http://localhost:{port}/")
    print(f"Chaîne chargée : {len(chain)} bloc(s), valide={chain.is_valid()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

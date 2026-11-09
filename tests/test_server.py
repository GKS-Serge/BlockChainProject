"""Tests for the local dashboard API."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from blockchain import Blockchain
from blockchain import server as blockchain_server


@pytest.fixture
def api_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    chain_file = tmp_path / "blockchain.json"
    monkeypatch.setattr(blockchain_server, "CHAIN_FILE", chain_file)
    httpd: ThreadingHTTPServer = blockchain_server.BlockchainHTTPServer(
        ("127.0.0.1", 0), Blockchain()
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_dashboard_and_api_serve_live_chain(api_server: str) -> None:
    with urlopen(f"{api_server}/") as response:
        assert response.status == 200
        assert b"Observatoire de la cha" in response.read()

    with urlopen(f"{api_server}/api/state") as response:
        state = json.load(response)

    assert state["valid"] is True
    assert len(state["chain"]) == 1
    assert state["chain"][0]["data"]["type"] == "genesis"


def test_transaction_updates_and_persists_chain(api_server: str) -> None:
    request = Request(
        f"{api_server}/api/transactions",
        data=json.dumps(
            {"sender": "Alice", "receiver": "Bob", "amount": 12.5, "currency": "EUR"}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request) as response:
        result = json.load(response)
        assert response.status == 201

    with urlopen(f"{api_server}/api/state") as response:
        state = json.load(response)

    assert state["valid"] is True
    assert len(state["chain"]) == 2
    assert state["chain"][1]["previous_hash"] == state["chain"][0]["hash"]
    assert result["block"]["data"]["sender"] == "Alice"
    assert blockchain_server.load_blockchain().is_valid()


def test_invalid_transaction_is_rejected_without_changing_chain(api_server: str) -> None:
    request = Request(
        f"{api_server}/api/transactions",
        data=json.dumps(
            {"sender": "Alice", "receiver": "Bob", "amount": -1, "currency": "EUR"}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(HTTPError) as error:
        urlopen(request)

    assert error.value.code == 400
    with urlopen(f"{api_server}/api/state") as response:
        state = json.load(response)
    assert len(state["chain"]) == 1

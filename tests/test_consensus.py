"""Tests de validation et de synchronisation des nœuds (M4)."""

from __future__ import annotations

import json
from io import BytesIO

import pytest
from blockchain import Block, Blockchain
from blockchain.consensus import (
    accept_block,
    chain_from_payload,
    is_better_chain,
    synchronize,
    synchronize_from_peers,
    validate_incoming_block,
)


def _make_block_miss_difficulty(block: Block, difficulty: int) -> None:
    """Ajuste le nonce pour obtenir un bloc qui échoue à la difficulté locale."""
    while block.meets_difficulty(difficulty):
        block.nonce += 1
        block.hash = block.compute_hash()


def test_reconnected_node_fetches_the_most_advanced_valid_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un nœud hors ligne récupère la chaîne du pair via /api/state."""
    up_to_date_node = Blockchain()
    reconnecting_node = Blockchain()
    up_to_date_node.add_transaction("alice", "bob", 10.0)
    up_to_date_node.add_transaction("alice", "bob", 20.0)
    demandes: list[str] = []

    def fake_urlopen(url: str, timeout: float) -> BytesIO:
        demandes.append(url)
        return BytesIO(json.dumps(up_to_date_node.to_dict()).encode("utf-8"))

    monkeypatch.setattr("blockchain.consensus.urlopen", fake_urlopen)
    assert synchronize_from_peers(
        reconnecting_node, ["http://pair.test"], timeout=2.0
    ) is True

    assert demandes == ["http://pair.test/api/state"]
    assert len(reconnecting_node.chain) == len(up_to_date_node.chain)
    assert reconnecting_node.chain[-1].hash == up_to_date_node.chain[-1].hash
    assert reconnecting_node.is_valid()


def test_invalid_longer_chain_is_rejected() -> None:
    """Une chaîne falsifiée est ignorée même si elle est plus longue."""
    local = Blockchain()
    peer = Blockchain()
    peer.add_transaction("alice", "bob", 10.0)
    peer.add_transaction("alice", "bob", 20.0)
    peer.chain[1].data["amount"] = 999.0

    assert synchronize(local, [peer]) is False
    assert len(local.chain) == 1


def test_synchronization_keeps_the_candidate_with_most_local_work() -> None:
    """La difficulté du pair n'altère ni la validation ni le choix du meilleur pair."""
    local = Blockchain(difficulty=1)
    shorter = Blockchain(difficulty=1)
    advanced = Blockchain(difficulty=1)
    shorter.add_transaction("alice", "bob", 10.0)
    advanced.add_transaction("alice", "bob", 10.0)
    advanced.add_transaction("bob", "chloe", 5.0)
    advanced.difficulty = 0

    assert synchronize(local, [advanced, shorter]) is True
    assert len(local.chain) == len(advanced.chain)
    assert local.chain[-1].hash == advanced.chain[-1].hash
    assert local.difficulty == 1


def test_chain_with_different_genesis_is_rejected() -> None:
    """Une chaîne issue d'un autre bloc genesis ne rejoint pas le réseau."""
    local = Blockchain()
    foreign = Blockchain()
    foreign.chain[0].data["message"] = "Autre réseau"
    foreign.chain[0].hash = foreign.chain[0].compute_hash()
    foreign.add_transaction("alice", "bob", 10.0)

    assert foreign.is_valid()
    assert is_better_chain(local, foreign) is False
    assert synchronize(local, [foreign]) is False


def test_peer_difficulty_never_overrides_local_difficulty() -> None:
    """Le pair annonce une difficulté nulle, mais le nœud impose la sienne."""
    local = Blockchain(difficulty=1)
    peer = Blockchain(difficulty=0)
    block = peer.add_transaction("alice", "bob", 10.0)
    _make_block_miss_difficulty(block, local.difficulty)

    assert peer.is_valid()
    candidate = chain_from_payload(
        {**peer.to_dict(), "difficulty": 0},
        difficulty=local.difficulty,
    )
    assert candidate.difficulty == local.difficulty
    assert is_better_chain(local, candidate) is False


def test_incoming_block_checks_index_hash_link_and_local_difficulty() -> None:
    """Un bloc entrant doit respecter les champs attendus et la difficulté locale."""
    local = Blockchain(difficulty=1)
    peer = Blockchain(difficulty=0)
    block = peer.add_transaction("alice", "bob", 5.0)
    _make_block_miss_difficulty(block, local.difficulty)
    block.index += 1
    block.previous_hash = "f" * 64

    problems = validate_incoming_block(local, block)
    assert any("Index" in problem for problem in problems)
    assert any("pointe pas" in problem for problem in problems)
    assert any("hash" in problem for problem in problems)
    assert any("difficulté" in problem for problem in problems)
    assert accept_block(local, block) is False
    assert len(local.chain) == 1


def test_malformed_block_timestamp_is_rejected() -> None:
    """Un horodatage trop grand est rejeté sans interrompre la validation."""
    local = Blockchain()
    peer = Blockchain()
    block = peer.add_transaction("alice", "bob", 5.0)
    block.timestamp = 10**400
    block.hash = block.compute_hash()
    peer.chain[1] = block

    assert is_better_chain(local, peer) is False


def test_accept_block_does_not_keep_a_mutable_reference_to_the_peer() -> None:
    """La copie locale reste valide si le pair modifie son objet après l'envoi."""
    local = Blockchain()
    peer = Blockchain()
    block = peer.add_transaction("alice", "bob", 5.0)

    assert accept_block(local, block) is True
    block.data["amount"] = 999.0
    assert local.is_valid()

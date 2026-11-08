"""Tests du hachage canonique et du minage.

Ces modules appartiennent à **M2 (hash, minage & intégrité)**. Ils sont
testés ici parce que M1 en dépend : la chaîne refuse d'ajouter un bloc dont
l'empreinte ne respecte pas la difficulté.
"""

from __future__ import annotations

import pytest

from blockchain import Block, Blockchain, canonical_payload, check_difficulty, hash_block
from blockchain.hashing import hash_payload, serialize_payload
from blockchain.mining import mine_block, work_of


# ----------------------------------------------------------------------
# Contenu canonique
# ----------------------------------------------------------------------
def test_canonical_payload_covers_the_five_fields() -> None:
    """Le contenu canonique est exactement index/timestamp/data/previous_hash/nonce."""
    block = Block(
        index=2,
        timestamp=1_700_000_000.0,
        data={"amount": 10.0},
        previous_hash="a" * 64,
        nonce=7,
    )

    payload = canonical_payload(block)

    assert payload == {
        "index": 2,
        "timestamp": 1_700_000_000.0,
        "data": {"amount": 10.0},
        "previous_hash": "a" * 64,
        "nonce": 7,
    }
    assert "hash" not in payload, "une empreinte ne se signe pas elle-même"


def test_serialization_is_canonical() -> None:
    """La sérialisation est compacte et triée par clé."""
    payload = {"b": 1, "a": 2}
    assert serialize_payload(payload) == '{"a":2,"b":1}'


def test_hash_is_stable_and_hexadecimal() -> None:
    """L'empreinte est un SHA-256 hexadécimal de 64 caractères."""
    block = Block(
        index=0,
        timestamp=1_700_000_000.0,
        data={},
        previous_hash="0" * 64,
    )

    digest = hash_block(block)

    assert len(digest) == 64
    assert all(char in "0123456789abcdef" for char in digest)
    assert digest == hash_payload(canonical_payload(block))


def test_hash_ignores_dict_key_order() -> None:
    """L'ordre des clés du payload ne change pas l'empreinte."""
    common = {"index": 1, "timestamp": 1_700_000_000.0, "previous_hash": "0" * 64}

    block_a = Block(data={"sender": "a", "receiver": "b", "amount": 1.0}, **common)
    block_b = Block(data={"amount": 1.0, "receiver": "b", "sender": "a"}, **common)

    assert hash_block(block_a) == hash_block(block_b)


# ----------------------------------------------------------------------
# Difficulté
# ----------------------------------------------------------------------
def test_check_difficulty() -> None:
    """La difficulté compte les zéros hexadécimaux en tête d'empreinte."""
    assert check_difficulty("00abc", 2) is True
    assert check_difficulty("0abc", 2) is False
    assert check_difficulty("abc", 0) is True
    assert check_difficulty("abc", -1) is True


# ----------------------------------------------------------------------
# Minage
# ----------------------------------------------------------------------
def test_mine_block_finds_a_valid_nonce() -> None:
    """Le minage trouve un nonce tel que l'empreinte respecte la difficulté."""
    block = Block(
        index=1,
        timestamp=1_700_000_000.0,
        data={"type": "transaction", "amount": 250.0},
        previous_hash="0" * 64,
    )

    mined = mine_block(block, difficulty=3)

    assert mined.nonce >= 0
    assert mined.hash.startswith("000")
    assert mined.hash == hash_block(mined)
    assert mined.is_hash_valid()


def test_mine_block_with_zero_difficulty() -> None:
    """Sans difficulté, le minage ne cherche rien et le nonce vaut 0."""
    block = Block(
        index=1,
        timestamp=1_700_000_000.0,
        data={},
        previous_hash="0" * 64,
    )

    mined = mine_block(block, difficulty=0)

    assert mined.nonce == 0
    assert mined.is_hash_valid()


def test_mined_block_is_accepted_by_the_chain() -> None:
    """Un bloc miné est accepté par la chaîne de M1."""
    blockchain = Blockchain(difficulty=2)

    block = Block(
        index=1,
        timestamp=1_700_000_000.0,
        data={"type": "transaction", "amount": 250.0},
        previous_hash=blockchain.last_block.hash,
    )
    mined = mine_block(block, difficulty=2)

    blockchain.chain.append(mined)

    assert blockchain.is_valid()
    assert blockchain.total_work() > 1


def test_mine_block_rejects_negative_difficulty() -> None:
    """Une difficulté négative est refusée."""
    block = Block(index=1, timestamp=1_700_000_000.0, data={}, previous_hash="0" * 64)

    with pytest.raises(ValueError):
        mine_block(block, difficulty=-1)


# ----------------------------------------------------------------------
# Travail cumulé (règle de sélection de M4)
# ----------------------------------------------------------------------
def test_work_of_grows_with_difficulty() -> None:
    """Un bloc conforme à une difficulté plus grande contribue plus de travail."""
    block = Block(index=1, timestamp=1_700_000_000.0, data={}, previous_hash="0" * 64)

    assert work_of(block, 0) == 1
    assert work_of(block, 1) == 16
    assert work_of(block, 2) == 256
    assert work_of(block, 2) > work_of(block, 1)


def test_total_work_reflects_chain_length() -> None:
    """Le travail cumulé augmente avec la longueur de la chaîne."""
    blockchain = Blockchain()
    first = blockchain.total_work()

    blockchain.add_transaction(sender="alice", receiver="bob", amount=10.0)

    assert blockchain.total_work() > first

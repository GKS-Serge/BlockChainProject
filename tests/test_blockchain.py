"""Tests du bloc et de la chaîne de la blockchain financière.

Cible du livrable : une chaîne créée avec un bloc genesis, puis un bloc
ajouté, avec vérification de la cohérence de la chaîne.
"""

from __future__ import annotations

import pytest

from blockchain import Block, Blockchain
from blockchain.blockchain import GENESIS_PREVIOUS_HASH


# ----------------------------------------------------------------------
# Bloc genesis
# ----------------------------------------------------------------------
def test_genesis_block_is_created() -> None:
    """Une nouvelle chaîne démarre avec un unique bloc genesis."""
    blockchain = Blockchain()

    assert len(blockchain.chain) == 1

    genesis = blockchain.chain[0]
    assert genesis.index == 0
    assert genesis.previous_hash == GENESIS_PREVIOUS_HASH
    assert genesis.previous_hash == "0" * 64
    assert genesis.hash != ""
    assert genesis.is_hash_valid()


def test_genesis_block_is_deterministic() -> None:
    """Deux chaînes créées indépendamment partagent le même bloc genesis."""
    assert Blockchain.create_genesis_block().hash == Blockchain.create_genesis_block().hash


# ----------------------------------------------------------------------
# Ajout d'un bloc
# ----------------------------------------------------------------------
def test_add_block_to_the_chain() -> None:
    """Le livrable : une chaîne avec un genesis, puis un bloc ajouté."""
    blockchain = Blockchain()
    genesis = blockchain.chain[0]

    new_block = blockchain.add_block(
        {
            "type": "transaction",
            "sender": "alice",
            "receiver": "bob",
            "amount": 250.0,
            "currency": "EUR",
        }
    )

    # La chaîne contient désormais deux blocs.
    assert len(blockchain.chain) == 2

    # Le nouveau bloc est bien le dernier de la chaîne.
    assert blockchain.last_block is new_block
    assert blockchain.chain[-1] is new_block

    # Le nouveau bloc est indexé juste après le genesis.
    assert new_block.index == genesis.index + 1
    assert new_block.index == 1

    # Le nouveau bloc pointe vers l'empreinte du genesis.
    assert new_block.previous_hash == genesis.hash

    # La charge utile est conservée.
    assert new_block.data["sender"] == "alice"
    assert new_block.data["receiver"] == "bob"
    assert new_block.data["amount"] == 250.0

    # L'empreinte est calculée et cohérente.
    assert new_block.hash != genesis.hash
    assert new_block.is_hash_valid()


def test_add_transaction_creates_a_financial_block() -> None:
    """L'ajout d'une transaction produit un bloc contenant celle-ci."""
    blockchain = Blockchain()

    block = blockchain.add_transaction(
        sender="0xAlice",
        receiver="0xBob",
        amount=99.99,
    )

    assert block.data["type"] == "transaction"
    assert block.data["sender"] == "0xAlice"
    assert block.data["receiver"] == "0xBob"
    assert block.data["amount"] == 99.99
    assert block.data["currency"] == "EUR"
    assert blockchain.is_valid()


def test_add_block_rejects_invalid_data() -> None:
    """Des données non conformes sont refusées."""
    blockchain = Blockchain()

    with pytest.raises(ValueError):
        blockchain.add_block("pas un dictionnaire")

    with pytest.raises(ValueError):
        blockchain.add_transaction(sender="alice", receiver="bob", amount=-10)


# ----------------------------------------------------------------------
# Intégrité de la chaîne
# ----------------------------------------------------------------------
def test_chain_is_valid_after_adding_blocks() -> None:
    """La chaîne reste intègre après l'ajout de plusieurs blocs."""
    blockchain = Blockchain()

    for i in range(1, 4):
        blockchain.add_transaction(
            sender="0xTrader",
            receiver="0xExchange",
            amount=10.0 * i,
        )

    assert len(blockchain.chain) == 4
    assert blockchain.is_valid()

    for current, following in zip(blockchain.chain, blockchain.chain[1:]):
        assert following.previous_hash == current.hash
        assert following.index == current.index + 1


def test_tampering_with_a_block_invalidates_the_chain() -> None:
    """Modifier le contenu d'un bloc invalide la chaîne."""
    blockchain = Blockchain()
    blockchain.add_transaction(sender="alice", receiver="bob", amount=50.0)

    blockchain.chain[1].data["amount"] = 999_999.0

    assert not blockchain.is_valid()


def test_block_hash_changes_with_the_content() -> None:
    """Deux blocs de même index mais de contenus différents n'ont pas le même hash."""
    common = {"index": 1, "timestamp": 1_700_000_000.0, "previous_hash": "0" * 64}

    block_a = Block(data={"amount": 10.0}, **common)
    block_b = Block(data={"amount": 20.0}, **common)

    assert block_a.hash != block_b.hash
    assert block_a.is_hash_valid()
    assert block_b.is_hash_valid()


def test_block_roundtrip_serialization() -> None:
    """Un bloc sérialisé puis rechargé reste identique."""
    original = Block(
        index=3,
        timestamp=1_700_000_000.0,
        data={"type": "transaction", "amount": 42.0},
        previous_hash="a" * 64,
    )

    restored = Block.from_dict(original.to_dict())

    assert restored.hash == original.hash
    assert restored.data == original.data
    assert restored.index == original.index
    assert restored.previous_hash == original.previous_hash

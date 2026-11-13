"""Validation des blocs entrants et synchronisation (M4)."""

from __future__ import annotations

import copy
import json
import math
import re
from typing import Any, Mapping
from urllib.request import urlopen

from .block import Block
from .blockchain import Blockchain
from .mining import work_of

_HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _is_well_formed_block(block: object) -> bool:
    """Vérifie la structure de base avant de recalculer une empreinte."""
    if not isinstance(block, Block):
        return False
    if type(block.index) is not int or block.index < 0:
        return False
    if type(block.timestamp) not in (int, float):
        return False
    try:
        if not math.isfinite(block.timestamp):
            return False
    except OverflowError:
        return False
    return (
        isinstance(block.data, dict)
        and isinstance(block.previous_hash, str)
        and _HASH_PATTERN.fullmatch(block.previous_hash) is not None
        and isinstance(block.hash, str)
        and _HASH_PATTERN.fullmatch(block.hash) is not None
        and type(block.nonce) is int
        and block.nonce >= 0
    )


def validate_incoming_block(local: Blockchain, block: Block) -> list[str]:
    """Retourne les anomalies d'un bloc reçu (liste vide = bloc acceptable)."""
    problems: list[str] = []
    if not local.chain:
        return ["La chaîne locale est vide."]
    if not _is_well_formed_block(block):
        return ["La structure du bloc reçu est invalide."]

    last = local.last_block
    if block.index != last.index + 1:
        problems.append(f"Index {block.index} reçu, attendu {last.index + 1}.")
    if block.previous_hash != last.hash:
        problems.append("Le bloc ne pointe pas vers le dernier bloc local.")
    if not block.is_hash_valid():
        problems.append("Le hash ne correspond pas au contenu du bloc.")
    if not block.meets_difficulty(local.difficulty):
        problems.append(f"Le bloc ne respecte pas la difficulté {local.difficulty}.")
    return problems


def accept_block(local: Blockchain, block: Block) -> bool:
    """Ajoute une copie du bloc reçu s'il est valide."""
    if validate_incoming_block(local, block):
        return False
    local.chain.append(copy.deepcopy(block))
    return True


def chain_from_payload(payload: Mapping[str, Any], difficulty: int) -> Blockchain:
    """Reconstruit une chaîne en ignorant toute difficulté annoncée par le pair."""
    blocks = payload.get("chain")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("Le message du pair doit contenir une chaîne non vide.")

    candidate = Blockchain(difficulty=difficulty)
    try:
        candidate.chain = [Block.from_dict(block) for block in blocks]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Le message du pair contient un bloc mal formé.") from error
    return candidate


def _chain_is_valid(chain: list[Block], difficulty: int) -> bool:
    """Valide la chaîne en appliquant la difficulté de notre propre nœud."""
    if not chain or any(not _is_well_formed_block(block) for block in chain):
        return False

    expected_genesis = Blockchain.create_genesis_block()
    if chain[0].hash != expected_genesis.hash:
        return False

    checked_chain = Blockchain(difficulty=difficulty)
    checked_chain.chain = chain
    return checked_chain.is_valid()


def _total_work(chain: list[Block], difficulty: int) -> int:
    """Calcule le travail sans consulter les paramètres annoncés par un pair."""
    return sum(work_of(block, difficulty) for block in chain)


def is_better_chain(local: Blockchain, candidate: Blockchain) -> bool:
    """Vrai si la candidate est valide à difficulté locale et a plus de travail."""
    if not local.chain or not candidate.chain:
        return False
    if not _is_well_formed_block(local.chain[0]) or not _is_well_formed_block(
        candidate.chain[0]
    ):
        return False
    if local.chain[0].hash != Blockchain.create_genesis_block().hash:
        return False
    if candidate.chain[0].hash != local.chain[0].hash:
        return False
    if not _chain_is_valid(candidate.chain, local.difficulty):
        return False
    return _total_work(candidate.chain, local.difficulty) > _total_work(
        local.chain, local.difficulty
    )


def synchronize(local: Blockchain, candidates: list[Blockchain]) -> bool:
    """Remplace la chaîne locale par la meilleure candidate valide."""
    best_chain = local.chain
    for candidate in candidates:
        comparison = Blockchain(difficulty=local.difficulty)
        comparison.chain = best_chain
        if is_better_chain(comparison, candidate):
            best_chain = candidate.chain

    if best_chain is local.chain:
        return False
    local.chain = copy.deepcopy(best_chain)
    return True


def fetch_peer_chain(
    peer_url: str, difficulty: int, timeout: float = 5.0
) -> Blockchain | None:
    """Récupère la chaîne d'un pair via GET /api/state."""
    try:
        with urlopen(f"{peer_url.rstrip('/')}/api/state", timeout=timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, Mapping):
            return None
        return chain_from_payload(payload, difficulty)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None


def synchronize_from_peers(
    local: Blockchain, peer_urls: list[str], timeout: float = 5.0
) -> bool:
    """Télécharge les chaînes des pairs et garde celle au travail valide maximal."""
    candidates = [
        candidate
        for peer_url in peer_urls
        if (candidate := fetch_peer_chain(peer_url, local.difficulty, timeout)) is not None
    ]
    return synchronize(local, candidates)

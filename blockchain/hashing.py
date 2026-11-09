"""Calcul de l'empreinte canonique et vérification de la difficulté.

Ce module est le **point de contact entre M1 (bloc & chaîne) et M2 (hash,
minage & intégrité)**. La répartition officielle du groupe confie à M2 le
calcul SHA-256 du contenu canonique du bloc, la preuve de travail et la
vérification du hash et de la difficulté.

En isolant ces trois responsabilités dans un fichier dédié, M2 peut les
faire évoluer (autre fonction de hachage, algorithme de minage, ajustement
de la difficulté) sans jamais modifier ``block.py`` ni ``blockchain.py``,
qui restent la propriété de M1. L'API publique de ``Block`` et
``Blockchain`` ne change pas.

Contrat à figer avec M2
------------------------
Le contenu canonique est exactement le dictionnaire produit par
:func:`canonical_payload` : ``index``, ``timestamp``, ``data``,
``previous_hash`` et ``nonce``. Le hash est le SHA-256 de sa sérialisation
JSON avec ``sort_keys=True`` et des séparateurs compacts. Tant que M1 et M2
utilisent cette définition, deux nœuds indépendants produisent la même
empreinte pour le même bloc.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = [
    "MAX_DIFFICULTY",
    "canonical_payload",
    "serialize_payload",
    "hash_payload",
    "hash_block",
    "check_difficulty",
]

MAX_DIFFICULTY = hashlib.sha256().digest_size * 2


def _validate_difficulty(difficulty: int) -> None:
    if type(difficulty) is not int:
        raise TypeError("La difficulté doit être un entier.")
    if not 0 <= difficulty <= MAX_DIFFICULTY:
        raise ValueError(
            f"La difficulté doit être comprise entre 0 et {MAX_DIFFICULTY}."
        )


def canonical_payload(block: Any) -> dict[str, Any]:
    """Retourne le contenu canonique d'un bloc, couvert par son empreinte.

    Parameters
    ----------
    block : Block
        Tout objet exposant les attributs ``index``, ``timestamp``, ``data``,
        ``previous_hash`` et ``nonce``.

    Returns
    -------
    dict
        Le dictionnaire canonique. Le champ ``hash`` en est volontairement
        exclu : une empreinte ne se signe pas elle-même.
    """
    return {
        "index": block.index,
        "timestamp": block.timestamp,
        "data": block.data,
        "previous_hash": block.previous_hash,
        "nonce": getattr(block, "nonce", 0),
    }


def serialize_payload(payload: dict[str, Any]) -> str:
    """Sérialise un payload canonique en JSON déterministe.

    ``sort_keys=True`` garantit que l'ordre d'insertion des clés du
    dictionnaire ``data`` n'influence pas le résultat, et les séparateurs
    compacts évitent que deux encodeurs divergeant sur les espaces
    produisent des empreintes différentes. Les valeurs non représentables
    en JSON standard sont rejetées au lieu d'être converties implicitement.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def hash_payload(payload: dict[str, Any]) -> str:
    """Calcule le SHA-256 hexadécimal d'un payload canonique."""
    return hashlib.sha256(serialize_payload(payload).encode("utf-8")).hexdigest()


def hash_block(block: Any) -> str:
    """Calcule l'empreinte d'un bloc à partir de son contenu canonique."""
    return hash_payload(canonical_payload(block))


def check_difficulty(hash_hex: str, difficulty: int) -> bool:
    """Indique si une empreinte respecte la difficulté demandée.

    La difficulté s'exprime en nombre de zéros hexadécimaux en tête de
    l'empreinte : ``difficulty=2`` exige un hash commençant par ``"00"``.
    Une difficulté nulle n'impose rien. Les difficultés négatives,
    supérieures à la longueur d'un hash SHA-256 ou non entières sont rejetées.
    """
    _validate_difficulty(difficulty)
    if not isinstance(hash_hex, str):
        raise TypeError("L'empreinte doit être une chaîne de caractères.")
    return hash_hex.startswith("0" * difficulty)

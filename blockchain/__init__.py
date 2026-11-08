"""Blockchain financière - module principal.

Expose les structures de données cœur du projet : le bloc et la chaîne.

Répartition du groupe
---------------------
- **M1 (bloc & chaîne)** — :class:`Block`, :class:`Blockchain`
- **M2 (hash, minage & intégrité)** — :mod:`blockchain.hashing`,
  :mod:`blockchain.mining`
- **M3 (API & communication)** — routes FastAPI, à venir
- **M4 (validation & synchronisation)** — à venir
- **M5 (interface & intégration)** — tableau de bord, à venir
"""

from .block import Block
from .blockchain import (
    GENESIS_DATA,
    GENESIS_PREVIOUS_HASH,
    GENESIS_TIMESTAMP,
    Blockchain,
)
from .hashing import canonical_payload, check_difficulty, hash_block
from .mining import mine_block, work_of

__all__ = [
    "Block",
    "Blockchain",
    "GENESIS_DATA",
    "GENESIS_PREVIOUS_HASH",
    "GENESIS_TIMESTAMP",
    "canonical_payload",
    "check_difficulty",
    "hash_block",
    "mine_block",
    "work_of",
]

__version__ = "0.1.0"

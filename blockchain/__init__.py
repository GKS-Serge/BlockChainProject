"""Blockchain financière - module principal.

Expose les structures de données cœur du projet : le bloc et la chaîne.
"""

from .block import Block
from .blockchain import (
    GENESIS_DATA,
    GENESIS_PREVIOUS_HASH,
    GENESIS_TIMESTAMP,
    Blockchain,
)

__all__ = [
    "Block",
    "Blockchain",
    "GENESIS_DATA",
    "GENESIS_PREVIOUS_HASH",
    "GENESIS_TIMESTAMP",
]

__version__ = "0.1.0"

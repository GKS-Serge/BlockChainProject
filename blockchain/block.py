"""Bloc (Block) de la blockchain financière.

Ce module définit la structure de données centrale du projet : le bloc.
Un bloc contient l'empreinte cryptographique du bloc précédent, ce qui
transforme une simple liste de blocs en une chaîne immuable et vérifiable.

Attributs
----------
index          : position du bloc dans la chaîne (0 pour le bloc genesis)
timestamp      : horodatage Unix de création du bloc
data           : charge utile du bloc (transaction financière)
previous_hash  : empreinte SHA-256 du bloc précédent
hash           : empreinte SHA-256 calculée à partir des champs ci-dessus
nonce          : valeur de travail, réservée à la partie minage du projet
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

__all__ = ["Block"]


@dataclass
class Block:
    """Un bloc de la chaîne.

    L'empreinte (``hash``) est calculée automatiquement à l'instanciation
    à partir de ``index``, ``timestamp``, ``data``, ``previous_hash`` et
    ``nonce``. Elle ne peut donc pas être falsifiée sans invalider le bloc.
    """

    index: int
    timestamp: float
    data: dict[str, Any]
    previous_hash: str
    hash: str = field(default="")
    nonce: int = 0

    def __post_init__(self) -> None:
        # Si le hash n'est pas fourni (cas normal), on le calcule.
        if not self.hash:
            self.hash = self.compute_hash()

    # ------------------------------------------------------------------
    # Calcul de l'empreinte
    # ------------------------------------------------------------------
    def payload(self) -> dict[str, Any]:
        """Retourne les champs signés par l'empreinte (le hash est exclu)."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }

    def compute_hash(self) -> str:
        """Calcule l'empreinte SHA-256 du bloc.

        La sérialisation JSON est canonique (``sort_keys=True`` et séparateurs
        compacts) afin que le hash ne dépende pas de l'ordre des clés du
        dictionnaire ``data``. Deux blocs ayant les mêmes champs produisent
        donc toujours la même empreinte.
        """
        encoded = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def is_hash_valid(self) -> bool:
        """Indique si l'empreinte stockée correspond au contenu du bloc."""
        return self.hash == self.compute_hash()

    def meets_difficulty(self, difficulty: int) -> bool:
        """Indique si l'empreinte respecte la difficulté demandée.

        La difficulté s'exprime en nombre de zéros hexadécimaux en tête de
        l'empreinte : ``difficulty=2`` exige un hash commençant par ``"00"``.

        Cette vérification sert à la partie minage du projet ; elle est
        fournie ici pour que la chaîne puisse valider des blocs minés
        ailleurs.
        """
        if difficulty <= 0:
            return True
        return self.hash.startswith("0" * difficulty)

    # ------------------------------------------------------------------
    # Sérialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Représentation du bloc sous forme de dictionnaire (JSON-ready)."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, block: Mapping[str, Any]) -> "Block":
        """Reconstruit un bloc à partir de sa représentation dictionnaire."""
        return cls(
            index=block["index"],
            timestamp=block["timestamp"],
            data=dict(block["data"]),
            previous_hash=block["previous_hash"],
            hash=block["hash"],
            nonce=block.get("nonce", 0),
        )

    @staticmethod
    def new_timestamp() -> float:
        """Retourne l'horodatage courant (séparé pour faciliter les tests)."""
        return time.time()

    def __str__(self) -> str:  # pragma: no cover - confort de débogage
        return (
            f"Block(index={self.index}, "
            f"timestamp={self.timestamp:.0f}, "
            f"data={self.data}, "
            f"hash={self.hash[:12]}...)"
        )

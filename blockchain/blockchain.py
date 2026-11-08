"""Chaîne de blocs (Blockchain) de la blockchain financière.

La classe :class:`Blockchain` orchestre l'ensemble de la chaîne :

* elle crée automatiquement le bloc genesis (premier bloc de la chaîne) ;
* elle sait ajouter un bloc à la suite du dernier bloc connu ;
* elle sait vérifier l'intégrité de toute la chaîne.

Dans le domaine de la finance, la charge utile (``data``) d'un bloc porte
une transaction : expéditeur, destinataire et montant.
"""

from __future__ import annotations

from typing import Any

from .block import Block

__all__ = ["Blockchain", "GENESIS_DATA", "GENESIS_PREVIOUS_HASH", "GENESIS_TIMESTAMP"]

# Horodatage fixe du bloc genesis : il rend le bloc genesis déterministe,
# c'est-à-dire identique sur tous les nouds du réseau.
GENESIS_TIMESTAMP = 1_700_000_000.0

# Empreinte conventionnelle du "bloc précédent" du genesis : une suite de zéros.
GENESIS_PREVIOUS_HASH = "0" * 64

# Contenu initial de la blockchain financière.
GENESIS_DATA: dict[str, Any] = {
    "type": "genesis",
    "message": "Genesis Block - Finance Blockchain",
    "reserve": "0.00",
}


class Blockchain:
    """Une chaîne de blocs finance.

    Attributs
    ---------
    chain : list[Block]
        La liste ordonnée des blocs, du genesis au dernier bloc ajouté.
    """

    def __init__(self) -> None:
        self.chain: list[Block] = [self.create_genesis_block()]

    # ------------------------------------------------------------------
    # Genesis
    # ------------------------------------------------------------------
    @staticmethod
    def create_genesis_block() -> Block:
        """Crée et retourne le bloc genesis (index 0, hash précédent nul)."""
        return Block(
            index=0,
            timestamp=GENESIS_TIMESTAMP,
            data=dict(GENESIS_DATA),
            previous_hash=GENESIS_PREVIOUS_HASH,
        )

    # ------------------------------------------------------------------
    # Accès à la chaîne
    # ------------------------------------------------------------------
    @property
    def last_block(self) -> Block:
        """Retourne le dernier bloc de la chaîne (lève IndexError si vide)."""
        return self.chain[-1]

    def __len__(self) -> int:
        return len(self.chain)

    # ------------------------------------------------------------------
    # Ajout de blocs
    # ------------------------------------------------------------------
    def add_block(self, data: dict[str, Any]) -> Block:
        """Ajoute un bloc à la fin de la chaîne et retourne ce bloc.

        Le nouveau bloc reprend l'empreinte du dernier bloc comme
        ``previous_hash`` et incrémente l'index.

        Parameters
        ----------
        data : dict
            Charge utile du bloc (transaction financière).

        Raises
        ------
        ValueError
            Si la chaîne est vide ou si ``data`` n'est pas un dictionnaire.
        """
        if not isinstance(data, dict):
            raise ValueError("Les données d'un bloc doivent être un dictionnaire.")

        last_block = self.last_block

        block = Block(
            index=last_block.index + 1,
            timestamp=Block.new_timestamp(),
            data=dict(data),
            previous_hash=last_block.hash,
        )
        self.chain.append(block)
        return block

    def add_transaction(
        self,
        sender: str,
        receiver: str,
        amount: float,
        currency: str = "EUR",
    ) -> Block:
        """Ajoute un bloc contenant une transaction financière.

        Parameters
        ----------
        sender : str
            Adresse de l'expéditeur.
        receiver : str
            Adresse du destinataire.
        amount : float
            Montant transféré (doit être strictement positif).
        currency : str
            Devise du transfert, ``EUR`` par défaut.

        Raises
        ------
        ValueError
            Si le montant est négatif ou nul, ou si l'expéditeur est vide.
        """
        if amount is None or amount <= 0:
            raise ValueError("Le montant d'une transaction doit être strictement positif.")
        if not sender:
            raise ValueError("L'expéditeur d'une transaction est obligatoire.")

        data = {
            "type": "transaction",
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "currency": currency,
        }
        return self.add_block(data)

    # ------------------------------------------------------------------
    # Vérification d'intégrité
    # ------------------------------------------------------------------
    def is_valid(self) -> bool:
        """Vérifie l'intégrité complète de la chaîne.

        Contrôle, pour chaque bloc : l'index, le lien vers le bloc précédent
        et la correspondance de l'empreinte recalculée.
        """
        if not self.chain:
            return False

        genesis = self.chain[0]
        if genesis.index != 0 or genesis.previous_hash != GENESIS_PREVIOUS_HASH:
            return False

        for current, following in zip(self.chain, self.chain[1:]):
            if following.index != current.index + 1:
                return False
            if following.previous_hash != current.hash:
                return False
            if not following.is_hash_valid():
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Sérialise la chaîne complète."""
        return {"chain": [block.to_dict() for block in self.chain]}

    def __str__(self) -> str:  # pragma: no cover - confort de débogage
        return f"Blockchain(length={len(self.chain)}, valid={self.is_valid()})"

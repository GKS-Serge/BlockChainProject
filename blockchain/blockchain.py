"""Chaîne de blocs (Blockchain) de la blockchain financière.

La classe :class:`Blockchain` orchestre l'ensemble de la chaîne :

* elle crée automatiquement le bloc genesis (premier bloc de la chaîne) ;
* elle sait ajouter un bloc à la suite du dernier bloc connu ;
* elle sait vérifier l'intégrité de toute la chaîne.

Dans le domaine de la finance, la charge utile (``data``) d'un bloc porte
une transaction : expéditeur, destinataire et montant.

Répartition du groupe
---------------------
Ce fichier appartient à **M1 (bloc & chaîne)**. Le calcul de l'empreinte et
la vérification de la difficulté vivent dans :mod:`blockchain.hashing`, qui
appartient à **M2 (hash, minage & intégrité)**. Les points d'entrée
publics (`add_block`, `add_transaction`, `is_valid`, `validate`) restent
stables quel que soit le travail de M2.
"""

from __future__ import annotations

from typing import Any, Mapping

from .block import Block
from .hashing import check_difficulty

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
    difficulty : int
        Difficulté de preuve de travail exigée pour les blocs non-genesis.
        ``0`` (défaut) désactive la vérification de minage.
    """

    def __init__(self, difficulty: int = 0) -> None:
        self.difficulty = difficulty
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
    def add_block(
        self,
        data: dict[str, Any],
        nonce: int | None = None,
        difficulty: int | None = None,
    ) -> Block:
        """Ajoute un bloc à la fin de la chaîne et retourne ce bloc.

        Le nouveau bloc reprend l'empreinte du dernier bloc comme
        ``previous_hash`` et incrémente l'index. Le ``previous_hash`` n'est
        jamais fourni par l'appelant : c'est la chaîne qui garantit le lien.

        Parameters
        ----------
        data : dict
            Charge utile du bloc (transaction financière).
        nonce : int, optional
            Valeur de travail, réservée à la partie minage. Par défaut ``0``.
        difficulty : int, optional
            Difficulté exigée pour ce bloc. Par défaut, celle de la chaîne.

        Raises
        ------
        ValueError
            Si ``data`` n'est pas un dictionnaire, ou si le bloc ne satisfait
            pas la difficulté demandée.
        """
        if not isinstance(data, dict):
            raise ValueError("Les données d'un bloc doivent être un dictionnaire.")

        required_difficulty = self.difficulty if difficulty is None else difficulty

        last_block = self.last_block

        block = Block(
            index=last_block.index + 1,
            timestamp=Block.new_timestamp(),
            data=dict(data),
            previous_hash=last_block.hash,
            nonce=0 if nonce is None else nonce,
        )

        if not block.meets_difficulty(required_difficulty):
            raise ValueError(
                f"Le bloc ne satisfait pas la difficulté {required_difficulty} "
                f"(hash={block.hash})."
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
        """Indique si la chaîne est intègre (voir :meth:`validate`)."""
        return not self.validate()

    def validate(self) -> list[str]:
        """Vérifie l'intégrité de la chaîne et retourne la liste des anomalies.

        Chaque anomalie est décrite en une phrase, ce qui permet à une partie
        CLI ou API d'expliquer *pourquoi* la chaîne est invalide.

        Returns
        -------
        list[str]
            Liste vide si la chaîne est intègre, sinon la liste des
            problèmes détectés.
        """
        problems: list[str] = []

        if not self.chain:
            return ["La chaîne est vide."]

        genesis = self.chain[0]
        if genesis.index != 0:
            problems.append(
                f"Le bloc genesis devrait avoir l'index 0 (index={genesis.index})."
            )
        if genesis.previous_hash != GENESIS_PREVIOUS_HASH:
            problems.append(
                "Le bloc genesis devrait pointer vers une empreinte de 64 zéros."
            )
        if not genesis.is_hash_valid():
            problems.append("L'empreinte du bloc genesis ne correspond pas à son contenu.")

        for position, (current, following) in enumerate(
            zip(self.chain, self.chain[1:]), start=1
        ):
            if following.index != current.index + 1:
                problems.append(
                    f"Le bloc {position} a l'index {following.index}, "
                    f"attendu {current.index + 1}."
                )
            if following.previous_hash != current.hash:
                problems.append(
                    f"Le bloc {position} ne pointe pas vers l'empreinte du bloc "
                    f"{position - 1}."
                )
            if not following.is_hash_valid():
                problems.append(
                    f"L'empreinte du bloc {position} ne correspond pas à son contenu."
                )
            if not following.meets_difficulty(self.difficulty):
                problems.append(
                    f"Le bloc {position} ne satisfait pas la difficulté "
                    f"{self.difficulty}."
                )

        return problems

    def total_work(self) -> int:
        """Retourne le travail cumulé de la chaîne.

        Cette mesure sert la règle de sélection de **M4 (validation &
        synchronisation)** : entre deux chaînes valides, celle qui a le plus
        de travail cumulé l'emporte. Le calcul lui-même appartient à M2 et
        peut être remplacé via :func:`blockchain.mining.work_of`.
        """
        from .mining import work_of

        return sum(work_of(block, self.difficulty) for block in self.chain)

    def to_dict(self) -> dict[str, Any]:
        """Sérialise la chaîne complète."""
        return {"chain": [block.to_dict() for block in self.chain]}

    @classmethod
    def from_dict(cls, chain: Mapping[str, Any]) -> "Blockchain":
        """Reconstruit une chaîne à partir de sa représentation dictionnaire.

        Utilisé par **M3 (API & communication)** pour décoder une chaîne
        reçue par HTTP. Les blocs sont reconstruits sans recalculer leur
        empreinte : la validation se fait ensuite via :meth:`validate`.
        """
        blockchain = cls()
        blockchain.chain = [Block.from_dict(block) for block in chain["chain"]]
        return blockchain

    def __str__(self) -> str:  # pragma: no cover - confort de débogage
        return f"Blockchain(length={len(self.chain)}, valid={self.is_valid()})"

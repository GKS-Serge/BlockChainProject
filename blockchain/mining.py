"""Preuve de travail (Proof of Work) — module appartient à M2.

Ce module est la **propriété de M2 (hash, minage & intégrité)**. M1 fournit
l'interface et les points d'accroche ; M2 y implémente l'algorithme de
minage, l'ajustement de la difficulté et les vérifications associées.

Contrat avec M1
---------------
``mine_block`` renvoie un bloc dont l'empreinte respecte la difficulté
demandée et dont le ``nonce`` est le nombre d'essais nécessaires. La chaîne
de M1 refuse d'ajouter un bloc qui ne respecte pas la difficulté (voir
``Blockchain.add_block``), donc un bloc produit ici est toujours acceptable
par la chaîne.

Côté M1, rien dans ``block.py`` ni ``blockchain.py`` n'a besoin d'être
modifié pour que M2 fasse évoluer ce module.
"""

from __future__ import annotations

from typing import Callable

from .block import Block
from .hashing import _validate_difficulty, check_difficulty, hash_block

__all__ = ["mine_block", "work_of"]


def work_of(block: Block, difficulty: int) -> int:
    """Retourne le travail qu'un bloc contribue à la chaîne.

    Un bloc conforme à la difficulté ``d`` contribue ``16 ** d`` unités de
    travail. Cette mesure sert à la règle de sélection de M4 (la chaîne
    valide ayant le plus de travail cumulé l'emporte).
    """
    _validate_difficulty(difficulty)
    if difficulty == 0:
        return 1
    return 16**difficulty


def mine_block(
    block: Block,
    difficulty: int,
    hash_fn: Callable[[Block], str] = hash_block,
) -> Block:
    """Cherche un ``nonce`` tel que l'empreinte du bloc respecte la difficulté.

    Le nonce est incrémenté jusqu'à ce que l'empreinte commence par le
    nombre de zéros hexadécimaux exigé. La fonction est volontairement
    simple : M2 est libre de la remplacer par un algorithme plus efficace
    sans changer sa signature.

    Parameters
    ----------
    block : Block
        Le bloc à miner. Son ``nonce`` de départ sert de point de départ.
    difficulty : int
        Difficulté exigée, en zéros hexadécimaux de tête.
    hash_fn : Callable[[Block], str]
        Fonction de hachage, injectable pour permettre à M2 de la remplacer.

    Returns
    -------
    Block
        Le même bloc, avec un ``nonce`` et un ``hash`` recalculés.

    Raises
    ------
    TypeError
        Si la difficulté n'est pas un entier ou si le nonce du bloc n'est
        pas un entier.
    ValueError
        Si la difficulté est hors limites ou si le nonce du bloc est négatif.
    """
    _validate_difficulty(difficulty)
    if type(block.nonce) is not int:
        raise TypeError("Le nonce du bloc doit être un entier.")
    if block.nonce < 0:
        raise ValueError("Le nonce du bloc ne peut pas être négatif.")

    if difficulty == 0:
        # Aucune preuve de travail demandée : le nonce courant est conservé.
        candidate = hash_fn(block)
        check_difficulty(candidate, difficulty)
        block.hash = candidate
        return block

    original_nonce = block.nonce
    nonce = original_nonce
    original_hash = block.hash
    mined = False
    try:
        while True:
            block.nonce = nonce
            candidate = hash_fn(block)
            if check_difficulty(candidate, difficulty):
                block.hash = candidate
                mined = True
                return block
            nonce += 1
    finally:
        if not mined:
            block.nonce = original_nonce
            block.hash = original_hash

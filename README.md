# Blockchain financière

Implémentation en Python du cœur d'une blockchain orientée finance : le **bloc**
et la **chaîne de blocs**.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Utilisation

```python
from blockchain import Blockchain

blockchain = Blockchain()                       # crée le bloc genesis
blockchain.add_transaction("0xAlice", "0xBob", 250.0)   # ajoute un bloc
blockchain.add_block({"type": "audit", "note": "contrôle KYC"})

assert blockchain.is_valid()
print(len(blockchain.chain))   # 3
```

## Structure

| Fichier | Rôle |
| --- | --- |
| `blockchain/block.py` | Classe `Block` : `index`, `timestamp`, `data`, `previous_hash`, `hash` + calcul SHA-256 |
| `blockchain/blockchain.py` | Classe `Blockchain` : bloc genesis, `add_block`, `add_transaction`, `is_valid` |
| `tests/test_blockchain.py` | Tests pytest : chaîne avec genesis + ajout de bloc, intégrité, sérialisation |

## Tests

```bash
pytest
```

## Règle d'intégrité

Le hash d'un bloc est le SHA-256 de la sérialisation JSON canonique de
`index`, `timestamp`, `data` et `previous_hash`. Chaque bloc embarque le hash
du précédent : modifier un bloc invalide toute la chaîne qui le suit, ce que
vérifie `Blockchain.is_valid()`.

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
| `blockchain/block.py` | Classe `Block` : `index`, `timestamp`, `data`, `previous_hash`, `hash`, `nonce` + calcul SHA-256 |
| `blockchain/blockchain.py` | Classe `Blockchain` : bloc genesis, `add_block`, `add_transaction`, `is_valid`, `validate` |
| `tests/test_blockchain.py` | Tests pytest : chaîne avec genesis + ajout de bloc, intégrité, sérialisation |

## API publique

| Méthode | Rôle |
| --- | --- |
| `Blockchain()` | Crée la chaîne avec son bloc genesis |
| `chain.add_block(data)` | Ajoute un bloc, lie son `previous_hash` au dernier bloc |
| `chain.add_transaction(sender, receiver, amount, currency="EUR")` | Ajoute un bloc contenant une transaction |
| `chain.is_valid()` | `True` si la chaîne est intègre |
| `chain.validate()` | Liste des anomalies (vide si la chaîne est intègre) |
| `block.is_hash_valid()` | Recalcule l'empreinte et la compare à celle stockée |
| `block.meets_difficulty(d)` | Vérifie la preuve de travail (zéros hex en tête du hash) |

## Tests

```bash
pytest
```

Le test livré par le groupe est `test_add_block_to_the_chain` : il crée une
chaîne avec un bloc genesis puis ajoute un bloc.

```bash
pytest tests/test_blockchain.py::test_add_block_to_the_chain
```

## Règle d'intégrité

Le hash d'un bloc est le SHA-256 de la sérialisation JSON canonique de
`index`, `timestamp`, `data`, `previous_hash` et `nonce`. La sérialisation est
canonique (`sort_keys=True`, séparateurs compacts) : l'ordre des clés du
payload ne change donc pas l'empreinte, et deux nœuds qui construisent le même
contenu obtiennent le même hash.

Chaque bloc embarque le hash du précédent : modifier un bloc invalide toute la
chaîne qui le suit, ce que vérifie `Blockchain.is_valid()`.

## Points d'extension pour les autres parties du groupe

Ces points sont prévus pour que les autres parties se branchent sans modifier
l'API existante :

- **Minage / preuve de travail** — `add_block(data, nonce=None, difficulty=None)`
  et `Blockchain(difficulty=N)`. Le `nonce` fait partie du payload hashé, donc
  il est couvert par l'empreinte. `meets_difficulty(d)` vérifie que le hash
  commence par `d` zéros hexadécimaux.
- **Signature** — à placer dans `data["signature"]` et non dans le payload
  hashé, pour ne pas invalider les blocs déjà créés.
- **Persistance** — `to_dict()` / `from_dict()` sur `Block` et `Blockchain`.
- **Rapport d'erreurs** — `is_valid()` renvoie un booléen, `validate()` renvoie
  la liste des raisons de l'échec.

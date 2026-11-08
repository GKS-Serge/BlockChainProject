# BlockChainProject

Projet d'école : blockchain orientée finance, écrite en Python.

## Partie 1 — Bloc et chaîne de blocs

Implémentation du cœur de la blockchain : la classe **Block** et la classe
**Blockchain** (bloc genesis, ajout de blocs, vérification d'intégrité).

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Utilisation

```python
from blockchain import Blockchain

blockchain = Blockchain()                       # crée le bloc genesis
blockchain.add_transaction("0xAlice", "0xBob", 250.0)   # ajoute un bloc
blockchain.add_block({"type": "audit", "note": "contrôle KYC"})

assert blockchain.is_valid()
print(len(blockchain.chain))   # 3
```

### Structure

| Fichier | Rôle | Partie |
| --- | --- | --- |
| `blockchain/block.py` | Classe `Block` : `index`, `timestamp`, `data`, `previous_hash`, `hash`, `nonce` | **M1** |
| `blockchain/blockchain.py` | Classe `Blockchain` : bloc genesis, `add_block`, `add_transaction`, `is_valid`, `validate` | **M1** |
| `blockchain/hashing.py` | Contenu canonique, SHA-256, vérification de la difficulté | **M2** |
| `blockchain/mining.py` | Preuve de travail (`mine_block`), mesure du travail cumulé | **M2** |
| `tests/test_blockchain.py` | Tests pytest : chaîne avec genesis + ajout de bloc, intégrité, sérialisation | **M1** |
| `tests/test_hashing.py` | Tests pytest : contenu canonique, minage, travail cumulé | **M2** |

### Répartition du groupe

| Membre | Responsabilité | Livrable |
| --- | --- | --- |
| **M1** | Bloc & chaîne | Un test qui crée une chaîne avec un Genesis Block et ajoute un bloc |
| **M2** | Hash, minage & intégrité | Un bloc miné et un test qui détecte une donnée modifiée |
| **M3** | API & communication | Deux nœuds s'envoient une transaction et un bloc via HTTP |
| **M4** | Validation & synchronisation | Un nœud reconnecté récupère la chaîne valide la plus avancée |
| **M5** | Interface & intégration | Une page web affichant les données réelles d'un nœud |

### Points d'intégration fournis par M1

Pour que les autres parties se branchent sans réécrire l'API existante :

- **M2** — `blockchain/hashing.py` et `blockchain/mining.py` sont isolés : M2 peut
  remplacer la fonction de hachage, l'algorithme de minage ou l'ajustement de
  la difficulté sans toucher `block.py` ni `blockchain.py`. `Block.compute_hash()`
  et `Block.meets_difficulty()` délèguent vers ces modules.
  `mine_block(block, difficulty, hash_fn=...)` accepte une fonction de hachage
  injectable.
- **M3** — `Block.from_dict()` / `Blockchain.from_dict()` décodent une chaîne
  reçue par HTTP. `Blockchain.to_dict()` la sérialise.
- **M4** — `chain.validate()` retourne la liste des anomalies,
  `chain.total_work()` le travail cumulé, base de la règle de sélection de la
  chaîne la plus avancée.
- **M5** — `chain.to_dict()` expose l'état du nœud : blocs, hash, transactions.

### API publique

| Méthode | Rôle |
| --- | --- |
| `Blockchain()` | Crée la chaîne avec son bloc genesis |
| `chain.add_block(data)` | Ajoute un bloc, lie son `previous_hash` au dernier bloc |
| `chain.add_transaction(sender, receiver, amount, currency="EUR")` | Ajoute un bloc contenant une transaction |
| `chain.is_valid()` | `True` si la chaîne est intègre |
| `chain.validate()` | Liste des anomalies (vide si la chaîne est intègre) |
| `block.is_hash_valid()` | Recalcule l'empreinte et la compare à celle stockée |
| `block.meets_difficulty(d)` | Vérifie la preuve de travail (zéros hex en tête du hash) |

### Tests

```bash
pytest
```

Le test livré par le groupe est `test_add_block_to_the_chain` : il crée une
chaîne avec un bloc genesis puis ajoute un bloc.

```bash
pytest tests/test_blockchain.py::test_add_block_to_the_chain
```

### Règle d'intégrité

Le hash d'un bloc est le SHA-256 de la sérialisation JSON canonique de
`index`, `timestamp`, `data`, `previous_hash` et `nonce`. La sérialisation est
canonique (`sort_keys=True`, séparateurs compacts) : l'ordre des clés du
payload ne change donc pas l'empreinte, et deux nœuds qui construisent le même
contenu obtiennent le même hash.

Chaque bloc embarque le hash du précédent : modifier un bloc invalide toute la
chaîne qui le suit, ce que vérifie `Blockchain.is_valid()`.

### Points d'extension pour les autres parties du groupe

Ces points sont prévus pour que les autres parties se branchent sans modifier
l'API existante :

- **Minage / preuve de travail (M2)** — `add_block(data, nonce=None, difficulty=None)`
  et `Blockchain(difficulty=N)`. Le `nonce` fait partie du payload hashé, donc
  il est couvert par l'empreinte. `meets_difficulty(d)` vérifie que le hash
  commence par `d` zéros hexadécimaux. L'implémentation du minage est dans
  `blockchain/mining.py` : `mine_block(block, difficulty, hash_fn=...)`.
- **Signature (à situer)** — à placer dans `data["signature"]` et non dans le
  payload hashé, pour ne pas invalider les blocs déjà créés.
- **Persistance (M3)** — `to_dict()` / `from_dict()` sur `Block` et `Blockchain`.
- **Rapport d'erreurs (M4/M5)** — `is_valid()` renvoie un booléen, `validate()`
  renvoie la liste des raisons de l'échec.

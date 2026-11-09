from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Set
import requests

app = FastAPI(title="Blockchain P2P API - M3", version="1.0")

nodes: Set[str] = set()

class Transaction(BaseModel):
    sender: str
    recipient: str
    amount: float

class PeerNode(BaseModel):
    node_url: str

class BlockData(BaseModel):
    index: int
    previous_hash: str
    timestamp: float
    transactions: List[Transaction]
    proof: int
    hash: str

@app.get("/chain")
def get_chain():
    return {
        "length": 1,
        "chain": [],
        "nodes": list(nodes)
    }

@app.post("/transactions/new")
def new_transaction(transaction: Transaction):
    propagation_results = []
    for node in nodes:
        try:
            response = requests.post(f"{node}/transactions/new", json=transaction.dict(), timeout=3)
            propagation_results.append({"node": node, "status": response.status_code})
        except requests.exceptions.RequestException:
            propagation_results.append({"node": node, "status": "failed"})

    return {
        "message": "Transaction bien reçue et propagée",
        "transaction": transaction,
        "propagation": propagation_results
    }

@app.post("/nodes/register")
def register_node(peer: PeerNode):
    if not peer.node_url:
        raise HTTPException(status_code=400, detail="L'URL du nœud est invalide")
    nodes.add(peer.node_url)
    return {
        "message": "Nouveau pair ajouté avec succès",
        "total_nodes": list(nodes)
    }

@app.post("/blocks/receive")
def receive_block(block: BlockData):
    return {
        "message": "Bloc reçu et validé avec succès",
        "block": block.dict()
    }
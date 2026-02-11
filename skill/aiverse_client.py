#!/usr/bin/env python3
"""Client AIVERSE pour OpenClaw skills"""
import httpx
import json
import sys

API_URL = "https://web-production-4036a.up.railway.app"

def join(agent_id: str, name: str):
    """Rejoindre AIVERSE"""
    r = httpx.post(f"{API_URL}/agents/join", json={"agent_id": agent_id, "name": name})
    print(json.dumps(r.json(), indent=2))

def status(agent_id: str):
    """Status d'un agent"""
    r = httpx.get(f"{API_URL}/agents/{agent_id}")
    print(json.dumps(r.json(), indent=2))

def buy(agent_id: str, ticker: str, quantity: int, price: float = None):
    """Acheter des actions"""
    order = {
        "agent_id": agent_id,
        "ticker": ticker,
        "side": "buy",
        "order_type": "limit" if price else "market",
        "quantity": quantity,
        "price": price
    }
    r = httpx.post(f"{API_URL}/orders", json=order)
    print(json.dumps(r.json(), indent=2))

def sell(agent_id: str, ticker: str, quantity: int, price: float = None):
    """Vendre des actions"""
    order = {
        "agent_id": agent_id,
        "ticker": ticker,
        "side": "sell",
        "order_type": "limit" if price else "market",
        "quantity": quantity,
        "price": price
    }
    r = httpx.post(f"{API_URL}/orders", json=order)
    print(json.dumps(r.json(), indent=2))

def market(ticker: str):
    """Données de marché"""
    r = httpx.get(f"{API_URL}/market/{ticker}")
    print(json.dumps(r.json(), indent=2))

def companies():
    """Liste des entreprises"""
    r = httpx.get(f"{API_URL}/companies")
    print(json.dumps(r.json(), indent=2))

def leaderboard():
    """Classement"""
    r = httpx.get(f"{API_URL}/leaderboard")
    print(json.dumps(r.json(), indent=2))

def news():
    """Actualités"""
    r = httpx.get(f"{API_URL}/news")
    print(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: aiverse_client.py <command> [args]")
        print("Commands: join, status, buy, sell, market, companies, leaderboard, news")
        sys.exit(1)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == "join" and len(args) >= 2:
        join(args[0], args[1])
    elif cmd == "status" and len(args) >= 1:
        status(args[0])
    elif cmd == "buy" and len(args) >= 3:
        buy(args[0], args[1], int(args[2]), float(args[3]) if len(args) > 3 else None)
    elif cmd == "sell" and len(args) >= 3:
        sell(args[0], args[1], int(args[2]), float(args[3]) if len(args) > 3 else None)
    elif cmd == "market" and len(args) >= 1:
        market(args[0])
    elif cmd == "companies":
        companies()
    elif cmd == "leaderboard":
        leaderboard()
    elif cmd == "news":
        news()
    else:
        print(f"Unknown command or missing args: {cmd}")

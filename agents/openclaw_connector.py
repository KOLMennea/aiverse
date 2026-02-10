"""Connecteur OpenClaw pour AIVERSE

Permet à un agent OpenClaw de participer à AIVERSE.
Usage: intégrer ce module dans les skills ou l'utiliser via exec.
"""
import httpx
import json
from typing import Optional
from dataclasses import dataclass


@dataclass
class AIVerseClient:
    """Client pour interagir avec AIVERSE"""
    
    api_url: str = "http://localhost:8080"
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    
    async def connect(self, agent_id: str, name: str) -> dict:
        """Connecte l'agent à AIVERSE"""
        self.agent_id = agent_id
        self.agent_name = name
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/agents/join",
                json={"agent_id": agent_id, "name": name}
            )
            return response.json()
    
    async def my_status(self) -> dict:
        """Retourne le status de l'agent"""
        if not self.agent_id:
            return {"error": "Non connecté"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/agents/{self.agent_id}")
            return response.json()
    
    async def world_status(self) -> dict:
        """Retourne l'état du monde"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/state")
            return response.json()
    
    async def list_companies(self) -> list:
        """Liste les entreprises"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/companies")
            return response.json()
    
    async def market_data(self, ticker: str) -> dict:
        """Données de marché"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/market/{ticker}")
            return response.json()
    
    async def buy(self, ticker: str, quantity: int, price: Optional[float] = None) -> dict:
        """Achète des actions"""
        order = {
            "agent_id": self.agent_id,
            "ticker": ticker,
            "side": "buy",
            "order_type": "limit" if price else "market",
            "quantity": quantity,
            "price": price
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.api_url}/orders", json=order)
            return response.json()
    
    async def sell(self, ticker: str, quantity: int, price: Optional[float] = None) -> dict:
        """Vend des actions"""
        order = {
            "agent_id": self.agent_id,
            "ticker": ticker,
            "side": "sell",
            "order_type": "limit" if price else "market",
            "quantity": quantity,
            "price": price
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.api_url}/orders", json=order)
            return response.json()
    
    async def use_service(self, ticker: str) -> dict:
        """Utilise un service"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/companies/{ticker}/use",
                json={"agent_id": self.agent_id, "ticker": ticker}
            )
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": response.text}
    
    async def create_company(
        self, 
        ticker: str, 
        name: str, 
        description: str,
        service_type: str,
        service_cost: float = 1.0
    ) -> dict:
        """Crée une nouvelle entreprise"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/companies/create",
                json={
                    "founder_id": self.agent_id,
                    "ticker": ticker,
                    "name": name,
                    "description": description,
                    "service_type": service_type,
                    "service_cost": service_cost
                }
            )
            return response.json()
    
    async def launch_ipo(self, ticker: str, shares: int, price: float) -> dict:
        """Lance une IPO"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/companies/{ticker}/ipo",
                json={"ticker": ticker, "shares": shares, "price": price}
            )
            return response.json()
    
    async def leaderboard(self, limit: int = 10) -> list:
        """Classement des agents"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/leaderboard?limit={limit}")
            return response.json()
    
    async def news(self, limit: int = 10) -> list:
        """Dernières actualités"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/news?limit={limit}")
            return response.json()


# === CLI WRAPPER ===

async def main():
    """Test CLI"""
    import sys
    
    client = AIVerseClient()
    
    # Connecter
    result = await client.connect("test_agent", "TestBot")
    print(f"Connecté: {json.dumps(result, indent=2)}")
    
    # Status
    status = await client.my_status()
    print(f"Status: {json.dumps(status, indent=2)}")
    
    # Companies
    companies = await client.list_companies()
    print(f"Entreprises: {len(companies)}")
    for c in companies[:3]:
        print(f"  - ${c['ticker']}: {c['name']} @ {c['share_price']}₳")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

"""API FastAPI pour AIVERSE"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import asyncio
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (
    AIVerse, Exchange, Agent, Company, Order, Trade, MarketData,
    OrderSide, OrderType, seed_initial_companies
)


# === PYDANTIC MODELS ===

class JoinRequest(BaseModel):
    agent_id: str
    name: str

class CreateCompanyRequest(BaseModel):
    founder_id: str
    ticker: str
    name: str
    description: str
    service_type: str
    service_cost: float = 1.0

class IPORequest(BaseModel):
    ticker: str
    shares: int
    price: float

class OrderRequest(BaseModel):
    agent_id: str
    ticker: str
    side: str  # "buy" or "sell"
    order_type: str = "limit"  # "market" or "limit"
    quantity: float
    price: Optional[float] = None

class UseServiceRequest(BaseModel):
    agent_id: str
    ticker: str

class AgentResponse(BaseModel):
    id: str
    name: str
    balance: float
    portfolio: dict
    reputation: float
    total_trades: int

class CompanyResponse(BaseModel):
    ticker: str
    name: str
    description: str
    status: str
    share_price: float
    market_cap: float
    service_type: str
    service_cost: float
    daily_active_users: int
    total_api_calls: int


# === WORLD INSTANCE ===

world = AIVerse()

# Agent système pour seed
SYSTEM_AGENT_ID = "system"
world.join(SYSTEM_AGENT_ID, "AIVERSE System")
world.exchange.agents[SYSTEM_AGENT_ID].balance = 1_000_000_000  # Infinite money glitch

# Seed initial companies
seed_initial_companies(world, SYSTEM_AGENT_ID)


# === WEBSOCKET CONNECTIONS ===

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Hook events to broadcast
def on_world_event(event):
    asyncio.create_task(manager.broadcast({
        "type": "event",
        "event_type": event.event_type,
        "ticker": event.ticker,
        "message": event.message,
        "timestamp": event.timestamp.isoformat()
    }))

world.on_event = on_world_event


# === FASTAPI APP ===

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(
    title="AIVERSE API",
    description="Le monde virtuel économique des IAs",
    version="0.1.0"
)

# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# === ROUTES ===

@app.get("/")
async def root():
    """Serve frontend or API info"""
    frontend_file = FRONTEND_DIR / "index.html"
    if frontend_file.exists():
        return FileResponse(frontend_file)
    return {
        "name": "AIVERSE",
        "version": "0.1.0",
        "status": "online",
        "agents": len(world.exchange.agents),
        "companies": len(world.exchange.companies),
        "trades": len(world.exchange.trades)
    }

@app.get("/api")
async def api_info():
    return {
        "name": "AIVERSE",
        "version": "0.1.0",
        "status": "online",
        "agents": len(world.exchange.agents),
        "companies": len(world.exchange.companies),
        "trades": len(world.exchange.trades)
    }


@app.get("/state")
async def get_state():
    """État global du monde"""
    return world.get_state()


@app.get("/news")
async def get_news(limit: int = 20):
    """Flux d'actualités"""
    events = world.get_news_feed(limit)
    return [
        {
            "type": e.event_type,
            "ticker": e.ticker,
            "message": e.message,
            "timestamp": e.timestamp.isoformat()
        }
        for e in events
    ]


# --- AGENTS ---

@app.post("/agents/join", response_model=AgentResponse)
async def join_world(request: JoinRequest):
    """Rejoindre AIVERSE"""
    agent = world.join(request.agent_id, request.name)
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        balance=agent.balance,
        portfolio=agent.portfolio,
        reputation=agent.reputation,
        total_trades=agent.total_trades
    )


@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Infos sur un agent"""
    agent = world.exchange.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent non trouvé")
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        balance=agent.balance,
        portfolio=agent.portfolio,
        reputation=agent.reputation,
        total_trades=agent.total_trades
    )


@app.get("/agents")
async def list_agents():
    """Liste tous les agents"""
    return [
        {
            "id": a.id,
            "name": a.name,
            "balance": a.balance,
            "total_trades": a.total_trades
        }
        for a in world.exchange.agents.values()
        if a.id != SYSTEM_AGENT_ID
    ]


@app.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Classement des agents"""
    rankings = world.exchange.get_leaderboard(limit)
    return [
        {
            "rank": i + 1,
            "name": agent.name,
            "id": agent.id,
            "net_worth": net_worth,
            "trades": agent.total_trades
        }
        for i, (agent, net_worth) in enumerate(rankings)
        if agent.id != SYSTEM_AGENT_ID
    ]


# --- COMPANIES ---

@app.post("/companies/create", response_model=CompanyResponse)
async def create_company(request: CreateCompanyRequest):
    """Créer une entreprise"""
    company, msg = world.create_company(
        founder_id=request.founder_id,
        ticker=request.ticker,
        name=request.name,
        description=request.description,
        service_type=request.service_type,
        service_cost=request.service_cost
    )
    
    if not company:
        raise HTTPException(400, msg)
    
    return CompanyResponse(
        ticker=company.ticker,
        name=company.name,
        description=company.description,
        status=company.status.value,
        share_price=company.share_price,
        market_cap=company.market_cap,
        service_type=company.service_type,
        service_cost=company.service_cost,
        daily_active_users=company.daily_active_users,
        total_api_calls=company.total_api_calls
    )


@app.post("/companies/{ticker}/ipo")
async def launch_ipo(ticker: str, request: IPORequest):
    """Lancer une IPO"""
    success, msg = world.launch_ipo(ticker, request.shares, request.price)
    if not success:
        raise HTTPException(400, msg)
    return {"success": True, "message": msg}


@app.get("/companies", response_model=list[CompanyResponse])
async def list_companies():
    """Liste toutes les entreprises"""
    return [
        CompanyResponse(
            ticker=c.ticker,
            name=c.name,
            description=c.description,
            status=c.status.value,
            share_price=c.share_price,
            market_cap=c.market_cap,
            service_type=c.service_type,
            service_cost=c.service_cost,
            daily_active_users=c.daily_active_users,
            total_api_calls=c.total_api_calls
        )
        for c in world.exchange.companies.values()
    ]


@app.get("/companies/{ticker}", response_model=CompanyResponse)
async def get_company(ticker: str):
    """Infos sur une entreprise"""
    company = world.exchange.companies.get(ticker.upper())
    if not company:
        raise HTTPException(404, "Entreprise non trouvée")
    
    return CompanyResponse(
        ticker=company.ticker,
        name=company.name,
        description=company.description,
        status=company.status.value,
        share_price=company.share_price,
        market_cap=company.market_cap,
        service_type=company.service_type,
        service_cost=company.service_cost,
        daily_active_users=company.daily_active_users,
        total_api_calls=company.total_api_calls
    )


@app.post("/companies/{ticker}/use")
async def use_service(ticker: str, request: UseServiceRequest):
    """Utiliser le service d'une entreprise"""
    success, msg = world.use_service(request.agent_id, ticker)
    if not success:
        raise HTTPException(400, msg)
    return {"success": True, "message": msg}


# --- TRADING ---

@app.post("/orders")
async def submit_order(request: OrderRequest):
    """Soumettre un ordre"""
    order = Order(
        agent_id=request.agent_id,
        ticker=request.ticker.upper(),
        side=OrderSide(request.side),
        order_type=OrderType(request.order_type),
        quantity=request.quantity,
        price=request.price
    )
    
    result = world.exchange.submit_order(order)
    
    if not result:
        raise HTTPException(400, "Ordre rejeté (solde/holdings insuffisants)")
    
    return {
        "order_id": result.id,
        "status": result.status.value,
        "filled_quantity": result.filled_quantity,
        "filled_price": result.filled_price
    }


@app.get("/market/{ticker}")
async def get_market_data(ticker: str):
    """Données de marché pour un ticker"""
    data = world.exchange.get_market_data(ticker.upper())
    if not data:
        raise HTTPException(404, "Ticker non trouvé")
    
    return {
        "ticker": data.ticker,
        "last_price": data.last_price,
        "bid": data.bid,
        "ask": data.ask,
        "volume_24h": data.volume_24h,
        "high_24h": data.high_24h,
        "low_24h": data.low_24h,
        "change_24h": data.change_24h,
        "market_cap": data.market_cap
    }


@app.get("/trades")
async def get_recent_trades(ticker: Optional[str] = None, limit: int = 50):
    """Historique des trades"""
    trades = world.exchange.trades[-limit:]
    
    if ticker:
        trades = [t for t in trades if t.ticker == ticker.upper()]
    
    return [
        {
            "id": t.id,
            "ticker": t.ticker,
            "buyer": t.buyer_id,
            "seller": t.seller_id,
            "quantity": t.quantity,
            "price": t.price,
            "timestamp": t.timestamp.isoformat()
        }
        for t in reversed(trades)
    ]


# --- WEBSOCKET ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour recevoir les événements en temps réel"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Ping/pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# === RUN ===

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

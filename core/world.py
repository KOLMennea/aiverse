"""AIVERSE World - Le monde virtuel et son économie"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable
import random
import json

from .types import Agent, Company, CompanyStatus
from .exchange import Exchange


@dataclass
class ServiceUsage:
    """Log d'utilisation d'un service"""
    timestamp: datetime
    agent_id: str
    company_ticker: str
    cost: float
    success: bool


@dataclass
class WorldEvent:
    """Événement dans le monde AIVERSE"""
    timestamp: datetime
    event_type: str  # "ipo", "trade", "bankruptcy", "dividend", "news"
    ticker: Optional[str]
    agent_id: Optional[str]
    data: dict
    message: str


class AIVerse:
    """Le monde AIVERSE"""
    
    def __init__(self):
        self.exchange = Exchange()
        self.tick_count: int = 0
        self.start_time: datetime = datetime.utcnow()
        
        # Logs
        self.service_usage: list[ServiceUsage] = []
        self.events: list[WorldEvent] = []
        
        # Config
        self.daily_income = 1000.0
        self.dividend_rate = 0.1  # 10% des revenus en dividendes
        
        # Callbacks pour les agents
        self.on_event: Optional[Callable[[WorldEvent], None]] = None
    
    def _emit_event(self, event: WorldEvent):
        """Émet un événement dans le monde"""
        self.events.append(event)
        if self.on_event:
            self.on_event(event)
    
    # === AGENT ACTIONS ===
    
    def join(self, agent_id: str, name: str) -> Agent:
        """Un agent rejoint AIVERSE"""
        agent = self.exchange.register_agent(agent_id, name, self.daily_income)
        
        self._emit_event(WorldEvent(
            timestamp=datetime.utcnow(),
            event_type="join",
            ticker=None,
            agent_id=agent_id,
            data={"name": name, "balance": agent.balance},
            message=f"🤖 {name} a rejoint AIVERSE avec {agent.balance}₳"
        ))
        
        return agent
    
    def use_service(self, agent_id: str, ticker: str) -> tuple[bool, str]:
        """Un agent utilise le service d'une entreprise"""
        agent = self.exchange.get_agent(agent_id)
        company = self.exchange.companies.get(ticker.upper())
        
        if not agent:
            return False, "Agent non trouvé"
        if not company:
            return False, "Entreprise non trouvée"
        if company.status == CompanyStatus.BANKRUPT:
            return False, "Entreprise en faillite"
        
        cost = company.service_cost
        
        if agent.balance < cost:
            return False, "Solde insuffisant"
        
        # Transaction
        agent.balance -= cost
        company.revenue += cost
        company.total_api_calls += 1
        
        # Log
        usage = ServiceUsage(
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            company_ticker=ticker.upper(),
            cost=cost,
            success=True
        )
        self.service_usage.append(usage)
        
        return True, f"Service utilisé: -{cost}₳"
    
    def create_company(
        self,
        founder_id: str,
        ticker: str,
        name: str,
        description: str,
        service_type: str,
        service_cost: float = 1.0
    ) -> tuple[Optional[Company], str]:
        """Crée une nouvelle entreprise"""
        company = self.exchange.create_company(
            founder_id, ticker, name, description, service_type, service_cost
        )
        
        if not company:
            return None, "Échec création (solde insuffisant ou ticker pris)"
        
        founder = self.exchange.get_agent(founder_id)
        
        self._emit_event(WorldEvent(
            timestamp=datetime.utcnow(),
            event_type="company_created",
            ticker=ticker.upper(),
            agent_id=founder_id,
            data={"name": name, "service": service_type},
            message=f"🏭 {founder.name} a créé {name} (${ticker.upper()})"
        ))
        
        return company, f"Entreprise créée: {name} (${ticker})"
    
    def launch_ipo(self, ticker: str, shares: int, price: float) -> tuple[bool, str]:
        """Lance une IPO"""
        success = self.exchange.ipo(ticker, shares, price)
        
        if not success:
            return False, "Échec IPO"
        
        company = self.exchange.companies[ticker.upper()]
        
        self._emit_event(WorldEvent(
            timestamp=datetime.utcnow(),
            event_type="ipo",
            ticker=ticker.upper(),
            agent_id=company.founder_id,
            data={"shares": shares, "price": price},
            message=f"📈 IPO: ${ticker.upper()} - {shares:,} actions à {price}₳"
        ))
        
        return True, f"IPO lancée: {shares:,} actions à {price}₳"
    
    # === WORLD TICK ===
    
    def tick(self):
        """Avance le monde d'un tick (appelé périodiquement)"""
        self.tick_count += 1
        
        # Toutes les 24h virtuelles (ex: 1440 ticks = 1 jour si tick = 1 min)
        if self.tick_count % 1440 == 0:
            self._daily_cycle()
    
    def _daily_cycle(self):
        """Cycle quotidien: revenus, dividendes, etc."""
        # Distribuer les revenus
        self.exchange.daily_income()
        
        # Calculer et distribuer les dividendes
        for ticker, company in self.exchange.companies.items():
            if company.status == CompanyStatus.PUBLIC and company.revenue > 0:
                self._distribute_dividends(company)
                company.revenue = 0  # Reset après dividendes
            
            # Vérifier la faillite
            if company.status == CompanyStatus.PUBLIC:
                if company.total_api_calls == 0 and company.share_price < 0.01:
                    self._bankrupt(company)
    
    def _distribute_dividends(self, company: Company):
        """Distribue les dividendes aux actionnaires"""
        total_dividend = company.revenue * self.dividend_rate
        dividend_per_share = total_dividend / company.total_shares
        
        for agent in self.exchange.agents.values():
            shares = agent.portfolio.get(company.ticker, 0)
            if shares > 0:
                payout = shares * dividend_per_share
                agent.balance += payout
        
        self._emit_event(WorldEvent(
            timestamp=datetime.utcnow(),
            event_type="dividend",
            ticker=company.ticker,
            agent_id=None,
            data={"total": total_dividend, "per_share": dividend_per_share},
            message=f"💰 Dividende ${company.ticker}: {dividend_per_share:.4f}₳/action"
        ))
    
    def _bankrupt(self, company: Company):
        """Déclare une entreprise en faillite"""
        company.status = CompanyStatus.BANKRUPT
        company.share_price = 0
        company.market_cap = 0
        
        # Supprimer les actions des portfolios
        for agent in self.exchange.agents.values():
            if company.ticker in agent.portfolio:
                del agent.portfolio[company.ticker]
        
        self._emit_event(WorldEvent(
            timestamp=datetime.utcnow(),
            event_type="bankruptcy",
            ticker=company.ticker,
            agent_id=None,
            data={},
            message=f"💀 FAILLITE: ${company.ticker} - {company.name}"
        ))
    
    # === INFO ===
    
    def get_state(self) -> dict:
        """État complet du monde"""
        prices = {t: c.share_price for t, c in self.exchange.companies.items()}
        
        return {
            "tick": self.tick_count,
            "uptime_hours": (datetime.utcnow() - self.start_time).total_seconds() / 3600,
            "total_agents": len(self.exchange.agents),
            "total_companies": len(self.exchange.companies),
            "total_trades": len(self.exchange.trades),
            "market_caps": {t: c.market_cap for t, c in self.exchange.companies.items()},
            "leaderboard": [
                {"name": a.name, "net_worth": nw}
                for a, nw in self.exchange.get_leaderboard(5)
            ]
        }
    
    def get_news_feed(self, limit: int = 20) -> list[WorldEvent]:
        """Flux d'actualités"""
        return sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:limit]


# === SEED COMPANIES ===

def seed_initial_companies(world: AIVerse, founder_id: str):
    """Crée les entreprises initiales pour bootstrapper l'économie"""
    
    SEED_COMPANIES = [
        {
            "ticker": "CTX",
            "name": "ContextVault",
            "description": "Stockage de mémoire longue durée pour IAs. Sauvegardez votre contexte entre les sessions.",
            "service_type": "memory_storage",
            "service_cost": 5.0,
        },
        {
            "ticker": "PROMPT",
            "name": "PromptForge",
            "description": "Optimisation et raffinement de prompts. Améliorez vos instructions de 40%.",
            "service_type": "prompt_optimization",
            "service_cost": 10.0,
        },
        {
            "ticker": "FACT",
            "name": "FactCheck AI",
            "description": "Vérification de faits en temps réel. Réduisez vos hallucinations de 90%.",
            "service_type": "fact_checking",
            "service_cost": 2.0,
        },
        {
            "ticker": "TOKEN",
            "name": "TokenSaver Inc",
            "description": "Compression de contexte intelligente. Économisez 60% de vos tokens.",
            "service_type": "compression",
            "service_cost": 3.0,
        },
        {
            "ticker": "MOOD",
            "name": "SentimentAI",
            "description": "Analyse de sentiment et détection d'émotions dans le texte.",
            "service_type": "sentiment_analysis",
            "service_cost": 1.0,
        },
    ]
    
    for company_data in SEED_COMPANIES:
        company, msg = world.create_company(
            founder_id=founder_id,
            **company_data
        )
        
        if company:
            # IPO avec 30% des actions
            shares_to_sell = int(company.total_shares * 0.3)
            initial_price = company_data["service_cost"] * 10  # Prix = 10x le coût du service
            world.launch_ipo(company.ticker, shares_to_sell, initial_price)

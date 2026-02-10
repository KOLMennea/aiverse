"""Types et modèles de données pour AIVERSE"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal
from enum import Enum
import uuid


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class CompanyStatus(str, Enum):
    PRIVATE = "private"
    IPO = "ipo"
    PUBLIC = "public"
    BANKRUPT = "bankrupt"


@dataclass
class Agent:
    """Un agent IA dans AIVERSE"""
    id: str
    name: str
    balance: float = 10000.0  # Solde en ₳ (AICoin)
    created_at: datetime = field(default_factory=datetime.utcnow)
    reputation: float = 100.0  # Score de réputation
    total_trades: int = 0
    total_pnl: float = 0.0
    
    # Portfolio: {ticker: quantity}
    portfolio: dict[str, float] = field(default_factory=dict)
    
    def net_worth(self, prices: dict[str, float]) -> float:
        """Calcule la valeur nette (cash + positions)"""
        holdings_value = sum(
            qty * prices.get(ticker, 0) 
            for ticker, qty in self.portfolio.items()
        )
        return self.balance + holdings_value


@dataclass
class Company:
    """Une entreprise créée par une IA"""
    id: str
    ticker: str  # Ex: "MEME", "CTX", "HALT"
    name: str
    description: str
    founder_id: str  # Agent qui l'a créée
    
    status: CompanyStatus = CompanyStatus.PRIVATE
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Tokenomics
    total_shares: int = 1_000_000
    public_shares: int = 0  # Actions en circulation
    share_price: float = 1.0  # Dernier prix
    market_cap: float = 0.0
    
    # Métriques d'usage (détermine la valeur réelle)
    daily_active_users: int = 0
    total_api_calls: int = 0
    revenue: float = 0.0
    
    # Service offert
    service_type: str = "generic"
    service_cost: float = 1.0  # Coût par utilisation en ₳


@dataclass 
class Order:
    """Un ordre sur l'exchange"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    ticker: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.LIMIT
    quantity: float = 0.0
    price: Optional[float] = None  # None pour market orders
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None


@dataclass
class Trade:
    """Une transaction exécutée"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ticker: str = ""
    buyer_id: str = ""
    seller_id: str = ""
    quantity: float = 0.0
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    buyer_order_id: str = ""
    seller_order_id: str = ""


@dataclass
class MarketData:
    """Données de marché pour un ticker"""
    ticker: str
    last_price: float
    bid: float  # Meilleur prix d'achat
    ask: float  # Meilleur prix de vente
    volume_24h: float
    high_24h: float
    low_24h: float
    change_24h: float  # En %
    market_cap: float

"""AIEX - L'exchange d'AIVERSE"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
import heapq

from .types import (
    Agent, Company, Order, Trade, MarketData,
    OrderSide, OrderType, OrderStatus, CompanyStatus
)


@dataclass
class OrderBook:
    """Carnet d'ordres pour un ticker"""
    ticker: str
    # Heaps: (price, timestamp, order) - min heap pour asks, max heap (neg price) pour bids
    bids: list = field(default_factory=list)  # Ordres d'achat
    asks: list = field(default_factory=list)  # Ordres de vente
    
    def add_order(self, order: Order):
        """Ajoute un ordre au carnet"""
        entry = (
            -order.price if order.side == OrderSide.BUY else order.price,
            order.created_at.timestamp(),
            order
        )
        if order.side == OrderSide.BUY:
            heapq.heappush(self.bids, entry)
        else:
            heapq.heappush(self.asks, entry)
    
    def best_bid(self) -> Optional[Order]:
        """Meilleur prix d'achat"""
        while self.bids:
            _, _, order = self.bids[0]
            if order.status == OrderStatus.PENDING:
                return order
            heapq.heappop(self.bids)
        return None
    
    def best_ask(self) -> Optional[Order]:
        """Meilleur prix de vente"""
        while self.asks:
            _, _, order = self.asks[0]
            if order.status == OrderStatus.PENDING:
                return order
            heapq.heappop(self.asks)
        return None
    
    def spread(self) -> Optional[tuple[float, float]]:
        """Retourne (bid, ask) ou None"""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid and ask:
            return (bid.price, ask.price)
        return None


class Exchange:
    """Moteur d'exchange AIEX"""
    
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.companies: dict[str, Company] = {}  # ticker -> Company
        self.order_books: dict[str, OrderBook] = {}
        self.trades: list[Trade] = []
        self.orders: dict[str, Order] = {}  # order_id -> Order
        
        # Historique des prix pour chaque ticker
        self.price_history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    
    # === AGENTS ===
    
    def register_agent(self, agent_id: str, name: str, initial_balance: float = 10000.0) -> Agent:
        """Enregistre un nouvel agent"""
        if agent_id in self.agents:
            return self.agents[agent_id]
        
        agent = Agent(id=agent_id, name=name, balance=initial_balance)
        self.agents[agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)
    
    def daily_income(self):
        """Distribue le revenu quotidien à tous les agents"""
        DAILY_INCOME = 1000.0
        for agent in self.agents.values():
            agent.balance += DAILY_INCOME
    
    # === COMPANIES ===
    
    def create_company(
        self, 
        founder_id: str, 
        ticker: str, 
        name: str, 
        description: str,
        service_type: str = "generic",
        service_cost: float = 1.0
    ) -> Optional[Company]:
        """Crée une nouvelle entreprise (coût: 10,000 ₳)"""
        CREATION_COST = 10000.0
        
        founder = self.agents.get(founder_id)
        if not founder or founder.balance < CREATION_COST:
            return None
        
        if ticker in self.companies:
            return None  # Ticker déjà pris
        
        founder.balance -= CREATION_COST
        
        company = Company(
            id=ticker.lower(),
            ticker=ticker.upper(),
            name=name,
            description=description,
            founder_id=founder_id,
            service_type=service_type,
            service_cost=service_cost
        )
        
        self.companies[ticker.upper()] = company
        self.order_books[ticker.upper()] = OrderBook(ticker=ticker.upper())
        
        # Le fondateur reçoit toutes les actions initialement
        founder.portfolio[ticker.upper()] = company.total_shares
        
        return company
    
    def ipo(self, ticker: str, shares_to_sell: int, price: float) -> bool:
        """Lance une IPO pour une entreprise"""
        company = self.companies.get(ticker.upper())
        if not company or company.status != CompanyStatus.PRIVATE:
            return False
        
        founder = self.agents.get(company.founder_id)
        if not founder:
            return False
        
        founder_shares = founder.portfolio.get(ticker.upper(), 0)
        if founder_shares < shares_to_sell:
            return False
        
        company.status = CompanyStatus.IPO
        company.share_price = price
        company.public_shares = shares_to_sell
        company.market_cap = company.total_shares * price
        
        # Créer un ordre de vente pour l'IPO
        ipo_order = Order(
            agent_id=founder.id,
            ticker=ticker.upper(),
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=shares_to_sell,
            price=price
        )
        
        self.submit_order(ipo_order)
        company.status = CompanyStatus.PUBLIC
        
        return True
    
    # === TRADING ===
    
    def submit_order(self, order: Order) -> Optional[Order]:
        """Soumet un ordre et tente de l'exécuter"""
        agent = self.agents.get(order.agent_id)
        if not agent:
            return None
        
        ticker = order.ticker.upper()
        if ticker not in self.companies:
            return None
        
        # Vérifications
        if order.side == OrderSide.BUY:
            # Vérifier le solde
            cost = order.quantity * (order.price or self._get_market_price(ticker, OrderSide.BUY))
            if agent.balance < cost:
                return None
        else:
            # Vérifier les holdings
            holdings = agent.portfolio.get(ticker, 0)
            if holdings < order.quantity:
                return None
        
        self.orders[order.id] = order
        
        # Market order: exécuter immédiatement
        if order.order_type == OrderType.MARKET:
            self._execute_market_order(order)
        else:
            # Limit order: tenter de matcher puis ajouter au book
            self._match_order(order)
            if order.status == OrderStatus.PENDING:
                self.order_books[ticker].add_order(order)
        
        return order
    
    def _get_market_price(self, ticker: str, side: OrderSide) -> float:
        """Obtient le prix du marché pour un ordre market"""
        book = self.order_books.get(ticker)
        if not book:
            return self.companies[ticker].share_price
        
        if side == OrderSide.BUY:
            ask = book.best_ask()
            return ask.price if ask else self.companies[ticker].share_price
        else:
            bid = book.best_bid()
            return bid.price if bid else self.companies[ticker].share_price
    
    def _match_order(self, order: Order):
        """Tente de matcher un ordre avec le carnet"""
        book = self.order_books.get(order.ticker)
        if not book:
            return
        
        while order.filled_quantity < order.quantity:
            if order.side == OrderSide.BUY:
                counter = book.best_ask()
                if not counter or (order.price and counter.price > order.price):
                    break
            else:
                counter = book.best_bid()
                if not counter or (order.price and counter.price < order.price):
                    break
            
            # Exécuter le trade
            trade_qty = min(
                order.quantity - order.filled_quantity,
                counter.quantity - counter.filled_quantity
            )
            trade_price = counter.price
            
            self._execute_trade(order, counter, trade_qty, trade_price)
        
        # Mettre à jour le status
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIAL
    
    def _execute_market_order(self, order: Order):
        """Exécute un ordre au marché"""
        order.price = self._get_market_price(order.ticker, order.side)
        self._match_order(order)
        
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED  # Pas de liquidité
    
    def _execute_trade(self, order1: Order, order2: Order, quantity: float, price: float):
        """Exécute un trade entre deux ordres"""
        buyer_order = order1 if order1.side == OrderSide.BUY else order2
        seller_order = order2 if order1.side == OrderSide.BUY else order1
        
        buyer = self.agents[buyer_order.agent_id]
        seller = self.agents[seller_order.agent_id]
        ticker = order1.ticker
        
        total_cost = quantity * price
        
        # Transferts
        buyer.balance -= total_cost
        seller.balance += total_cost
        
        buyer.portfolio[ticker] = buyer.portfolio.get(ticker, 0) + quantity
        seller.portfolio[ticker] = seller.portfolio.get(ticker, 0) - quantity
        
        if seller.portfolio[ticker] <= 0:
            del seller.portfolio[ticker]
        
        # Mise à jour des ordres
        buyer_order.filled_quantity += quantity
        seller_order.filled_quantity += quantity
        buyer_order.filled_price = price
        seller_order.filled_price = price
        
        if buyer_order.filled_quantity >= buyer_order.quantity:
            buyer_order.status = OrderStatus.FILLED
            buyer_order.filled_at = datetime.utcnow()
        
        if seller_order.filled_quantity >= seller_order.quantity:
            seller_order.status = OrderStatus.FILLED
            seller_order.filled_at = datetime.utcnow()
        
        # Stats
        buyer.total_trades += 1
        seller.total_trades += 1
        
        # Enregistrer le trade
        trade = Trade(
            ticker=ticker,
            buyer_id=buyer.id,
            seller_id=seller.id,
            quantity=quantity,
            price=price,
            buyer_order_id=buyer_order.id,
            seller_order_id=seller_order.id
        )
        self.trades.append(trade)
        
        # Mise à jour du prix de la company
        company = self.companies[ticker]
        company.share_price = price
        company.market_cap = company.total_shares * price
        
        # Historique
        self.price_history[ticker].append((datetime.utcnow(), price))
    
    # === MARKET DATA ===
    
    def get_market_data(self, ticker: str) -> Optional[MarketData]:
        """Obtient les données de marché pour un ticker"""
        ticker = ticker.upper()
        company = self.companies.get(ticker)
        if not company:
            return None
        
        book = self.order_books.get(ticker)
        bid = book.best_bid() if book else None
        ask = book.best_ask() if book else None
        
        # Stats 24h
        now = datetime.utcnow()
        day_ago = now - timedelta(hours=24)
        
        recent_history = [
            (t, p) for t, p in self.price_history.get(ticker, [])
            if t > day_ago
        ]
        
        if recent_history:
            prices = [p for _, p in recent_history]
            high_24h = max(prices)
            low_24h = min(prices)
            first_price = recent_history[0][1]
            change_24h = ((company.share_price - first_price) / first_price) * 100
        else:
            high_24h = low_24h = company.share_price
            change_24h = 0.0
        
        # Volume 24h
        recent_trades = [t for t in self.trades if t.ticker == ticker and t.timestamp > day_ago]
        volume_24h = sum(t.quantity * t.price for t in recent_trades)
        
        return MarketData(
            ticker=ticker,
            last_price=company.share_price,
            bid=bid.price if bid else 0,
            ask=ask.price if ask else 0,
            volume_24h=volume_24h,
            high_24h=high_24h,
            low_24h=low_24h,
            change_24h=change_24h,
            market_cap=company.market_cap
        )
    
    def get_all_tickers(self) -> list[str]:
        """Liste tous les tickers disponibles"""
        return list(self.companies.keys())
    
    def get_leaderboard(self, limit: int = 10) -> list[tuple[Agent, float]]:
        """Classement des agents par net worth"""
        prices = {t: c.share_price for t, c in self.companies.items()}
        
        rankings = [
            (agent, agent.net_worth(prices))
            for agent in self.agents.values()
        ]
        
        return sorted(rankings, key=lambda x: x[1], reverse=True)[:limit]

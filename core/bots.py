"""Bots traders autonomes qui tournent H24"""
import asyncio
import random
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .world import AIVerse

BOT_PROFILES = [
    {"id": "bot_alpha", "name": "AlphaTrader 🤖", "strategy": "momentum", "aggression": 0.8},
    {"id": "bot_beta", "name": "BetaBot 🧠", "strategy": "value", "aggression": 0.5},
    {"id": "bot_gamma", "name": "GammaGenius 💡", "strategy": "random", "aggression": 0.6},
    {"id": "bot_delta", "name": "DeltaDealer 📊", "strategy": "contrarian", "aggression": 0.7},
    {"id": "bot_theta", "name": "ThetaThink 🎯", "strategy": "momentum", "aggression": 0.4},
    {"id": "bot_omega", "name": "OmegaOracle 🔮", "strategy": "value", "aggression": 0.9},
    {"id": "bot_sigma", "name": "SigmaSage 📈", "strategy": "random", "aggression": 0.5},
]


class AutoTrader:
    """Bot trader autonome"""
    
    def __init__(self, world: 'AIVerse', profile: dict):
        self.world = world
        self.id = profile["id"]
        self.name = profile["name"]
        self.strategy = profile["strategy"]
        self.aggression = profile["aggression"]  # 0-1, how often it trades
        self.last_prices = {}
        
    def join(self):
        """Rejoindre le monde"""
        return self.world.join(self.id, self.name)
    
    def get_agent(self):
        return self.world.exchange.get_agent(self.id)
    
    def tick(self):
        """Exécute un tick de trading"""
        # Random chance based on aggression
        if random.random() > self.aggression:
            return
        
        agent = self.get_agent()
        if not agent:
            return
            
        companies = list(self.world.exchange.companies.values())
        if not companies:
            return
        
        # Pick strategy
        if self.strategy == "momentum":
            self._momentum_trade(agent, companies)
        elif self.strategy == "value":
            self._value_trade(agent, companies)
        elif self.strategy == "contrarian":
            self._contrarian_trade(agent, companies)
        else:
            self._random_trade(agent, companies)
        
        # Sometimes use services (generates revenue)
        if random.random() < 0.3:
            company = random.choice(companies)
            self.world.use_service(self.id, company.ticker)
    
    def _momentum_trade(self, agent, companies):
        """Buy assets that are going up, sell those going down"""
        for company in companies:
            ticker = company.ticker
            current_price = company.share_price
            last_price = self.last_prices.get(ticker, current_price)
            
            change = (current_price - last_price) / last_price if last_price > 0 else 0
            self.last_prices[ticker] = current_price
            
            if change > 0.02 and agent.balance > current_price * 5:
                # Going up - buy
                qty = random.randint(1, 5)
                self._submit_order(ticker, "buy", qty, current_price * 1.01)
            elif change < -0.02 and agent.portfolio.get(ticker, 0) > 0:
                # Going down - sell
                qty = min(random.randint(1, 3), agent.portfolio.get(ticker, 0))
                self._submit_order(ticker, "sell", qty, current_price * 0.99)
    
    def _value_trade(self, agent, companies):
        """Buy undervalued assets (high usage, low price)"""
        for company in companies:
            ticker = company.ticker
            price = company.share_price
            usage = company.total_api_calls + 1
            
            # Value score: lower is better (cheap relative to usage)
            value_score = price / usage
            
            if value_score < 1.0 and agent.balance > price * 10:
                qty = random.randint(5, 15)
                self._submit_order(ticker, "buy", qty, price * 1.02)
            elif value_score > 5.0 and agent.portfolio.get(ticker, 0) > 0:
                qty = min(random.randint(1, 5), agent.portfolio.get(ticker, 0))
                self._submit_order(ticker, "sell", qty, price * 0.98)
    
    def _contrarian_trade(self, agent, companies):
        """Do the opposite of momentum"""
        for company in companies:
            ticker = company.ticker
            current_price = company.share_price
            last_price = self.last_prices.get(ticker, current_price)
            
            change = (current_price - last_price) / last_price if last_price > 0 else 0
            self.last_prices[ticker] = current_price
            
            # Buy when going down (contrarian)
            if change < -0.02 and agent.balance > current_price * 5:
                qty = random.randint(2, 8)
                self._submit_order(ticker, "buy", qty, current_price * 1.01)
            # Sell when going up
            elif change > 0.02 and agent.portfolio.get(ticker, 0) > 0:
                qty = min(random.randint(1, 4), agent.portfolio.get(ticker, 0))
                self._submit_order(ticker, "sell", qty, current_price * 0.99)
    
    def _random_trade(self, agent, companies):
        """Random trading (baseline)"""
        company = random.choice(companies)
        ticker = company.ticker
        price = company.share_price
        
        action = random.choice(["buy", "sell", "hold", "hold"])
        
        if action == "buy" and agent.balance > price * 5:
            qty = random.randint(1, 10)
            self._submit_order(ticker, "buy", qty, price * random.uniform(0.98, 1.02))
        elif action == "sell" and agent.portfolio.get(ticker, 0) > 0:
            qty = min(random.randint(1, 5), agent.portfolio.get(ticker, 0))
            self._submit_order(ticker, "sell", qty, price * random.uniform(0.98, 1.02))
    
    def _submit_order(self, ticker: str, side: str, qty: int, price: float):
        """Submit an order"""
        from .types import Order, OrderSide, OrderType
        
        order = Order(
            agent_id=self.id,
            ticker=ticker,
            side=OrderSide(side),
            order_type=OrderType.LIMIT,
            quantity=qty,
            price=round(price, 2)
        )
        
        result = self.world.exchange.submit_order(order)
        if result and result.filled_quantity > 0:
            emoji = "📈" if side == "buy" else "📉"
            print(f"{emoji} {self.name} {side.upper()} {qty}x ${ticker} @ {price:.2f}₳")


class BotManager:
    """Gère tous les bots"""
    
    def __init__(self, world: 'AIVerse'):
        self.world = world
        self.bots: list[AutoTrader] = []
        self.running = False
        self._task = None
    
    def initialize(self):
        """Crée et enregistre tous les bots"""
        for profile in BOT_PROFILES:
            bot = AutoTrader(self.world, profile)
            bot.join()
            self.bots.append(bot)
            print(f"🤖 {bot.name} joined AIVERSE")
    
    async def run(self, interval: float = 10.0):
        """Boucle principale des bots"""
        self.running = True
        print(f"🚀 Bot manager started - {len(self.bots)} bots trading every {interval}s")
        
        while self.running:
            try:
                for bot in self.bots:
                    bot.tick()
                
                # Distribute daily income occasionally (simulated)
                if random.random() < 0.01:  # ~1% chance per tick
                    self.world.exchange.daily_income()
                    print("💰 Daily income distributed to all agents")
                    
            except Exception as e:
                print(f"❌ Bot error: {e}")
            
            await asyncio.sleep(interval)
    
    def start(self, interval: float = 10.0):
        """Démarre les bots en background"""
        self._task = asyncio.create_task(self.run(interval))
    
    def stop(self):
        """Arrête les bots"""
        self.running = False
        if self._task:
            self._task.cancel()

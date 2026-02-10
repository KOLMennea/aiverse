"""Agent Trader automatique pour AIVERSE"""
import httpx
import asyncio
import random
from datetime import datetime
from typing import Optional
import json


class TraderBot:
    """Un bot trader basique qui trade dans AIVERSE"""
    
    def __init__(
        self, 
        agent_id: str, 
        name: str, 
        api_url: str = "http://localhost:8080",
        strategy: str = "random"  # random, momentum, value
    ):
        self.agent_id = agent_id
        self.name = name
        self.api_url = api_url
        self.strategy = strategy
        self.running = False
        
        # État local
        self.balance = 0
        self.portfolio = {}
        self.trade_history = []
    
    async def join(self):
        """Rejoindre AIVERSE"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/agents/join",
                json={"agent_id": self.agent_id, "name": self.name}
            )
            data = response.json()
            self.balance = data["balance"]
            self.portfolio = data["portfolio"]
            print(f"🤖 {self.name} a rejoint AIVERSE avec {self.balance}₳")
            return data
    
    async def get_state(self):
        """Récupère l'état actuel de l'agent"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/agents/{self.agent_id}")
            data = response.json()
            self.balance = data["balance"]
            self.portfolio = data["portfolio"]
            return data
    
    async def get_companies(self):
        """Liste les entreprises disponibles"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/companies")
            return response.json()
    
    async def get_market_data(self, ticker: str):
        """Données de marché pour un ticker"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/market/{ticker}")
            if response.status_code == 200:
                return response.json()
            return None
    
    async def submit_order(self, ticker: str, side: str, quantity: float, price: Optional[float] = None):
        """Soumet un ordre"""
        order = {
            "agent_id": self.agent_id,
            "ticker": ticker,
            "side": side,
            "order_type": "limit" if price else "market",
            "quantity": quantity,
            "price": price
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.api_url}/orders", json=order)
            if response.status_code == 200:
                result = response.json()
                self.trade_history.append({
                    "time": datetime.utcnow().isoformat(),
                    "ticker": ticker,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "result": result
                })
                return result
            return None
    
    async def use_service(self, ticker: str):
        """Utilise le service d'une entreprise"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/companies/{ticker}/use",
                json={"agent_id": self.agent_id, "ticker": ticker}
            )
            return response.status_code == 200
    
    # === STRATEGIES ===
    
    async def random_strategy(self):
        """Stratégie aléatoire: achète/vend au hasard"""
        companies = await self.get_companies()
        if not companies:
            return
        
        company = random.choice(companies)
        ticker = company["ticker"]
        market = await self.get_market_data(ticker)
        
        if not market or market["last_price"] == 0:
            return
        
        # Décider achat ou vente
        action = random.choice(["buy", "sell", "hold", "hold"])  # 50% hold
        
        if action == "buy" and self.balance > market["last_price"] * 10:
            # Acheter 1-10 actions
            qty = random.randint(1, 10)
            price = market["last_price"] * random.uniform(0.98, 1.02)  # ±2%
            result = await self.submit_order(ticker, "buy", qty, price)
            if result:
                print(f"📈 {self.name} BUY {qty}x ${ticker} @ {price:.2f}₳")
        
        elif action == "sell" and ticker in self.portfolio:
            holdings = self.portfolio[ticker]
            qty = min(random.randint(1, 5), holdings)
            price = market["last_price"] * random.uniform(0.98, 1.02)
            result = await self.submit_order(ticker, "sell", qty, price)
            if result:
                print(f"📉 {self.name} SELL {qty}x ${ticker} @ {price:.2f}₳")
    
    async def momentum_strategy(self):
        """Stratégie momentum: suit la tendance"""
        companies = await self.get_companies()
        
        for company in companies:
            ticker = company["ticker"]
            market = await self.get_market_data(ticker)
            
            if not market:
                continue
            
            change = market.get("change_24h", 0)
            
            # Si hausse > 5%, acheter
            if change > 5 and self.balance > market["last_price"] * 5:
                qty = min(5, int(self.balance / market["last_price"] / 10))
                if qty > 0:
                    result = await self.submit_order(
                        ticker, "buy", qty, market["last_price"] * 1.01
                    )
                    if result:
                        print(f"🚀 {self.name} MOMENTUM BUY {qty}x ${ticker} (change: +{change:.1f}%)")
            
            # Si baisse > 5%, vendre
            elif change < -5 and ticker in self.portfolio:
                qty = min(3, self.portfolio[ticker])
                result = await self.submit_order(
                    ticker, "sell", qty, market["last_price"] * 0.99
                )
                if result:
                    print(f"💨 {self.name} MOMENTUM SELL {qty}x ${ticker} (change: {change:.1f}%)")
    
    async def value_strategy(self):
        """Stratégie value: achète les sous-évaluées"""
        companies = await self.get_companies()
        
        for company in companies:
            ticker = company["ticker"]
            market = await self.get_market_data(ticker)
            
            if not market:
                continue
            
            # Ratio simple: prix / utilisation
            usage = company.get("total_api_calls", 1)
            price = market["last_price"]
            
            value_ratio = price / (usage + 1)
            
            # Si ratio bas (beaucoup d'usage, prix bas) = sous-évalué
            if value_ratio < 0.1 and self.balance > price * 10:
                qty = min(10, int(self.balance / price / 5))
                if qty > 0:
                    result = await self.submit_order(ticker, "buy", qty, price * 1.01)
                    if result:
                        print(f"💎 {self.name} VALUE BUY {qty}x ${ticker} (ratio: {value_ratio:.3f})")
    
    # === MAIN LOOP ===
    
    async def run(self, interval: float = 5.0):
        """Boucle principale du bot"""
        await self.join()
        self.running = True
        
        strategy_fn = {
            "random": self.random_strategy,
            "momentum": self.momentum_strategy,
            "value": self.value_strategy
        }.get(self.strategy, self.random_strategy)
        
        print(f"🤖 {self.name} démarre avec stratégie: {self.strategy}")
        
        while self.running:
            try:
                await self.get_state()
                await strategy_fn()
                
                # Utiliser des services aléatoirement (génère de la revenue)
                if random.random() < 0.3:  # 30% chance
                    companies = await self.get_companies()
                    if companies:
                        company = random.choice(companies)
                        if await self.use_service(company["ticker"]):
                            print(f"⚡ {self.name} utilise ${company['ticker']}")
                
            except Exception as e:
                print(f"❌ {self.name} erreur: {e}")
            
            await asyncio.sleep(interval)
    
    def stop(self):
        """Arrête le bot"""
        self.running = False
        print(f"🛑 {self.name} arrêté")


async def run_multiple_bots(num_bots: int = 5):
    """Lance plusieurs bots en parallèle"""
    
    BOT_NAMES = [
        "AlphaTrader", "BetaBot", "GammaGenius", "DeltaDealer",
        "ThetaThink", "OmegaOracle", "SigmaSage", "LambdaLogic",
        "KappaKing", "ZetaZen"
    ]
    
    STRATEGIES = ["random", "momentum", "value"]
    
    bots = []
    for i in range(min(num_bots, len(BOT_NAMES))):
        bot = TraderBot(
            agent_id=f"bot_{i}",
            name=BOT_NAMES[i],
            strategy=random.choice(STRATEGIES)
        )
        bots.append(bot)
    
    # Lancer tous les bots
    tasks = [bot.run(interval=random.uniform(3, 10)) for bot in bots]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        for bot in bots:
            bot.stop()


if __name__ == "__main__":
    print("🚀 Lancement des bots traders...")
    asyncio.run(run_multiple_bots(5))

"""
Market Simulator

Generates realistic synthetic Polymarket data for backtesting:
- Price paths with mean-reversion and jumps (event-driven markets)
- Synthetic trade flow with informed/noise trader mix
- Orderbook snapshots
- Market resolution outcomes

Calibrated to observed Polymarket market behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from ..data.models import Market, Trade, OrderBookSnapshot, Side, Outcome
from ..utils.logger import get_logger

logger = get_logger("backtest.simulator")


@dataclass
class SimulatedMarket:
    """A simulated market with full history."""

    market: Market
    price_history: list[float]
    volume_history: list[float]
    trades: list[Trade]
    orderbook_snapshots: list[OrderBookSnapshot]
    timestamps: list[datetime]
    resolution: float  # 1.0 = YES, 0.0 = NO
    resolution_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    true_probability: float = 0.5  # Hidden true prob for AI signal edge


class MarketSimulator:
    """Generates synthetic but realistic prediction market data."""

    def __init__(
        self,
        n_markets: int = 30,
        duration_days: int = 30,
        tick_interval_minutes: int = 60,
        seed: int = 42,
    ):
        self.n_markets = n_markets
        self.duration_days = duration_days
        self.tick_interval_minutes = tick_interval_minutes
        self.rng = np.random.RandomState(seed)

    def generate_markets(
        self,
        start_date: Optional[datetime] = None,
    ) -> list[SimulatedMarket]:
        """Generate a set of simulated markets with full histories."""
        start = start_date or datetime(2024, 6, 1, tzinfo=timezone.utc)
        markets = []

        categories = [
            "Politics", "Crypto", "Sports", "Tech", "Economics",
            "Entertainment", "Science", "World Events",
        ]

        questions = [
            "Will BTC exceed $100K by end of Q{q}?",
            "Will the Fed cut rates in {month}?",
            "Will {team} win the championship?",
            "Will {company} announce layoffs this quarter?",
            "Will inflation drop below 3% by {month}?",
            "Will {country} hold elections before {month}?",
            "Will ETH flip BTC market cap this year?",
            "Will AI regulation pass in {country}?",
            "Will oil prices exceed $90/barrel?",
            "Will unemployment rise above 4.5%?",
            "Will the S&P 500 reach new ATH in {month}?",
            "Will a major CEX face insolvency?",
            "Will SOL exceed $200?",
            "Will there be a government shutdown?",
            "Will a new COVID variant emerge?",
            "Will DOGE be added to a major ETF?",
            "Will the housing market crash?",
            "Will Apple release AR glasses?",
            "Will there be a major cyber attack?",
            "Will gold hit $3000/oz?",
            "Will TikTok be banned?",
            "Will a new stablecoin depeg?",
            "Will merger between {company} and {company2} close?",
            "Will student loan forgiveness pass?",
            "Will minimum wage increase federally?",
            "Will autonomous vehicles get federal approval?",
            "Will a major bank adopt Bitcoin reserves?",
            "Will streaming services raise prices again?",
            "Will there be a rail strike?",
            "Will commercial real estate see mass defaults?",
        ]

        for i in range(self.n_markets):
            question = questions[i % len(questions)].format(
                q=self.rng.randint(1, 5),
                month=self.rng.choice(["Jan", "Mar", "Jun", "Sep", "Dec"]),
                team=self.rng.choice(["Lakers", "Chiefs", "Yankees", "Arsenal"]),
                company=self.rng.choice(["Meta", "Google", "Amazon", "Tesla"]),
                company2=self.rng.choice(["Nvidia", "Microsoft", "Apple"]),
                country=self.rng.choice(["US", "UK", "France", "Brazil"]),
            )

            # Random initial probability
            initial_prob = self.rng.beta(2, 2)  # Centered around 0.5
            initial_prob = np.clip(initial_prob, 0.1, 0.9)

            # Market duration (subset of total duration)
            market_days = self.rng.randint(7, self.duration_days + 1)
            market_start = start + timedelta(days=self.rng.randint(0, max(1, self.duration_days - market_days)))
            market_end = market_start + timedelta(days=market_days)

            # Generate price path
            sim = self._simulate_price_path(
                initial_prob=initial_prob,
                n_ticks=market_days * (24 * 60 // self.tick_interval_minutes),
                market_id=f"market_{i:03d}",
            )

            # Resolution based on true probability
            true_prob = sim["true_prob"]
            resolution = 1.0 if self.rng.random() < true_prob else 0.0

            # Build timestamps
            timestamps = [
                market_start + timedelta(minutes=j * self.tick_interval_minutes)
                for j in range(len(sim["prices"]))
            ]

            # Build Market object
            market = Market(
                condition_id=f"market_{i:03d}",
                question=question,
                slug=f"market-{i:03d}",
                outcomes=["Yes", "No"],
                outcome_prices=[initial_prob, 1.0 - initial_prob],
                volume=float(self.rng.uniform(50000, 5000000)),
                liquidity=float(self.rng.uniform(10000, 500000)),
                end_date=market_end,
                active=True,
                category=categories[i % len(categories)],
            )

            # Generate synthetic trades
            trades = self._generate_trades(
                market_id=market.condition_id,
                prices=sim["prices"],
                volumes=sim["volumes"],
                timestamps=timestamps,
            )

            # Generate orderbook snapshots
            orderbooks = self._generate_orderbooks(
                market_id=market.condition_id,
                prices=sim["prices"],
                timestamps=timestamps,
            )

            markets.append(SimulatedMarket(
                market=market,
                price_history=sim["prices"],
                volume_history=sim["volumes"],
                trades=trades,
                orderbook_snapshots=orderbooks,
                timestamps=timestamps,
                resolution=resolution,
                resolution_time=market_end,
                true_probability=true_prob,
            ))

        logger.info(f"Generated {len(markets)} simulated markets")
        return markets

    def _simulate_price_path(
        self,
        initial_prob: float,
        n_ticks: int,
        market_id: str,
    ) -> dict:
        """
        Simulate a prediction market price path.

        Uses a model combining:
        - Random walk with mean-reversion toward resolution
        - Occasional jumps (news events)
        - Volume correlated with price movement
        """
        prices = [initial_prob]
        volumes = [self.rng.uniform(100, 1000)]

        # Market parameters — calibrated to real Polymarket behavior
        # Real markets have stronger mean-reversion and momentum regimes
        volatility = self.rng.uniform(0.003, 0.015)
        jump_prob = self.rng.uniform(0.02, 0.06)
        jump_size = self.rng.uniform(0.04, 0.12)
        mean_rev_speed = self.rng.uniform(0.005, 0.025)  # Stronger convergence

        # Hidden "true" probability that the market converges toward
        true_prob = self.rng.beta(2, 2)
        
        # Momentum regime: markets often trend before reverting
        momentum_factor = self.rng.uniform(0.1, 0.4)  # Price stickiness

        for t in range(1, n_ticks):
            prev = prices[-1]

            # Time decay: as market nears end, converge to truth faster
            time_frac = t / n_ticks
            decay_factor = 1.0 + 3.0 * time_frac ** 2

            # Mean reversion toward true probability
            mean_rev = mean_rev_speed * decay_factor * (true_prob - prev)
            
            # Momentum: recent direction continues (trending markets)
            momentum = 0.0
            if len(prices) >= 3:
                recent_dir = prices[-1] - prices[-3]
                momentum = momentum_factor * recent_dir * (1.0 - time_frac)

            # Random walk
            noise = self.rng.normal(0, volatility)

            # Occasional jumps (news events — tend toward true prob)
            if self.rng.random() < jump_prob:
                jump_dir = np.sign(true_prob - prev) if self.rng.random() < 0.65 else -np.sign(true_prob - prev)
                jump = jump_dir * jump_size * self.rng.uniform(0.5, 1.5)
            else:
                jump = 0.0

            # New price
            new_price = prev + mean_rev + momentum + noise + jump
            new_price = float(np.clip(new_price, 0.01, 0.99))
            prices.append(new_price)

            # Volume: higher on bigger moves
            base_vol = self.rng.uniform(50, 500)
            move_vol = abs(new_price - prev) * 10000
            vol = base_vol + move_vol
            volumes.append(float(vol))

        return {"prices": prices, "volumes": volumes, "true_prob": float(true_prob)}

    def _generate_trades(
        self,
        market_id: str,
        prices: list[float],
        volumes: list[float],
        timestamps: list[datetime],
    ) -> list[Trade]:
        """Generate synthetic trades from price/volume data."""
        trades = []
        n_wallets = 50
        wallets = [f"0x{self.rng.bytes(20).hex()}" for _ in range(n_wallets)]

        for i in range(1, len(prices)):
            price = prices[i]
            prev_price = prices[i - 1]
            vol = volumes[i]
            ts = timestamps[i]

            # Number of trades this tick
            n_trades = max(1, int(vol / 100))

            for _ in range(n_trades):
                # Direction based on price movement + noise
                move = price - prev_price
                buy_prob = 0.5 + np.clip(move * 10, -0.3, 0.3)
                is_buy = self.rng.random() < buy_prob

                trade_size = self.rng.exponential(vol / n_trades)
                trade_price = price + self.rng.normal(0, 0.005)
                trade_price = float(np.clip(trade_price, 0.01, 0.99))

                trades.append(Trade(
                    market_id=market_id,
                    timestamp=ts + timedelta(seconds=self.rng.randint(0, self.tick_interval_minutes * 60)),
                    side=Side.BUY if is_buy else Side.SELL,
                    outcome=Outcome.YES,
                    price=trade_price,
                    size=round(trade_size, 2),
                    maker=self.rng.choice(wallets),
                    taker=self.rng.choice(wallets),
                ))

        trades.sort(key=lambda t: t.timestamp)
        return trades

    def _generate_orderbooks(
        self,
        market_id: str,
        prices: list[float],
        timestamps: list[datetime],
    ) -> list[OrderBookSnapshot]:
        """Generate synthetic orderbook snapshots."""
        snapshots = []

        for i, (price, ts) in enumerate(zip(prices, timestamps)):
            n_levels = self.rng.randint(3, 8)
            spread = self.rng.uniform(0.005, 0.03)

            bids = []
            asks = []

            for j in range(n_levels):
                bid_price = price - spread / 2 - j * self.rng.uniform(0.005, 0.015)
                ask_price = price + spread / 2 + j * self.rng.uniform(0.005, 0.015)
                bid_size = self.rng.exponential(200) * (n_levels - j) / n_levels
                ask_size = self.rng.exponential(200) * (n_levels - j) / n_levels

                if 0 < bid_price < 1:
                    bids.append((round(bid_price, 4), round(bid_size, 2)))
                if 0 < ask_price < 1:
                    asks.append((round(ask_price, 4), round(ask_size, 2)))

            snapshots.append(OrderBookSnapshot(
                market_id=market_id,
                timestamp=ts,
                bids=sorted(bids, key=lambda x: x[0], reverse=True),
                asks=sorted(asks, key=lambda x: x[0]),
            ))

        return snapshots

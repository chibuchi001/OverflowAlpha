"""Core data models for orderflow-alpha."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Outcome(Enum):
    YES = "Yes"
    NO = "No"


@dataclass
class Market:
    """A Polymarket prediction market."""

    condition_id: str
    question: str
    slug: str
    outcomes: list[str]
    outcome_prices: list[float]
    volume: float
    liquidity: float
    end_date: Optional[datetime] = None
    active: bool = True
    category: str = ""
    tokens: list[dict] = field(default_factory=list)

    @property
    def yes_price(self) -> float:
        if self.outcome_prices:
            return self.outcome_prices[0]
        return 0.5

    @property
    def no_price(self) -> float:
        if len(self.outcome_prices) > 1:
            return self.outcome_prices[1]
        return 1.0 - self.yes_price

    @property
    def implied_probability(self) -> float:
        return self.yes_price


@dataclass
class Trade:
    """A single trade on Polymarket."""

    market_id: str
    timestamp: datetime
    side: Side
    outcome: Outcome
    price: float
    size: float
    maker: str = ""
    taker: str = ""

    @property
    def notional(self) -> float:
        return self.price * self.size


@dataclass
class OrderBookSnapshot:
    """Point-in-time orderbook state."""

    market_id: str
    timestamp: datetime
    bids: list[tuple[float, float]]  # (price, size)
    asks: list[tuple[float, float]]
    outcome: Outcome = Outcome.YES

    @property
    def best_bid(self) -> float:
        return self.bids[0][0] if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0][0] if self.asks else 1.0

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid

    @property
    def bid_depth(self) -> float:
        return sum(size for _, size in self.bids)

    @property
    def ask_depth(self) -> float:
        return sum(size for _, size in self.asks)

    @property
    def depth_imbalance(self) -> float:
        total = self.bid_depth + self.ask_depth
        if total == 0:
            return 0.0
        return (self.bid_depth - self.ask_depth) / total


@dataclass
class Position:
    """A position in a market."""

    market_id: str
    outcome: Outcome
    size: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.size

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price


@dataclass
class Signal:
    """A trading signal from any signal generator."""

    market_id: str
    timestamp: datetime
    name: str
    value: float  # -1 to 1, where positive = buy YES
    confidence: float  # 0 to 1
    metadata: dict = field(default_factory=dict)

    @property
    def direction(self) -> str:
        return "YES" if self.value > 0 else "NO" if self.value < 0 else "NEUTRAL"


@dataclass
class TradeDecision:
    """A decision to enter or exit a trade."""

    market_id: str
    timestamp: datetime
    action: str  # "BUY_YES", "BUY_NO", "SELL_YES", "SELL_NO", "HOLD"
    size: float
    target_price: float
    edge: float
    signals: list[Signal] = field(default_factory=list)
    reason: str = ""

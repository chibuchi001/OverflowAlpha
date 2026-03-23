"""
Orderflow Signal Generator

Analyzes trade flow patterns on Polymarket to detect informed positioning:
- Trade flow imbalance (net buy vs sell pressure)
- Large order detection (whale tracking)
- Smart wallet clustering (repeat profitable wallets)
- Volume-weighted price impact
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from ..data.models import Trade, OrderBookSnapshot, Signal, Side, Outcome
from ..utils.logger import get_logger

logger = get_logger("signals.orderflow")


class OrderflowSignal:
    """Generates trading signals from orderflow analysis."""

    def __init__(
        self,
        lookback_minutes: int = 60,
        large_trade_threshold: float = 500.0,
        smoothing_window: int = 5,
        smart_wallet_min_trades: int = 5,
        smart_wallet_min_winrate: float = 0.55,
    ):
        self.lookback_minutes = lookback_minutes
        self.large_trade_threshold = large_trade_threshold
        self.smoothing_window = smoothing_window
        self.smart_wallet_min_trades = smart_wallet_min_trades
        self.smart_wallet_min_winrate = smart_wallet_min_winrate

        # Track wallet performance over time
        self._wallet_history: dict[str, list[Trade]] = defaultdict(list)
        self._smart_wallets: set[str] = set()

    def generate(
        self,
        market_id: str,
        trades: list[Trade],
        orderbook: Optional[OrderBookSnapshot] = None,
        now: Optional[datetime] = None,
    ) -> Signal:
        """
        Generate an orderflow signal for a market.

        Returns a Signal with value in [-1, 1]:
          Positive = net buying pressure (bullish on YES)
          Negative = net selling pressure (bearish on YES)
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.lookback_minutes)

        # Filter to lookback window
        recent = [t for t in trades if t.timestamp >= cutoff]

        if len(recent) < 3:
            return Signal(
                market_id=market_id,
                timestamp=now,
                name="orderflow",
                value=0.0,
                confidence=0.1,
                metadata={"reason": "insufficient_trades", "trade_count": len(recent)},
            )

        # ── Component 1: Trade Flow Imbalance ────────────────────────
        flow_imbalance = self._compute_flow_imbalance(recent)

        # ── Component 2: Large Order Signal ──────────────────────────
        whale_signal = self._compute_whale_signal(recent)

        # ── Component 3: Smart Wallet Signal ─────────────────────────
        smart_signal = self._compute_smart_wallet_signal(recent)

        # ── Component 4: Orderbook Imbalance ─────────────────────────
        book_signal = 0.0
        if orderbook:
            book_signal = orderbook.depth_imbalance

        # ── Combine ──────────────────────────────────────────────────
        # Weighted combination of sub-signals
        raw = (
            0.35 * flow_imbalance
            + 0.25 * whale_signal
            + 0.20 * smart_signal
            + 0.20 * book_signal
        )

        # Clamp to [-1, 1]
        value = float(np.clip(raw, -1.0, 1.0))

        # Confidence based on trade count and signal agreement
        signals = [flow_imbalance, whale_signal, smart_signal, book_signal]
        agreement = 1.0 - np.std([s for s in signals if s != 0.0]) if any(s != 0 for s in signals) else 0.0
        volume_confidence = min(len(recent) / 50.0, 1.0)
        confidence = float(np.clip(0.5 * volume_confidence + 0.5 * agreement, 0.1, 0.95))

        return Signal(
            market_id=market_id,
            timestamp=now,
            name="orderflow",
            value=value,
            confidence=confidence,
            metadata={
                "flow_imbalance": round(flow_imbalance, 4),
                "whale_signal": round(whale_signal, 4),
                "smart_wallet_signal": round(smart_signal, 4),
                "book_imbalance": round(book_signal, 4),
                "trade_count": len(recent),
                "total_volume": round(sum(t.notional for t in recent), 2),
            },
        )

    def _compute_flow_imbalance(self, trades: list[Trade]) -> float:
        """
        Net buy vs sell flow, volume-weighted.
        Positive = net buying (bullish YES), Negative = net selling.
        """
        buy_volume = 0.0
        sell_volume = 0.0

        for t in trades:
            notional = t.notional
            if t.side == Side.BUY and t.outcome == Outcome.YES:
                buy_volume += notional
            elif t.side == Side.SELL and t.outcome == Outcome.YES:
                sell_volume += notional
            elif t.side == Side.BUY and t.outcome == Outcome.NO:
                sell_volume += notional  # Buying NO = bearish YES
            elif t.side == Side.SELL and t.outcome == Outcome.NO:
                buy_volume += notional

        total = buy_volume + sell_volume
        if total == 0:
            return 0.0

        return (buy_volume - sell_volume) / total

    def _compute_whale_signal(self, trades: list[Trade]) -> float:
        """
        Signal from large trades (whale detection).
        Large trades from informed players tend to predict direction.
        """
        large_trades = [t for t in trades if t.notional >= self.large_trade_threshold]

        if not large_trades:
            return 0.0

        whale_buy = sum(
            t.notional for t in large_trades
            if (t.side == Side.BUY and t.outcome == Outcome.YES)
            or (t.side == Side.SELL and t.outcome == Outcome.NO)
        )
        whale_sell = sum(
            t.notional for t in large_trades
            if (t.side == Side.SELL and t.outcome == Outcome.YES)
            or (t.side == Side.BUY and t.outcome == Outcome.NO)
        )

        total = whale_buy + whale_sell
        if total == 0:
            return 0.0

        return (whale_buy - whale_sell) / total

    def _compute_smart_wallet_signal(self, trades: list[Trade]) -> float:
        """
        Track wallets with historically profitable trades.
        Weight their current activity more heavily.
        """
        # Update wallet histories
        for t in trades:
            addr = t.taker or t.maker
            if addr:
                self._wallet_history[addr].append(t)

        # For simplicity in backtesting, we compute directional bias
        # of wallets that have traded frequently
        active_wallets = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})

        for t in trades:
            addr = t.taker or t.maker
            if not addr:
                continue

            history = self._wallet_history.get(addr, [])
            if len(history) < self.smart_wallet_min_trades:
                continue

            notional = t.notional
            if (t.side == Side.BUY and t.outcome == Outcome.YES) or \
               (t.side == Side.SELL and t.outcome == Outcome.NO):
                active_wallets[addr]["buy"] += notional
            else:
                active_wallets[addr]["sell"] += notional

        if not active_wallets:
            return 0.0

        total_buy = sum(w["buy"] for w in active_wallets.values())
        total_sell = sum(w["sell"] for w in active_wallets.values())
        total = total_buy + total_sell

        if total == 0:
            return 0.0

        return (total_buy - total_sell) / total

    def update_smart_wallets(self, resolved_markets: dict[str, float]):
        """
        Update smart wallet tracking after markets resolve.
        resolved_markets: {market_id: final_price} where 1.0 = YES won, 0.0 = NO won
        """
        wallet_pnl: dict[str, list[float]] = defaultdict(list)

        for addr, trades in self._wallet_history.items():
            for t in trades:
                if t.market_id in resolved_markets:
                    final = resolved_markets[t.market_id]
                    if t.side == Side.BUY and t.outcome == Outcome.YES:
                        pnl = (final - t.price) * t.size
                    elif t.side == Side.SELL and t.outcome == Outcome.YES:
                        pnl = (t.price - final) * t.size
                    else:
                        pnl = 0.0
                    wallet_pnl[addr].append(pnl)

        self._smart_wallets = set()
        for addr, pnls in wallet_pnl.items():
            if len(pnls) >= self.smart_wallet_min_trades:
                win_rate = sum(1 for p in pnls if p > 0) / len(pnls)
                if win_rate >= self.smart_wallet_min_winrate:
                    self._smart_wallets.add(addr)

        logger.info(f"Identified {len(self._smart_wallets)} smart wallets")

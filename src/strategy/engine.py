"""
Strategy Engine

Core decision-making engine that:
1. Collects signals from all generators
2. Aggregates into composite signal
3. Converts to trade decision with Kelly sizing
4. Applies risk constraints
5. Outputs executable trade decisions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..data.models import Market, Signal, TradeDecision, Position, Outcome
from ..signals.aggregator import SignalAggregator
from .kelly import KellySizer
from .risk import RiskManager
from ..utils.logger import get_logger

logger = get_logger("strategy.engine")


class StrategyEngine:
    """Main strategy engine combining signals, sizing, and risk."""

    def __init__(
        self,
        aggregator: SignalAggregator,
        sizer: KellySizer,
        risk_manager: RiskManager,
        min_edge: float = 0.05,
    ):
        self.aggregator = aggregator
        self.sizer = sizer
        self.risk_manager = risk_manager
        self.min_edge = min_edge

    def decide(
        self,
        market: Market,
        signals: list[Signal],
        positions: dict[str, Position],
        bankroll: float,
        now: Optional[datetime] = None,
    ) -> TradeDecision:
        """
        Make a trading decision for a market.

        Flow:
        1. Aggregate signals
        2. Estimate true probability
        3. Compute edge vs market
        4. Size position with Kelly
        5. Check risk constraints
        6. Return decision
        """
        now = now or datetime.now(timezone.utc)

        # Step 1: Aggregate signals
        composite = self.aggregator.aggregate(signals, now=now)

        # Step 2: Convert signal to probability estimate
        # composite.value is in [-1, 1], map to probability adjustment
        # Positive value = YES is underpriced
        market_price = market.yes_price
        prob_adjustment = composite.value * 0.15  # Max ±15% adjustment
        estimated_prob = np.clip(market_price + prob_adjustment, 0.01, 0.99)

        # Step 3: Compute edge
        edge = float(estimated_prob - market_price)

        # Check minimum edge
        if abs(edge) < self.min_edge:
            return TradeDecision(
                market_id=market.condition_id,
                timestamp=now,
                action="HOLD",
                size=0.0,
                target_price=market_price,
                edge=edge,
                signals=signals,
                reason=f"edge_below_threshold_{abs(edge):.4f}<{self.min_edge}",
            )

        # Check existing position
        existing = positions.get(market.condition_id)
        if existing:
            return self._handle_existing_position(
                market, existing, edge, estimated_prob, composite, signals, bankroll, now
            )

        # Step 4: Size new position
        kelly = self.sizer.compute(
            estimated_prob=float(estimated_prob),
            market_price=market_price,
            confidence=composite.confidence,
            bankroll=bankroll,
        )

        if kelly.fraction <= 0:
            return TradeDecision(
                market_id=market.condition_id,
                timestamp=now,
                action="HOLD",
                size=0.0,
                target_price=market_price,
                edge=edge,
                signals=signals,
                reason="kelly_zero",
            )

        position_size = kelly.fraction * bankroll

        # Determine direction
        if edge > 0:
            action = "BUY_YES"
            target_price = market_price
        else:
            action = "BUY_NO"
            target_price = 1.0 - market_price

        decision = TradeDecision(
            market_id=market.condition_id,
            timestamp=now,
            action=action,
            size=position_size,
            target_price=target_price,
            edge=abs(edge),
            signals=signals,
            reason=f"signal={composite.value:.3f}_kelly={kelly.fraction:.4f}",
        )

        # Step 5: Risk check
        allowed, reason, adjusted_size = self.risk_manager.check_new_trade(
            decision, positions, bankroll, now
        )

        if not allowed:
            return TradeDecision(
                market_id=market.condition_id,
                timestamp=now,
                action="HOLD",
                size=0.0,
                target_price=market_price,
                edge=edge,
                signals=signals,
                reason=f"risk_blocked: {reason}",
            )

        decision.size = adjusted_size
        logger.info(
            f"TRADE: {action} {market.condition_id[:12]}... "
            f"size=${adjusted_size:.0f} edge={abs(edge):.3f} "
            f"conf={composite.confidence:.2f}"
        )

        return decision

    def _handle_existing_position(
        self,
        market: Market,
        position: Position,
        edge: float,
        estimated_prob: float,
        composite: Signal,
        signals: list[Signal],
        bankroll: float,
        now: datetime,
    ) -> TradeDecision:
        """Handle decision when we already have a position."""
        # Check if signal has flipped against us
        is_long_yes = position.outcome == Outcome.YES
        signal_says_yes = edge > 0

        if is_long_yes != signal_says_yes and abs(edge) > self.min_edge * 1.5:
            # Signal flipped — exit position
            action = "SELL_YES" if is_long_yes else "SELL_NO"
            return TradeDecision(
                market_id=market.condition_id,
                timestamp=now,
                action=action,
                size=position.size,
                target_price=market.yes_price if is_long_yes else market.no_price,
                edge=abs(edge),
                signals=signals,
                reason="signal_reversal",
            )

        # Otherwise hold
        return TradeDecision(
            market_id=market.condition_id,
            timestamp=now,
            action="HOLD",
            size=0.0,
            target_price=market.yes_price,
            edge=edge,
            signals=signals,
            reason="maintaining_position",
        )

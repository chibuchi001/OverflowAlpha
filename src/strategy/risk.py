"""
Risk Manager

Enforces portfolio-level risk constraints:
- Max position size per market
- Max total portfolio exposure
- Stop-loss monitoring
- Drawdown circuit breaker
- Cooldown after stops
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from ..data.models import Position, TradeDecision
from ..utils.logger import get_logger

logger = get_logger("strategy.risk")


@dataclass
class RiskState:
    """Current risk state of the portfolio."""

    total_exposure: float = 0.0
    max_drawdown_hit: bool = False
    current_drawdown: float = 0.0
    peak_equity: float = 0.0
    positions_at_limit: int = 0
    cooldown_until: Optional[datetime] = None
    halted: bool = False
    halt_reason: str = ""


class RiskManager:
    """Portfolio-level risk management."""

    def __init__(
        self,
        max_position_pct: float = 0.15,
        max_portfolio_exposure: float = 0.60,
        stop_loss_pct: float = 0.25,
        max_drawdown_pct: float = 0.20,
        max_correlated_exposure: float = 0.30,
        cooldown_seconds: int = 1800,
    ):
        self.max_position_pct = max_position_pct
        self.max_portfolio_exposure = max_portfolio_exposure
        self.stop_loss_pct = stop_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_correlated_exposure = max_correlated_exposure
        self.cooldown_seconds = cooldown_seconds

        self._peak_equity: float = 0.0
        self._cooldown_until: Optional[datetime] = None
        self._stopped_markets: set[str] = set()
        self._halted: bool = False

    def check_new_trade(
        self,
        decision: TradeDecision,
        positions: dict[str, Position],
        bankroll: float,
        now: Optional[datetime] = None,
    ) -> tuple[bool, str, float]:
        """
        Check if a new trade passes risk constraints.

        Returns (allowed, reason, adjusted_size)
        """
        now = now or datetime.now(timezone.utc)

        # Check halt
        if self._halted:
            return False, "trading_halted_drawdown", 0.0

        # Check cooldown
        if self._cooldown_until and now < self._cooldown_until:
            remaining = (self._cooldown_until - now).total_seconds()
            return False, f"cooldown_active_{int(remaining)}s", 0.0

        # Check if market was stopped out
        if decision.market_id in self._stopped_markets:
            return False, "market_stopped_out", 0.0

        # Check max position size
        max_size = bankroll * self.max_position_pct
        adjusted_size = min(decision.size, max_size)

        # Check total portfolio exposure
        current_exposure = sum(
            pos.size * pos.entry_price for pos in positions.values()
        )
        max_total = bankroll * self.max_portfolio_exposure
        remaining_capacity = max_total - current_exposure

        if remaining_capacity <= 0:
            return False, "max_exposure_reached", 0.0

        adjusted_size = min(adjusted_size, remaining_capacity)

        if adjusted_size < 1.0:  # Min trade size
            return False, "size_too_small", 0.0

        return True, "approved", adjusted_size

    def check_stop_losses(
        self,
        positions: dict[str, Position],
        bankroll: float,
        now: Optional[datetime] = None,
    ) -> list[TradeDecision]:
        """
        Check all positions for stop-loss triggers.
        Returns list of exit decisions.
        """
        now = now or datetime.now(timezone.utc)
        exits = []

        for market_id, pos in positions.items():
            pnl_pct = pos.unrealized_pnl_pct

            if pnl_pct <= -self.stop_loss_pct:
                action = "SELL_YES" if pos.outcome.value == "Yes" else "SELL_NO"
                exits.append(TradeDecision(
                    market_id=market_id,
                    timestamp=now,
                    action=action,
                    size=pos.size,
                    target_price=pos.current_price,
                    edge=0.0,
                    reason=f"stop_loss_triggered_pnl={pnl_pct:.2%}",
                ))
                self._stopped_markets.add(market_id)
                self._cooldown_until = now + timedelta(seconds=self.cooldown_seconds)
                logger.warning(
                    f"STOP LOSS: {market_id} at {pnl_pct:.2%} loss. "
                    f"Cooldown until {self._cooldown_until}"
                )

        return exits

    def update_equity(self, equity: float, now: Optional[datetime] = None):
        """Update equity tracking for drawdown monitoring."""
        now = now or datetime.now(timezone.utc)

        if equity > self._peak_equity:
            self._peak_equity = equity

        if self._peak_equity > 0:
            drawdown = (self._peak_equity - equity) / self._peak_equity

            if drawdown >= self.max_drawdown_pct:
                self._halted = True
                logger.critical(
                    f"CIRCUIT BREAKER: Drawdown {drawdown:.2%} exceeds "
                    f"max {self.max_drawdown_pct:.2%}. Trading halted."
                )

    def get_state(
        self,
        positions: dict[str, Position],
        bankroll: float,
    ) -> RiskState:
        """Get current risk state summary."""
        exposure = sum(pos.size * pos.entry_price for pos in positions.values())
        drawdown = 0.0
        if self._peak_equity > 0:
            drawdown = (self._peak_equity - bankroll) / self._peak_equity

        return RiskState(
            total_exposure=round(exposure, 2),
            max_drawdown_hit=self._halted,
            current_drawdown=round(max(drawdown, 0.0), 4),
            peak_equity=round(self._peak_equity, 2),
            positions_at_limit=sum(
                1 for p in positions.values()
                if p.size * p.entry_price >= bankroll * self.max_position_pct * 0.9
            ),
            cooldown_until=self._cooldown_until,
            halted=self._halted,
            halt_reason="max_drawdown_exceeded" if self._halted else "",
        )

    def reset(self):
        """Reset risk state (for new backtest run)."""
        self._peak_equity = 0.0
        self._cooldown_until = None
        self._stopped_markets.clear()
        self._halted = False

"""
Kelly Criterion Position Sizer

Implements fractional Kelly criterion for optimal bet sizing
in prediction market trading. Handles binary outcomes and
adjusts for estimation uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..utils.logger import get_logger

logger = get_logger("strategy.kelly")


@dataclass
class KellyResult:
    """Result of Kelly criterion calculation."""

    fraction: float          # Recommended fraction of bankroll
    edge: float              # Estimated edge
    odds: float              # Decimal odds
    ev_per_unit: float       # Expected value per unit bet
    confidence_adj: float    # Confidence adjustment factor


class KellySizer:
    """
    Fractional Kelly criterion for prediction market bet sizing.

    Uses half-Kelly by default to reduce variance while capturing
    most of the long-term growth rate advantage.
    """

    def __init__(
        self,
        kelly_fraction: float = 0.5,
        max_position_pct: float = 0.15,
        min_edge: float = 0.05,
    ):
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.min_edge = min_edge

    def compute(
        self,
        estimated_prob: float,
        market_price: float,
        confidence: float = 1.0,
        bankroll: float = 10000.0,
    ) -> KellyResult:
        """
        Compute Kelly-optimal position size.

        Parameters
        ----------
        estimated_prob : float
            Our estimated true probability (0 to 1)
        market_price : float
            Current market price for YES outcome (0 to 1)
        confidence : float
            Signal confidence (0 to 1), scales down Kelly fraction
        bankroll : float
            Current bankroll

        Returns
        -------
        KellyResult with recommended position size
        """
        # Clamp inputs
        estimated_prob = np.clip(estimated_prob, 0.01, 0.99)
        market_price = np.clip(market_price, 0.01, 0.99)

        # Edge: our probability vs market probability
        edge = estimated_prob - market_price

        # If edge is below threshold, don't trade
        if abs(edge) < self.min_edge:
            return KellyResult(
                fraction=0.0,
                edge=edge,
                odds=0.0,
                ev_per_unit=0.0,
                confidence_adj=confidence,
            )

        if edge > 0:
            # Buy YES: pay market_price, win (1 - market_price) if YES resolves
            b = (1.0 - market_price) / market_price  # decimal odds minus 1
            p = estimated_prob
            q = 1.0 - p

            # Kelly: f* = (bp - q) / b
            if b > 0:
                full_kelly = (b * p - q) / b
            else:
                full_kelly = 0.0
        else:
            # Buy NO: pay (1 - market_price), win market_price if NO resolves
            b = market_price / (1.0 - market_price)
            p = 1.0 - estimated_prob  # prob of NO
            q = estimated_prob

            if b > 0:
                full_kelly = (b * p - q) / b
            else:
                full_kelly = 0.0

        # Apply fractional Kelly and confidence adjustment
        confidence_adj = max(confidence, 0.1)
        adjusted = full_kelly * self.kelly_fraction * confidence_adj

        # Cap at max position size
        fraction = float(np.clip(adjusted, 0.0, self.max_position_pct))

        # Expected value per unit bet
        if edge > 0:
            ev = estimated_prob * (1.0 - market_price) - (1.0 - estimated_prob) * market_price
        else:
            ev = (1.0 - estimated_prob) * market_price - estimated_prob * (1.0 - market_price)

        return KellyResult(
            fraction=round(fraction, 6),
            edge=round(edge, 6),
            odds=round(b, 4) if b > 0 else 0.0,
            ev_per_unit=round(ev, 6),
            confidence_adj=round(confidence_adj, 4),
        )

    def size_position(
        self,
        estimated_prob: float,
        market_price: float,
        confidence: float,
        bankroll: float,
    ) -> float:
        """Convenience: returns dollar amount to bet."""
        result = self.compute(estimated_prob, market_price, confidence, bankroll)
        return round(result.fraction * bankroll, 2)

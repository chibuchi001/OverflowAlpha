"""
Momentum Signal Generator

Detects directional momentum in market odds using:
- Price velocity (rate of change)
- Price acceleration (change of velocity)
- Volume-confirmed moves
- Breakout detection from trading ranges
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..data.models import Market, Trade, Signal
from ..utils.logger import get_logger

logger = get_logger("signals.momentum")


class MomentumSignal:
    """Generates signals from price momentum patterns."""

    def __init__(
        self,
        velocity_window: int = 10,
        acceleration_window: int = 5,
        breakout_lookback: int = 20,
        volume_confirm_threshold: float = 1.5,
    ):
        self.velocity_window = velocity_window
        self.acceleration_window = acceleration_window
        self.breakout_lookback = breakout_lookback
        self.volume_confirm_threshold = volume_confirm_threshold

    def generate(
        self,
        market_id: str,
        price_history: list[float],
        volume_history: Optional[list[float]] = None,
        now: Optional[datetime] = None,
    ) -> Signal:
        """
        Generate a momentum signal from price history.

        price_history: list of prices (oldest first)
        volume_history: optional matching volume series

        Returns Signal with value in [-1, 1]:
          Positive = upward momentum (bullish YES)
          Negative = downward momentum (bearish YES)
        """
        now = now or datetime.now(timezone.utc)

        if len(price_history) < self.velocity_window + 2:
            return Signal(
                market_id=market_id,
                timestamp=now,
                name="momentum",
                value=0.0,
                confidence=0.1,
                metadata={"reason": "insufficient_data"},
            )

        prices = np.array(price_history, dtype=float)

        # ── Component 1: Price Velocity ──────────────────────────────
        velocity = self._compute_velocity(prices)

        # ── Component 2: Price Acceleration ──────────────────────────
        acceleration = self._compute_acceleration(prices)

        # ── Component 3: Breakout Score ──────────────────────────────
        breakout = self._compute_breakout(prices)

        # ── Component 4: Volume Confirmation ─────────────────────────
        volume_mult = 1.0
        if volume_history and len(volume_history) >= self.velocity_window:
            volume_mult = self._volume_confirmation(
                np.array(volume_history, dtype=float),
                velocity,
            )

        # ── Combine ──────────────────────────────────────────────────
        raw = (
            0.40 * velocity
            + 0.25 * acceleration
            + 0.35 * breakout
        ) * volume_mult

        value = float(np.clip(raw, -1.0, 1.0))

        # Confidence: higher when signals agree and volume confirms
        signals = [velocity, acceleration, breakout]
        signs = [np.sign(s) for s in signals if abs(s) > 0.05]
        if signs:
            agreement = abs(sum(signs)) / len(signs)
        else:
            agreement = 0.0
        confidence = float(np.clip(
            0.3 + 0.4 * agreement + 0.3 * min(volume_mult / 2.0, 1.0),
            0.1,
            0.9,
        ))

        return Signal(
            market_id=market_id,
            timestamp=now,
            name="momentum",
            value=value,
            confidence=confidence,
            metadata={
                "velocity": round(velocity, 4),
                "acceleration": round(acceleration, 4),
                "breakout": round(breakout, 4),
                "volume_multiplier": round(volume_mult, 4),
                "price_current": round(float(prices[-1]), 4),
                "price_change_pct": round(float((prices[-1] - prices[-self.velocity_window]) / prices[-self.velocity_window]) if prices[-self.velocity_window] != 0 else 0.0, 4),
            },
        )

    def _compute_velocity(self, prices: np.ndarray) -> float:
        """Normalized rate of price change over the velocity window."""
        window = prices[-self.velocity_window:]
        if len(window) < 2:
            return 0.0

        # Linear regression slope, normalized by price level
        x = np.arange(len(window))
        slope = np.polyfit(x, window, 1)[0]

        # Normalize: slope relative to mean price
        mean_price = np.mean(window)
        if mean_price == 0:
            return 0.0

        normalized = slope / mean_price * len(window)
        return float(np.clip(normalized * 5.0, -1.0, 1.0))

    def _compute_acceleration(self, prices: np.ndarray) -> float:
        """Rate of change of velocity (second derivative)."""
        if len(prices) < self.velocity_window + self.acceleration_window:
            return 0.0

        # Compute velocity at multiple points
        velocities = []
        for i in range(self.acceleration_window):
            end = len(prices) - i
            start = end - self.velocity_window
            if start < 0:
                break
            window = prices[start:end]
            x = np.arange(len(window))
            slope = np.polyfit(x, window, 1)[0]
            velocities.append(slope)

        velocities.reverse()
        if len(velocities) < 2:
            return 0.0

        # Acceleration = change in velocity
        accels = np.diff(velocities)
        avg_accel = np.mean(accels)

        mean_price = np.mean(prices[-self.velocity_window:])
        if mean_price == 0:
            return 0.0

        normalized = avg_accel / mean_price * 100
        return float(np.clip(normalized, -1.0, 1.0))

    def _compute_breakout(self, prices: np.ndarray) -> float:
        """
        Detect breakouts from recent trading range.
        Returns positive for upward breakout, negative for downward.
        """
        lookback = min(self.breakout_lookback, len(prices) - 1)
        if lookback < 5:
            return 0.0

        range_prices = prices[-(lookback + 1):-1]
        current = prices[-1]

        high = np.max(range_prices)
        low = np.min(range_prices)
        range_width = high - low

        if range_width == 0:
            return 0.0

        # How far current price is from the range midpoint, normalized
        midpoint = (high + low) / 2
        deviation = (current - midpoint) / range_width

        # Strong signal only for actual breakouts (beyond range)
        if current > high:
            return float(np.clip((current - high) / range_width * 3.0, 0.0, 1.0))
        elif current < low:
            return float(np.clip((current - low) / range_width * 3.0, -1.0, 0.0))
        else:
            # Within range: mild directional signal
            return float(np.clip(deviation * 0.3, -0.3, 0.3))

    def _volume_confirmation(
        self,
        volumes: np.ndarray,
        velocity: float,
    ) -> float:
        """
        Check if volume confirms the momentum direction.
        Returns multiplier > 1 if confirmed, < 1 if divergent.
        """
        recent_vol = np.mean(volumes[-3:]) if len(volumes) >= 3 else volumes[-1]
        avg_vol = np.mean(volumes[-self.velocity_window:])

        if avg_vol == 0:
            return 1.0

        vol_ratio = recent_vol / avg_vol

        if abs(velocity) > 0.1:
            # Strong momentum: volume should confirm
            if vol_ratio >= self.volume_confirm_threshold:
                return min(vol_ratio, 2.0)  # Volume confirms
            elif vol_ratio < 0.7:
                return 0.5  # Volume diverges — weaker signal
        return 1.0

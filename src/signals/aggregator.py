"""
Signal Aggregator

Combines multiple independent signals into a unified trading signal
using confidence-weighted ensemble with adaptive weights.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..data.models import Signal
from ..utils.logger import get_logger

logger = get_logger("signals.aggregator")


class SignalAggregator:
    """Combines multiple signals into a single composite signal."""

    def __init__(
        self,
        weights: Optional[dict[str, float]] = None,
        min_confidence: float = 0.2,
        min_signals: int = 2,
    ):
        self.base_weights = weights or {
            "orderflow": 0.35,
            "ai_probability": 0.40,
            "momentum": 0.25,
        }
        self.min_confidence = min_confidence
        self.min_signals = min_signals

        # Track signal performance for adaptive weighting
        self._signal_scores: dict[str, list[float]] = {}

    def aggregate(
        self,
        signals: list[Signal],
        now: Optional[datetime] = None,
    ) -> Signal:
        """
        Aggregate multiple signals into a composite signal.

        Uses confidence-weighted combination where each signal's
        contribution is scaled by both its configured weight and
        its self-reported confidence.
        """
        now = now or datetime.now(timezone.utc)

        # Filter by minimum confidence
        valid = [s for s in signals if s.confidence >= self.min_confidence]

        if len(valid) < self.min_signals:
            return Signal(
                market_id=signals[0].market_id if signals else "",
                timestamp=now,
                name="composite",
                value=0.0,
                confidence=0.0,
                metadata={
                    "reason": "insufficient_confident_signals",
                    "valid_count": len(valid),
                    "total_count": len(signals),
                },
            )

        # Compute confidence-weighted combination
        weighted_sum = 0.0
        total_weight = 0.0
        signal_details = {}

        for sig in valid:
            base_w = self.base_weights.get(sig.name, 0.1)
            effective_w = base_w * sig.confidence

            weighted_sum += sig.value * effective_w
            total_weight += effective_w

            signal_details[sig.name] = {
                "value": round(sig.value, 4),
                "confidence": round(sig.confidence, 4),
                "effective_weight": round(effective_w, 4),
            }

        if total_weight == 0:
            composite_value = 0.0
        else:
            composite_value = weighted_sum / total_weight

        composite_value = float(np.clip(composite_value, -1.0, 1.0))

        # Composite confidence:
        # Higher when signals agree, lower when they disagree
        values = [s.value for s in valid]
        if len(values) >= 2:
            # Agreement: check if signals point the same direction
            signs = [np.sign(v) for v in values if abs(v) > 0.05]
            if signs:
                agreement = abs(sum(signs)) / len(signs)
            else:
                agreement = 0.5

            avg_confidence = np.mean([s.confidence for s in valid])
            composite_confidence = float(np.clip(
                agreement * avg_confidence,
                0.1,
                0.95,
            ))
        else:
            composite_confidence = float(valid[0].confidence * 0.7)

        return Signal(
            market_id=valid[0].market_id,
            timestamp=now,
            name="composite",
            value=composite_value,
            confidence=composite_confidence,
            metadata={
                "signals": signal_details,
                "agreement": round(agreement if len(values) >= 2 else 0.0, 4),
                "num_signals": len(valid),
            },
        )

    def update_performance(self, signal_name: str, score: float):
        """Track signal performance for potential adaptive weighting."""
        if signal_name not in self._signal_scores:
            self._signal_scores[signal_name] = []
        self._signal_scores[signal_name].append(score)

        # Keep last 100 scores
        if len(self._signal_scores[signal_name]) > 100:
            self._signal_scores[signal_name] = self._signal_scores[signal_name][-100:]

    def get_performance_summary(self) -> dict:
        """Get performance summary for all tracked signals."""
        summary = {}
        for name, scores in self._signal_scores.items():
            if scores:
                summary[name] = {
                    "mean_score": round(np.mean(scores), 4),
                    "std_score": round(np.std(scores), 4),
                    "count": len(scores),
                    "recent_mean": round(np.mean(scores[-20:]), 4) if len(scores) >= 20 else None,
                }
        return summary

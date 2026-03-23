"""
Groq LLM Probability Estimator

Uses Groq's ultra-fast LLM inference (Llama 3.3 70B) to analyze
prediction market events and produce calibrated probability estimates.

Why Groq:
- Sub-second inference latency (critical for live trading)
- OpenAI-compatible API (easy integration)
- Free tier available for hackathon demo
- Llama 3.3 70B is strong at structured reasoning

Pipeline:
1. Construct context-rich prompt with event details
2. Call Groq API for probability estimate + reasoning
3. Parse structured JSON response
4. Calibrate and return probability estimate

Usage:
    export GROQ_API_KEY="gsk_..."
    estimator = GroqProbabilityEstimator()
    signal = estimator.estimate(market)
"""

from __future__ import annotations

import json
import re
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..data.models import Market, Signal
from ..utils.logger import get_logger

logger = get_logger("signals.groq_llm")

# Groq API endpoint (OpenAI-compatible)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Default model — Llama 3.3 70B is fast and capable
DEFAULT_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a calibrated prediction market analyst specializing in Polymarket events. Your job is to estimate the probability of events resolving YES or NO.

Rules:
1. Analyze the event objectively using available information
2. Consider base rates, historical precedent, and current context
3. Account for uncertainty — avoid overconfident extreme estimates
4. The market price is shown for reference but make your OWN independent assessment
5. Respond ONLY with valid JSON, no other text

Your response MUST be exactly this JSON format:
{"probability": <number 1-99>, "confidence": <number 20-90>, "reasoning": "<2-3 sentences>", "key_factors": ["<factor1>", "<factor2>", "<factor3>"]}"""


class GroqProbabilityEstimator:
    """
    Groq-powered LLM probability estimation for prediction markets.
    
    Uses Llama 3.3 70B via Groq for sub-second probability estimates.
    Falls back to heuristic estimation if Groq API is unavailable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        calibration_offset: float = 0.0,
        temperature: float = 0.3,
        max_tokens: int = 300,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model
        self.calibration_offset = calibration_offset
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._cache: dict[str, dict] = {}
        self._has_requests = False
        self._has_groq_sdk = False

        # Try native Groq SDK first, then requests as fallback
        try:
            import groq as _groq
            self._has_groq_sdk = True
            if self.api_key:
                self._groq_client = _groq.Groq(api_key=self.api_key)
            else:
                self._groq_client = None
        except ImportError:
            try:
                import requests as _req
                self._has_requests = True
            except ImportError:
                pass

    def estimate(
        self,
        market: Market,
        additional_context: str = "",
        current_market_price: Optional[float] = None,
    ) -> Signal:
        """
        Generate a probability estimate for a market event.
        
        Returns Signal with:
        - value: edge relative to market price (-1 to 1)
        - confidence: estimate confidence (0 to 1)
        - metadata: full LLM response including reasoning
        """
        now = datetime.now(timezone.utc)
        market_price = current_market_price or market.yes_price

        # Check cache (avoid duplicate API calls for same market state)
        cache_key = f"{market.condition_id}_{round(market_price, 2)}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return self._build_signal(market, cached, market_price, now)

        # Try Groq API
        if self.api_key and (self._has_groq_sdk or self._has_requests):
            try:
                result = self._call_groq(market, additional_context, market_price)
                self._cache[cache_key] = result
                logger.info(
                    f"Groq estimate for '{market.question[:50]}...': "
                    f"prob={result['probability']:.0%} conf={result['confidence']:.0%} "
                    f"[{result.get('source', 'groq')}]"
                )
                return self._build_signal(market, result, market_price, now)
            except Exception as e:
                logger.warning(f"Groq API failed: {e}, using heuristic fallback")

        # Heuristic fallback
        result = self._heuristic_estimate(market, market_price)
        return self._build_signal(market, result, market_price, now)

    def _call_groq(
        self,
        market: Market,
        context: str,
        market_price: float,
    ) -> dict:
        """Call Groq API for probability estimation."""
        user_prompt = self._build_prompt(market, context, market_price)

        if self._has_groq_sdk and self._groq_client:
            return self._call_via_sdk(user_prompt)
        else:
            return self._call_via_requests(user_prompt)

    def _call_via_sdk(self, user_prompt: str) -> dict:
        """Call Groq using the official Python SDK."""
        completion = self._groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content
        return self._parse_response(text)

    def _call_via_requests(self, user_prompt: str) -> dict:
        """Call Groq using raw HTTP requests (fallback if SDK not installed)."""
        import requests

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=10,  # Groq is fast — 10s is generous
        )
        response.raise_for_status()

        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return self._parse_response(text)

    def _build_prompt(
        self,
        market: Market,
        context: str,
        market_price: float,
    ) -> str:
        """Construct the analysis prompt."""
        prompt = f"""Estimate the probability for this Polymarket prediction market:

Event: {market.question}
Category: {market.category or 'General'}
Current market price (YES): {market_price:.1%}
Market volume: ${market.volume:,.0f}
Market liquidity: ${market.liquidity:,.0f}"""

        if context:
            prompt += f"\n\nAdditional context: {context}"

        prompt += "\n\nProvide your independent probability estimate as JSON."
        return prompt

    def _parse_response(self, text: str) -> dict:
        """Parse Groq's JSON response into a standardized result."""
        # Clean potential markdown wrapping
        clean = text.strip()
        if clean.startswith("```"):
            clean = re.sub(r'^```(?:json)?\s*', '', clean)
            clean = re.sub(r'\s*```$', '', clean)

        try:
            result = json.loads(clean)
        except json.JSONDecodeError:
            # Try to extract JSON object from response
            match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                raise ValueError(f"Could not parse Groq response: {text[:200]}")

        probability = float(result.get("probability", 50)) / 100
        probability = np.clip(probability, 0.01, 0.99)

        confidence = float(result.get("confidence", 50)) / 100
        confidence = np.clip(confidence, 0.1, 0.95)

        return {
            "probability": float(probability),
            "confidence": float(confidence),
            "reasoning": str(result.get("reasoning", "")),
            "key_factors": list(result.get("key_factors", [])),
            "source": "groq",
            "model": self.model,
        }

    def _heuristic_estimate(self, market: Market, market_price: float) -> dict:
        """
        Heuristic probability estimation when Groq is unavailable.
        
        Uses:
        - Slight mean reversion (extreme prices tend to revert)
        - Volume as confidence proxy (high volume = more efficient market)
        """
        base = market_price
        reversion = 0.05 * (0.5 - market_price)
        vol_factor = min(market.volume / 1_000_000, 1.0)

        estimate = base + reversion * (1.0 - vol_factor)
        estimate = float(np.clip(estimate, 0.02, 0.98))

        confidence = 0.3 + 0.3 * vol_factor

        return {
            "probability": estimate,
            "confidence": confidence,
            "reasoning": "Heuristic estimate: market price with mean-reversion adjustment, volume-weighted confidence.",
            "key_factors": ["market_price", "mean_reversion", "volume"],
            "source": "heuristic",
            "model": "none",
        }

    def _build_signal(
        self,
        market: Market,
        result: dict,
        market_price: float,
        now: datetime,
    ) -> Signal:
        """Convert estimation result to Signal object."""
        ai_prob = result["probability"] + self.calibration_offset
        ai_prob = float(np.clip(ai_prob, 0.01, 0.99))

        edge = ai_prob - market_price
        value = float(np.clip(edge * 5.0, -1.0, 1.0))

        return Signal(
            market_id=market.condition_id,
            timestamp=now,
            name="ai_probability",
            value=value,
            confidence=result["confidence"],
            metadata={
                "ai_probability": round(ai_prob, 4),
                "market_price": round(market_price, 4),
                "raw_edge": round(edge, 4),
                "reasoning": result.get("reasoning", ""),
                "key_factors": result.get("key_factors", []),
                "source": result.get("source", "unknown"),
                "model": result.get("model", "unknown"),
            },
        )

    def batch_estimate(
        self,
        markets: list[Market],
        additional_context: str = "",
    ) -> list[Signal]:
        """Estimate probabilities for multiple markets."""
        signals = []
        for market in markets:
            sig = self.estimate(market, additional_context)
            signals.append(sig)
        return signals

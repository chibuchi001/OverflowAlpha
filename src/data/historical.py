"""
Real Polymarket Historical Data Fetcher

Fetches resolved markets and their trade history from Polymarket's
public APIs, caches locally for reproducible backtesting.

Supports:
- Fetching resolved markets with known outcomes
- Trade history retrieval per market
- Price history at configurable intervals
- Local JSON caching for offline/reproducible runs
"""

from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import aiohttp
    import asyncio
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from ..data.models import Market, Trade, Side, Outcome
from ..utils.logger import get_logger

logger = get_logger("data.historical")

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


class HistoricalDataFetcher:
    """Fetches and caches real Polymarket historical data."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, endpoint: str, params: dict) -> str:
        raw = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _read_cache(self, key: str) -> Optional[dict | list]:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _write_cache(self, key: str, data):
        path = self.cache_dir / f"{key}.json"
        with open(path, "w") as f:
            json.dump(data, f)

    async def fetch_resolved_markets(
        self,
        limit: int = 50,
        min_volume: float = 50000,
    ) -> list[dict]:
        """
        Fetch resolved (closed) markets from Polymarket Gamma API.
        Returns raw market dicts with resolution info.
        """
        if not HAS_AIOHTTP:
            logger.warning("aiohttp not installed — using cached/sample data")
            return self._get_sample_resolved_markets()

        cache_key = self._cache_key("resolved_markets", {"limit": limit, "min_vol": min_volume})
        cached = self._read_cache(cache_key)
        if cached:
            logger.info(f"Loaded {len(cached)} resolved markets from cache")
            return cached

        params = {
            "limit": limit,
            "closed": "true",
            "order": "volume",
            "ascending": "false",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{GAMMA_API}/markets", params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            # Filter by volume
            markets = [
                m for m in (data if isinstance(data, list) else [])
                if float(m.get("volume", 0)) >= min_volume
            ]

            self._write_cache(cache_key, markets)
            logger.info(f"Fetched {len(markets)} resolved markets from Polymarket")
            return markets

        except Exception as e:
            logger.error(f"Failed to fetch resolved markets: {e}")
            return self._get_sample_resolved_markets()

    async def fetch_price_history(
        self,
        token_id: str,
        interval: str = "all",
        fidelity: int = 60,
    ) -> list[dict]:
        """Fetch price history for a token from CLOB API."""
        if not HAS_AIOHTTP:
            return []

        cache_key = self._cache_key("prices", {"token": token_id, "interval": interval})
        cached = self._read_cache(cache_key)
        if cached:
            return cached

        try:
            params = {"market": token_id, "interval": interval, "fidelity": fidelity}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{CLOB_API}/prices-history", params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            history = data.get("history", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            self._write_cache(cache_key, history)
            return history

        except Exception as e:
            logger.warning(f"Failed to fetch price history for {token_id}: {e}")
            return []

    async def fetch_trades(
        self,
        token_id: str,
        limit: int = 1000,
    ) -> list[dict]:
        """Fetch trade history for a token."""
        if not HAS_AIOHTTP:
            return []

        cache_key = self._cache_key("trades", {"token": token_id, "limit": limit})
        cached = self._read_cache(cache_key)
        if cached:
            return cached

        try:
            params = {"token_id": token_id, "limit": limit}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{CLOB_API}/trades", params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            trades = data if isinstance(data, list) else data.get("trades", [])
            self._write_cache(cache_key, trades)
            return trades

        except Exception as e:
            logger.warning(f"Failed to fetch trades for {token_id}: {e}")
            return []

    def _get_sample_resolved_markets(self) -> list[dict]:
        """
        Return sample resolved market data for offline development/demo.
        Based on real Polymarket market structures.
        """
        return [
            {
                "conditionId": "0x1234_btc_100k_2024",
                "question": "Will Bitcoin exceed $100,000 in 2024?",
                "slug": "will-bitcoin-exceed-100000-in-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.82, 0.18]',
                "volume": "15234567",
                "liquidity": "890000",
                "endDate": "2024-12-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "Yes",
                "category": "Crypto",
                "clobTokenIds": '["tok_btc100k_yes", "tok_btc100k_no"]',
            },
            {
                "conditionId": "0x5678_fed_rate_cut_mar",
                "question": "Will the Fed cut interest rates in March 2024?",
                "slug": "fed-rate-cut-march-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.05, 0.95]',
                "volume": "8765432",
                "liquidity": "450000",
                "endDate": "2024-03-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "No",
                "category": "Economics",
                "clobTokenIds": '["tok_fedmar_yes", "tok_fedmar_no"]',
            },
            {
                "conditionId": "0x9abc_trump_gop_nom",
                "question": "Will Trump win the GOP nomination?",
                "slug": "trump-gop-nomination-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.95, 0.05]',
                "volume": "45678901",
                "liquidity": "2100000",
                "endDate": "2024-07-18T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "Yes",
                "category": "Politics",
                "clobTokenIds": '["tok_trump_yes", "tok_trump_no"]',
            },
            {
                "conditionId": "0xdef0_eth_etf_approval",
                "question": "Will an Ethereum spot ETF be approved by May 2024?",
                "slug": "ethereum-spot-etf-may-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.25, 0.75]',
                "volume": "12345678",
                "liquidity": "670000",
                "endDate": "2024-05-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "No",
                "category": "Crypto",
                "clobTokenIds": '["tok_ethetf_yes", "tok_ethetf_no"]',
            },
            {
                "conditionId": "0x1111_sp500_ath_q1",
                "question": "Will S&P 500 reach a new ATH in Q1 2024?",
                "slug": "sp500-ath-q1-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.90, 0.10]',
                "volume": "6789012",
                "liquidity": "340000",
                "endDate": "2024-03-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "Yes",
                "category": "Economics",
                "clobTokenIds": '["tok_sp500_yes", "tok_sp500_no"]',
            },
            {
                "conditionId": "0x2222_tiktok_ban_2024",
                "question": "Will TikTok be banned in the US in 2024?",
                "slug": "tiktok-ban-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.12, 0.88]',
                "volume": "9876543",
                "liquidity": "520000",
                "endDate": "2024-12-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "No",
                "category": "Tech",
                "clobTokenIds": '["tok_tiktok_yes", "tok_tiktok_no"]',
            },
            {
                "conditionId": "0x3333_sol_200",
                "question": "Will SOL exceed $200 by end of 2024?",
                "slug": "sol-200-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.65, 0.35]',
                "volume": "7654321",
                "liquidity": "410000",
                "endDate": "2024-12-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "Yes",
                "category": "Crypto",
                "clobTokenIds": '["tok_sol200_yes", "tok_sol200_no"]',
            },
            {
                "conditionId": "0x4444_gov_shutdown_q1",
                "question": "Will there be a US government shutdown in Q1 2024?",
                "slug": "gov-shutdown-q1-2024",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '[0.40, 0.60]',
                "volume": "5432109",
                "liquidity": "280000",
                "endDate": "2024-03-31T23:59:59Z",
                "active": False,
                "closed": True,
                "resolved": True,
                "resolution": "No",
                "category": "Politics",
                "clobTokenIds": '["tok_shutdown_yes", "tok_shutdown_no"]',
            },
        ]


class RealMarketBacktestAdapter:
    """
    Converts real Polymarket data into SimulatedMarket format
    for use with the existing backtest engine.
    """

    @staticmethod
    def convert_resolved_market(
        raw: dict,
        price_history: list[float],
        volume_history: list[float],
        trades: list[Trade],
        timestamps: list[datetime],
    ):
        """Convert raw Polymarket data to SimulatedMarket-compatible format."""
        import json as _json
        from ..backtest.simulator import SimulatedMarket
        from ..data.models import OrderBookSnapshot
        import numpy as np

        # Parse outcomes and prices
        outcomes = raw.get("outcomes", ["Yes", "No"])
        if isinstance(outcomes, str):
            outcomes = _json.loads(outcomes)

        prices = raw.get("outcomePrices", [0.5, 0.5])
        if isinstance(prices, str):
            prices = [float(p) for p in _json.loads(prices)]

        # Determine resolution
        resolution_str = raw.get("resolution", "")
        if resolution_str == "Yes":
            resolution = 1.0
        elif resolution_str == "No":
            resolution = 0.0
        else:
            resolution = 0.5

        # Build Market object
        market = Market(
            condition_id=raw.get("conditionId", ""),
            question=raw.get("question", ""),
            slug=raw.get("slug", ""),
            outcomes=outcomes,
            outcome_prices=[float(p) for p in prices],
            volume=float(raw.get("volume", 0)),
            liquidity=float(raw.get("liquidity", 0)),
            end_date=None,
            active=False,
            category=raw.get("category", ""),
        )

        # Generate synthetic orderbooks from price data
        rng = np.random.RandomState(hash(market.condition_id) % 2**31)
        orderbooks = []
        for i, (price, ts) in enumerate(zip(price_history, timestamps)):
            spread = rng.uniform(0.005, 0.02)
            bids = [(round(max(0.01, price - spread/2 - j*0.01), 4), round(rng.exponential(150), 2)) for j in range(3)]
            asks = [(round(min(0.99, price + spread/2 + j*0.01), 4), round(rng.exponential(150), 2)) for j in range(3)]
            orderbooks.append(OrderBookSnapshot(
                market_id=market.condition_id,
                timestamp=ts,
                bids=sorted(bids, key=lambda x: x[0], reverse=True),
                asks=sorted(asks, key=lambda x: x[0]),
            ))

        return SimulatedMarket(
            market=market,
            price_history=price_history,
            volume_history=volume_history,
            trades=trades,
            orderbook_snapshots=orderbooks,
            timestamps=timestamps,
            resolution=resolution,
            resolution_time=timestamps[-1] if timestamps else datetime.now(timezone.utc),
            true_probability=resolution,  # For resolved markets, true prob = outcome
        )

"""Polymarket CLOB API client for fetching market data, trades, and orderbook."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

try:
    import aiohttp
except ImportError:
    aiohttp = None  # Optional: only needed for live data

from ..utils.logger import get_logger
from .models import Market, Trade, OrderBookSnapshot, Side, Outcome

logger = get_logger("data.polymarket")

# Polymarket CLOB API endpoints
BASE_URL = "https://clob.polymarket.com"
GAMMA_URL = "https://gamma-api.polymarket.com"


class PolymarketClient:
    """Client for Polymarket's CLOB and Gamma APIs."""

    def __init__(self, base_url: str = BASE_URL, gamma_url: str = GAMMA_URL):
        self.base_url = base_url.rstrip("/")
        self.gamma_url = gamma_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Accept": "application/json"}
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, url: str, params: dict | None = None) -> dict | list:
        session = await self._get_session()
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logger.error(f"API request failed: {url} - {e}")
            raise

    # ── Market Data ──────────────────────────────────────────────────

    async def get_markets(
        self,
        limit: int = 100,
        active: bool = True,
        closed: bool = False,
    ) -> list[Market]:
        """Fetch markets from Gamma API."""
        params = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": "volume24hr",
            "ascending": "false",
        }
        data = await self._get(f"{self.gamma_url}/markets", params)

        markets = []
        for m in data if isinstance(data, list) else []:
            try:
                prices = []
                if m.get("outcomePrices"):
                    raw = m["outcomePrices"]
                    if isinstance(raw, str):
                        import json
                        prices = [float(p) for p in json.loads(raw)]
                    elif isinstance(raw, list):
                        prices = [float(p) for p in raw]

                market = Market(
                    condition_id=m.get("conditionId", m.get("id", "")),
                    question=m.get("question", ""),
                    slug=m.get("slug", ""),
                    outcomes=m.get("outcomes", ["Yes", "No"]),
                    outcome_prices=prices,
                    volume=float(m.get("volume", 0)),
                    liquidity=float(m.get("liquidity", 0)),
                    end_date=_parse_dt(m.get("endDate")),
                    active=m.get("active", True),
                    category=m.get("category", ""),
                    tokens=m.get("clobTokenIds", []) if isinstance(m.get("clobTokenIds"), list) else [],
                )
                markets.append(market)
            except Exception as e:
                logger.warning(f"Failed to parse market: {e}")
                continue

        logger.info(f"Fetched {len(markets)} markets")
        return markets

    async def get_market(self, condition_id: str) -> Optional[Market]:
        """Fetch a single market by condition ID."""
        data = await self._get(f"{self.gamma_url}/markets/{condition_id}")
        if not data:
            return None

        m = data
        prices = []
        if m.get("outcomePrices"):
            raw = m["outcomePrices"]
            if isinstance(raw, str):
                import json
                prices = [float(p) for p in json.loads(raw)]
            elif isinstance(raw, list):
                prices = [float(p) for p in raw]

        return Market(
            condition_id=m.get("conditionId", m.get("id", "")),
            question=m.get("question", ""),
            slug=m.get("slug", ""),
            outcomes=m.get("outcomes", ["Yes", "No"]),
            outcome_prices=prices,
            volume=float(m.get("volume", 0)),
            liquidity=float(m.get("liquidity", 0)),
            end_date=_parse_dt(m.get("endDate")),
            active=m.get("active", True),
            category=m.get("category", ""),
            tokens=m.get("clobTokenIds", []) if isinstance(m.get("clobTokenIds"), list) else [],
        )

    # ── Orderbook ────────────────────────────────────────────────────

    async def get_orderbook(self, token_id: str) -> OrderBookSnapshot:
        """Fetch current orderbook for a token."""
        data = await self._get(f"{self.base_url}/book", {"token_id": token_id})

        bids = [
            (float(o["price"]), float(o["size"]))
            for o in data.get("bids", [])
        ]
        asks = [
            (float(o["price"]), float(o["size"]))
            for o in data.get("asks", [])
        ]

        # Sort: bids descending, asks ascending
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        return OrderBookSnapshot(
            market_id=token_id,
            timestamp=datetime.now(timezone.utc),
            bids=bids,
            asks=asks,
        )

    # ── Trade History ────────────────────────────────────────────────

    async def get_trades(
        self,
        token_id: str,
        limit: int = 500,
    ) -> list[Trade]:
        """Fetch recent trades for a token from CLOB."""
        params = {"token_id": token_id, "limit": limit}
        data = await self._get(f"{self.base_url}/trades", params)

        trades = []
        for t in data if isinstance(data, list) else data.get("trades", []):
            try:
                trade = Trade(
                    market_id=token_id,
                    timestamp=_parse_dt(t.get("timestamp", t.get("match_time", ""))) or datetime.now(timezone.utc),
                    side=Side.BUY if t.get("side", "").upper() == "BUY" else Side.SELL,
                    outcome=Outcome.YES if t.get("outcome", "Yes") == "Yes" else Outcome.NO,
                    price=float(t.get("price", 0)),
                    size=float(t.get("size", 0)),
                    maker=t.get("maker_address", ""),
                    taker=t.get("taker_address", ""),
                )
                trades.append(trade)
            except Exception as e:
                logger.warning(f"Failed to parse trade: {e}")
                continue

        return trades

    # ── Price History ────────────────────────────────────────────────

    async def get_price_history(
        self,
        token_id: str,
        interval: str = "1d",
        fidelity: int = 60,
    ) -> list[dict]:
        """Fetch price history for a token."""
        params = {"market": token_id, "interval": interval, "fidelity": fidelity}
        data = await self._get(f"{self.base_url}/prices-history", params)

        if isinstance(data, dict) and "history" in data:
            return data["history"]
        elif isinstance(data, list):
            return data
        return []


def _parse_dt(val) -> Optional[datetime]:
    """Parse various datetime formats from API responses."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except (ValueError, OSError):
            return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
    if isinstance(val, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None

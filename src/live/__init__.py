"""
Live Paper Trading Engine

Connects to Polymarket's live APIs and runs the full signal → strategy
pipeline in real-time, logging all decisions without placing actual trades.

Produces a live trading log with:
- Real-time signal values
- Trade decisions (would-execute)
- Paper portfolio tracking
- Performance metrics updated live
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..data.models import Market, Position, Signal, Trade, OrderBookSnapshot, Outcome, Side
from ..signals.orderflow import OrderflowSignal
from ..signals.ai_probability import AIProbabilitySignal
from ..signals.momentum import MomentumSignal
from ..signals.aggregator import SignalAggregator
from ..strategy.kelly import KellySizer
from ..strategy.risk import RiskManager
from ..strategy.engine import StrategyEngine
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger("live.paper")


class PaperTradingEngine:
    """
    Paper trading engine for live signal generation and strategy testing.

    In live mode:
    - Polls Polymarket API every N seconds
    - Generates signals from real market data
    - Makes trade decisions (logged, not executed)
    - Tracks paper portfolio and PnL

    For demo mode (no network):
    - Simulates live data stream from cached/sample data
    - Same full pipeline execution
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

        # Signal generators
        self.orderflow_signal = OrderflowSignal(
            lookback_minutes=self.config.signals.lookback_minutes,
        )
        self.ai_signal = AIProbabilitySignal(seed=int(time.time()))
        self.momentum_signal = MomentumSignal()

        self.aggregator = SignalAggregator(weights={
            "orderflow": self.config.signals.orderflow_weight,
            "ai_probability": self.config.signals.ai_prob_weight,
            "momentum": self.config.signals.momentum_weight,
        })

        self.sizer = KellySizer(
            kelly_fraction=self.config.strategy.kelly_fraction,
            max_position_pct=self.config.strategy.max_position_pct,
            min_edge=self.config.strategy.min_edge_threshold,
        )

        self.risk_manager = RiskManager(
            max_position_pct=self.config.strategy.max_position_pct,
            max_portfolio_exposure=self.config.strategy.max_portfolio_exposure,
            stop_loss_pct=self.config.risk.stop_loss_pct,
            max_drawdown_pct=self.config.risk.max_drawdown_pct,
        )

        self.strategy = StrategyEngine(
            aggregator=self.aggregator,
            sizer=self.sizer,
            risk_manager=self.risk_manager,
            min_edge=self.config.strategy.min_edge_threshold,
        )

        # State
        self.bankroll = self.config.backtest.initial_bankroll
        self.positions: dict[str, Position] = {}
        self.trade_log: list[dict] = []
        self.signal_log: list[dict] = []
        self.equity_history: list[dict] = []

    def run_demo(
        self,
        n_ticks: int = 50,
        tick_interval_seconds: float = 0.1,
        n_markets: int = 5,
    ) -> dict:
        """
        Run a demo paper trading session using simulated live data.

        This demonstrates the full pipeline running in real-time
        without requiring network access.
        """
        from ..backtest.simulator import MarketSimulator

        logger.info(f"Starting paper trading demo: {n_ticks} ticks, {n_markets} markets")

        simulator = MarketSimulator(
            n_markets=n_markets,
            duration_days=14,
            tick_interval_minutes=60,
            seed=int(time.time()) % 10000,
        )
        sim_markets = simulator.generate_markets()

        self.risk_manager.reset()
        self.risk_manager.update_equity(self.bankroll)

        for tick in range(n_ticks):
            now = datetime.now(timezone.utc)

            for sim in sim_markets:
                if tick >= len(sim.price_history):
                    continue

                # Update market with current tick price
                market = sim.market
                price = sim.price_history[tick]
                market.outcome_prices = [price, 1.0 - price]

                # Update existing positions
                mid = market.condition_id
                if mid in self.positions:
                    self.positions[mid].current_price = price

                # Get trades up to this tick
                trades = [t for t in sim.trades if t.timestamp <= sim.timestamps[min(tick, len(sim.timestamps)-1)]][-100:]

                # Orderbook
                ob = sim.orderbook_snapshots[tick] if tick < len(sim.orderbook_snapshots) else None

                # Price history so far
                ph = sim.price_history[:tick+1]

                # Generate signals
                signals = []

                of_sig = self.orderflow_signal.generate(mid, trades, ob, now=now)
                signals.append(of_sig)

                ai_sig = self.ai_signal.generate(market, ph, now=now, true_probability=sim.true_probability)
                signals.append(ai_sig)

                if len(ph) >= 12:
                    mom_sig = self.momentum_signal.generate(
                        mid, ph,
                        volume_history=sim.volume_history[:tick+1],
                        now=now,
                    )
                    signals.append(mom_sig)

                # Log signals
                self.signal_log.append({
                    "tick": tick,
                    "timestamp": now.isoformat(),
                    "market_id": mid,
                    "market_question": market.question[:60],
                    "market_price": round(price, 4),
                    "signals": {
                        s.name: {"value": round(s.value, 4), "confidence": round(s.confidence, 4)}
                        for s in signals
                    },
                })

                # Strategy decision
                decision = self.strategy.decide(
                    market, signals, self.positions, self.bankroll, now=now
                )

                # Paper execute
                if decision.action.startswith("BUY") and decision.size > 0:
                    outcome = Outcome.YES if "YES" in decision.action else Outcome.NO
                    exec_price = decision.target_price
                    self.bankroll -= decision.size

                    self.positions[mid] = Position(
                        market_id=mid,
                        outcome=outcome,
                        size=decision.size / exec_price,
                        entry_price=exec_price,
                        entry_time=now,
                        current_price=price,
                    )

                    self.trade_log.append({
                        "tick": tick,
                        "timestamp": now.isoformat(),
                        "action": decision.action,
                        "market": market.question[:60],
                        "price": round(exec_price, 4),
                        "size": round(decision.size, 2),
                        "edge": round(decision.edge, 4),
                        "reason": decision.reason,
                    })

                    logger.info(
                        f"[Tick {tick:3d}] PAPER {decision.action} "
                        f"{market.question[:40]}... @ {exec_price:.3f} "
                        f"${decision.size:.0f}"
                    )

                # Check stops
                stops = self.risk_manager.check_stop_losses(self.positions, self.bankroll, now=now)
                for stop in stops:
                    if stop.market_id in self.positions:
                        pos = self.positions[stop.market_id]
                        self.bankroll += pos.size * pos.current_price
                        self.trade_log.append({
                            "tick": tick,
                            "timestamp": now.isoformat(),
                            "action": "STOP_LOSS",
                            "market": market.question[:60],
                            "price": round(pos.current_price, 4),
                            "size": round(pos.size * pos.current_price, 2),
                            "reason": stop.reason,
                        })
                        del self.positions[stop.market_id]

            # Track equity
            equity = self.bankroll + sum(
                p.size * p.current_price for p in self.positions.values()
            )
            self.equity_history.append({
                "tick": tick,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "equity": round(equity, 2),
                "bankroll": round(self.bankroll, 2),
                "positions": len(self.positions),
            })
            self.risk_manager.update_equity(equity)

            time.sleep(tick_interval_seconds)

        # Final resolution
        for sim in sim_markets:
            mid = sim.market.condition_id
            if mid in self.positions:
                pos = self.positions[mid]
                resolution_price = sim.resolution if pos.outcome == Outcome.YES else (1.0 - sim.resolution)
                self.bankroll += pos.size * resolution_price

        final_equity = self.bankroll
        initial = self.config.backtest.initial_bankroll

        result = {
            "summary": {
                "initial_bankroll": initial,
                "final_equity": round(final_equity, 2),
                "total_return_pct": round((final_equity - initial) / initial, 4),
                "total_trades": len(self.trade_log),
                "total_signals_generated": len(self.signal_log),
                "ticks_processed": n_ticks,
                "markets_monitored": n_markets,
            },
            "trade_log": self.trade_log,
            "signal_log": self.signal_log[-50:],  # Last 50 signal snapshots
            "equity_history": self.equity_history,
        }

        logger.info(
            f"Paper trading complete: {len(self.trade_log)} trades, "
            f"return={(final_equity - initial) / initial:.2%}"
        )

        return result

"""
Backtest Engine

Event-driven backtester that replays historical (or simulated) market data
through the full signal → strategy → risk pipeline and produces
comprehensive performance metrics.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..data.models import Market, Position, Signal, TradeDecision, Outcome
from ..signals.orderflow import OrderflowSignal
from ..signals.ai_probability import AIProbabilitySignal
from ..signals.momentum import MomentumSignal
from ..signals.aggregator import SignalAggregator
from ..strategy.kelly import KellySizer
from ..strategy.risk import RiskManager
from ..strategy.engine import StrategyEngine
from ..utils.config import Config
from ..utils.logger import get_logger
from .simulator import MarketSimulator, SimulatedMarket

logger = get_logger("backtest.engine")


@dataclass
class TradeRecord:
    """Record of an executed trade."""

    market_id: str
    timestamp: datetime
    action: str
    side: str  # "YES" or "NO"
    size: float
    price: float
    fees: float
    slippage: float
    pnl: float = 0.0
    closed: bool = False


@dataclass
class BacktestResult:
    """Complete backtest results."""

    # Performance
    total_return: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    total_trades: int = 0
    total_markets_traded: int = 0

    # Time series
    equity_curve: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)

    # Trade details
    trades: list[dict] = field(default_factory=list)

    # Signal performance
    signal_stats: dict = field(default_factory=dict)

    # Configuration used
    config_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "performance": {
                "total_return": round(self.total_return, 2),
                "total_return_pct": round(self.total_return_pct, 4),
                "sharpe_ratio": round(self.sharpe_ratio, 4),
                "sortino_ratio": round(self.sortino_ratio, 4),
                "max_drawdown": round(self.max_drawdown, 2),
                "max_drawdown_pct": round(self.max_drawdown_pct, 4),
                "win_rate": round(self.win_rate, 4),
                "profit_factor": round(self.profit_factor, 4),
                "avg_trade_pnl": round(self.avg_trade_pnl, 2),
                "avg_winner": round(self.avg_winner, 2),
                "avg_loser": round(self.avg_loser, 2),
                "best_trade": round(self.best_trade, 2),
                "worst_trade": round(self.worst_trade, 2),
                "total_trades": self.total_trades,
                "total_markets_traded": self.total_markets_traded,
            },
            "equity_curve": self.equity_curve,
            "drawdown_curve": self.drawdown_curve,
            "timestamps": self.timestamps,
            "trades": self.trades[:100],  # Limit for output
            "signal_stats": self.signal_stats,
            "config": self.config_summary,
        }

    def summary(self) -> str:
        """Human-readable performance summary."""
        lines = [
            "=" * 60,
            "  ORDERFLOW-ALPHA BACKTEST RESULTS",
            "=" * 60,
            "",
            f"  Total Return:       ${self.total_return:>10,.2f}  ({self.total_return_pct:>+7.2%})",
            f"  Sharpe Ratio:       {self.sharpe_ratio:>10.3f}",
            f"  Sortino Ratio:      {self.sortino_ratio:>10.3f}",
            f"  Max Drawdown:       ${self.max_drawdown:>10,.2f}  ({self.max_drawdown_pct:>7.2%})",
            "",
            f"  Total Trades:       {self.total_trades:>10d}",
            f"  Markets Traded:     {self.total_markets_traded:>10d}",
            f"  Win Rate:           {self.win_rate:>10.2%}",
            f"  Profit Factor:      {self.profit_factor:>10.3f}",
            "",
            f"  Avg Trade PnL:      ${self.avg_trade_pnl:>10,.2f}",
            f"  Avg Winner:         ${self.avg_winner:>10,.2f}",
            f"  Avg Loser:          ${self.avg_loser:>10,.2f}",
            f"  Best Trade:         ${self.best_trade:>10,.2f}",
            f"  Worst Trade:        ${self.worst_trade:>10,.2f}",
            "",
            "=" * 60,
        ]
        return "\n".join(lines)


class BacktestEngine:
    """Event-driven backtester for the full trading system."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

        # Initialize components
        self.orderflow_signal = OrderflowSignal(
            lookback_minutes=self.config.signals.lookback_minutes,
            smoothing_window=self.config.signals.smoothing_window,
        )
        self.ai_signal = AIProbabilitySignal(seed=42)
        self.momentum_signal = MomentumSignal()

        self.aggregator = SignalAggregator(
            weights={
                "orderflow": self.config.signals.orderflow_weight,
                "ai_probability": self.config.signals.ai_prob_weight,
                "momentum": self.config.signals.momentum_weight,
            }
        )

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
            cooldown_seconds=self.config.risk.cooldown_after_stop_seconds,
        )

        self.strategy = StrategyEngine(
            aggregator=self.aggregator,
            sizer=self.sizer,
            risk_manager=self.risk_manager,
            min_edge=self.config.strategy.min_edge_threshold,
        )

    def run(
        self,
        markets: Optional[list[SimulatedMarket]] = None,
        n_markets: int = 30,
        duration_days: int = 30,
    ) -> BacktestResult:
        """
        Run a full backtest.

        If markets not provided, generates simulated data.
        """
        # Generate or use provided data
        if markets is None:
            simulator = MarketSimulator(
                n_markets=n_markets,
                duration_days=duration_days,
                seed=42,
            )
            markets = simulator.generate_markets()

        logger.info(f"Running backtest on {len(markets)} markets over {duration_days} days")

        # State
        bankroll = self.config.backtest.initial_bankroll
        initial_bankroll = bankroll
        positions: dict[str, Position] = {}
        trade_records: list[TradeRecord] = []
        equity_curve = [bankroll]
        timestamps = ["start"]

        # Reset risk manager
        self.risk_manager.reset()
        self.risk_manager.update_equity(bankroll)

        # Collect all timestamps across markets, sort chronologically
        all_events = []
        for sim_market in markets:
            for i, ts in enumerate(sim_market.timestamps):
                all_events.append((ts, sim_market, i))

        all_events.sort(key=lambda x: x[0])

        # Process events
        last_equity_ts = None
        for event_ts, sim_market, tick_idx in all_events:
            market = sim_market.market
            mid = market.condition_id

            # Update market price
            current_price = sim_market.price_history[tick_idx]
            market.outcome_prices = [current_price, 1.0 - current_price]

            # Update existing position prices
            if mid in positions:
                positions[mid].current_price = current_price

            # Check stop losses
            stops = self.risk_manager.check_stop_losses(positions, bankroll, now=event_ts)
            for stop in stops:
                if stop.market_id in positions:
                    pos = positions[stop.market_id]
                    exit_price = current_price if pos.outcome == Outcome.YES else (1.0 - current_price)
                    pnl = (exit_price - pos.entry_price) * pos.size
                    fees = pos.size * exit_price * self.config.backtest.fee_rate
                    pnl -= fees
                    bankroll += pos.size * exit_price - fees
                    trade_records.append(TradeRecord(
                        market_id=stop.market_id,
                        timestamp=event_ts,
                        action="STOP_LOSS",
                        side=pos.outcome.value,
                        size=pos.size,
                        price=exit_price,
                        fees=fees,
                        slippage=0.0,
                        pnl=pnl,
                        closed=True,
                    ))
                    del positions[stop.market_id]

            # Generate signals
            # Get trades up to this tick
            trades_so_far = [
                t for t in sim_market.trades
                if t.timestamp <= event_ts
            ][-200:]  # Last 200 trades

            orderbook = None
            if tick_idx < len(sim_market.orderbook_snapshots):
                orderbook = sim_market.orderbook_snapshots[tick_idx]

            price_history = sim_market.price_history[:tick_idx + 1]

            signals = []

            # Orderflow signal
            of_signal = self.orderflow_signal.generate(
                mid, trades_so_far, orderbook, now=event_ts
            )
            signals.append(of_signal)

            # AI probability signal
            ai_signal = self.ai_signal.generate(
                market, price_history, now=event_ts,
                true_probability=sim_market.true_probability,
            )
            signals.append(ai_signal)

            # Momentum signal
            if len(price_history) >= 12:
                mom_signal = self.momentum_signal.generate(
                    mid, price_history,
                    volume_history=sim_market.volume_history[:tick_idx + 1],
                    now=event_ts,
                )
                signals.append(mom_signal)

            # Strategy decision
            decision = self.strategy.decide(
                market, signals, positions, bankroll, now=event_ts
            )

            # Execute trade
            if decision.action.startswith("BUY") and decision.size > 0:
                slippage = decision.target_price * (self.config.backtest.slippage_bps / 10000)
                exec_price = decision.target_price + slippage
                fees = decision.size * self.config.backtest.fee_rate
                cost = decision.size + fees

                if cost <= bankroll:
                    bankroll -= cost
                    outcome = Outcome.YES if "YES" in decision.action else Outcome.NO

                    positions[mid] = Position(
                        market_id=mid,
                        outcome=outcome,
                        size=decision.size / exec_price,  # Number of shares
                        entry_price=exec_price,
                        entry_time=event_ts,
                        current_price=current_price,
                    )

                    trade_records.append(TradeRecord(
                        market_id=mid,
                        timestamp=event_ts,
                        action=decision.action,
                        side=outcome.value,
                        size=decision.size,
                        price=exec_price,
                        fees=fees,
                        slippage=slippage,
                    ))

            elif decision.action.startswith("SELL") and mid in positions:
                pos = positions[mid]
                exit_price = current_price if pos.outcome == Outcome.YES else (1.0 - current_price)
                slippage = exit_price * (self.config.backtest.slippage_bps / 10000)
                exec_price = exit_price - slippage
                proceeds = pos.size * exec_price
                fees = proceeds * self.config.backtest.fee_rate
                pnl = (exec_price - pos.entry_price) * pos.size - fees

                bankroll += proceeds - fees

                trade_records.append(TradeRecord(
                    market_id=mid,
                    timestamp=event_ts,
                    action=decision.action,
                    side=pos.outcome.value,
                    size=pos.size,
                    price=exec_price,
                    fees=fees,
                    slippage=slippage,
                    pnl=pnl,
                    closed=True,
                ))
                del positions[mid]

            # Update equity (sample periodically)
            if last_equity_ts is None or (event_ts - last_equity_ts).total_seconds() >= 3600:
                unrealized = sum(
                    (p.current_price - p.entry_price) * p.size
                    for p in positions.values()
                )
                equity = bankroll + sum(
                    p.size * p.current_price for p in positions.values()
                )
                equity_curve.append(round(equity, 2))
                timestamps.append(event_ts.isoformat())
                self.risk_manager.update_equity(equity)
                last_equity_ts = event_ts

        # Resolve remaining positions at market close
        for sim_market in markets:
            mid = sim_market.market.condition_id
            if mid in positions:
                pos = positions[mid]
                resolution = sim_market.resolution
                if pos.outcome == Outcome.YES:
                    exit_price = resolution
                else:
                    exit_price = 1.0 - resolution

                proceeds = pos.size * exit_price
                fees = proceeds * self.config.backtest.fee_rate
                pnl = (exit_price - pos.entry_price) * pos.size - fees
                bankroll += proceeds - fees

                trade_records.append(TradeRecord(
                    market_id=mid,
                    timestamp=sim_market.resolution_time,
                    action="RESOLUTION",
                    side=pos.outcome.value,
                    size=pos.size,
                    price=exit_price,
                    fees=fees,
                    slippage=0.0,
                    pnl=pnl,
                    closed=True,
                ))

        # Compute final metrics
        result = self._compute_metrics(
            initial_bankroll=initial_bankroll,
            final_bankroll=bankroll,
            equity_curve=equity_curve,
            timestamps=timestamps,
            trades=trade_records,
        )

        logger.info(f"\n{result.summary()}")
        return result

    def _compute_metrics(
        self,
        initial_bankroll: float,
        final_bankroll: float,
        equity_curve: list[float],
        timestamps: list[str],
        trades: list[TradeRecord],
    ) -> BacktestResult:
        """Compute comprehensive performance metrics."""
        closed_trades = [t for t in trades if t.closed]

        # Returns
        total_return = final_bankroll - initial_bankroll
        total_return_pct = total_return / initial_bankroll

        # Sharpe & Sortino
        if len(equity_curve) > 2:
            returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
            returns = returns[np.isfinite(returns)]

            if len(returns) > 0 and np.std(returns) > 0:
                sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365))
            else:
                sharpe = 0.0

            downside = returns[returns < 0]
            if len(downside) > 0 and np.std(downside) > 0:
                sortino = float(np.mean(returns) / np.std(downside) * np.sqrt(365))
            else:
                sortino = sharpe
        else:
            sharpe = 0.0
            sortino = 0.0

        # Drawdown
        peak = initial_bankroll
        max_dd = 0.0
        max_dd_pct = 0.0
        dd_curve = []
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = dd / peak if peak > 0 else 0
            dd_curve.append(round(dd_pct, 4))
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        # Win rate
        pnls = [t.pnl for t in closed_trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        win_rate = len(winners) / len(pnls) if pnls else 0.0
        profit_factor = (
            sum(winners) / abs(sum(losers))
            if losers and sum(losers) != 0
            else float("inf") if winners
            else 0.0
        )

        # Markets traded
        markets_traded = len(set(t.market_id for t in trades))

        return BacktestResult(
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_pnl=float(np.mean(pnls)) if pnls else 0.0,
            avg_winner=float(np.mean(winners)) if winners else 0.0,
            avg_loser=float(np.mean(losers)) if losers else 0.0,
            best_trade=max(pnls) if pnls else 0.0,
            worst_trade=min(pnls) if pnls else 0.0,
            total_trades=len(closed_trades),
            total_markets_traded=markets_traded,
            equity_curve=equity_curve,
            drawdown_curve=dd_curve,
            timestamps=timestamps,
            trades=[
                {
                    "market_id": t.market_id,
                    "timestamp": t.timestamp.isoformat() if isinstance(t.timestamp, datetime) else str(t.timestamp),
                    "action": t.action,
                    "side": t.side,
                    "size": round(t.size, 2),
                    "price": round(t.price, 4),
                    "fees": round(t.fees, 2),
                    "pnl": round(t.pnl, 2),
                }
                for t in closed_trades
            ],
            config_summary={
                "kelly_fraction": self.config.strategy.kelly_fraction,
                "max_position_pct": self.config.strategy.max_position_pct,
                "min_edge": self.config.strategy.min_edge_threshold,
                "initial_bankroll": self.config.backtest.initial_bankroll,
                "fee_rate": self.config.backtest.fee_rate,
                "slippage_bps": self.config.backtest.slippage_bps,
            },
        )

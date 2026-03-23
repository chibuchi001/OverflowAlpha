"""Configuration management for orderflow-alpha."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class StrategyConfig:
    kelly_fraction: float = 0.5
    max_position_pct: float = 0.15
    max_portfolio_exposure: float = 0.60
    min_edge_threshold: float = 0.05
    rebalance_interval_seconds: int = 300


@dataclass
class SignalConfig:
    orderflow_weight: float = 0.35
    ai_prob_weight: float = 0.40
    momentum_weight: float = 0.25
    lookback_minutes: int = 60
    smoothing_window: int = 5


@dataclass
class RiskConfig:
    stop_loss_pct: float = 0.25
    max_drawdown_pct: float = 0.20
    max_correlated_exposure: float = 0.30
    cooldown_after_stop_seconds: int = 1800


@dataclass
class BacktestConfig:
    initial_bankroll: float = 10000.0
    fee_rate: float = 0.002
    slippage_bps: float = 10.0
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"


@dataclass
class DataConfig:
    polymarket_api_url: str = "https://clob.polymarket.com"
    polygon_rpc_url: str = "https://polygon-rpc.com"
    cache_dir: str = "./data/cache"
    refresh_interval_seconds: int = 30


@dataclass
class Config:
    """Root configuration object."""

    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    signals: SignalConfig = field(default_factory=SignalConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data: DataConfig = field(default_factory=DataConfig)

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        return cls(
            strategy=StrategyConfig(**data.get("strategy", {})),
            signals=SignalConfig(**data.get("signals", {})),
            risk=RiskConfig(**data.get("risk", {})),
            backtest=BacktestConfig(**data.get("backtest", {})),
            data=DataConfig(**data.get("data", {})),
        )


def load_config(path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    if path is None:
        path = os.environ.get("ORDERFLOW_CONFIG", "config.yaml")

    config_path = Path(path)
    if not config_path.exists():
        return Config()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    return Config.from_dict(raw or {})

"""Tests for orderflow-alpha core components."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
import numpy as np

from src.data.models import Market, Trade, Signal, OrderBookSnapshot, Side, Outcome, Position
from src.signals.orderflow import OrderflowSignal
from src.signals.ai_probability import AIProbabilitySignal
from src.signals.momentum import MomentumSignal
from src.signals.aggregator import SignalAggregator
from src.strategy.kelly import KellySizer
from src.strategy.risk import RiskManager
from src.backtest.engine import BacktestEngine
from src.utils.config import Config, load_config


def test_kelly_sizer():
    """Test Kelly criterion position sizing."""
    sizer = KellySizer(kelly_fraction=0.5, max_position_pct=0.15, min_edge=0.05)

    # Strong edge case
    result = sizer.compute(
        estimated_prob=0.65,
        market_price=0.50,
        confidence=0.8,
        bankroll=10000,
    )
    assert result.fraction > 0, "Should recommend a position for 15% edge"
    assert result.fraction <= 0.15, "Should not exceed max position"
    assert result.edge > 0, "Edge should be positive"
    print(f"  Kelly strong edge: fraction={result.fraction:.4f}, edge={result.edge:.4f}")

    # No edge case
    result = sizer.compute(
        estimated_prob=0.52,
        market_price=0.50,
        confidence=0.8,
        bankroll=10000,
    )
    assert result.fraction == 0, "Should not trade with edge below threshold"
    print(f"  Kelly no edge: fraction={result.fraction:.4f}")

    # Negative edge (buy NO)
    result = sizer.compute(
        estimated_prob=0.35,
        market_price=0.50,
        confidence=0.7,
        bankroll=10000,
    )
    assert result.fraction > 0, "Should recommend position for NO side"
    print(f"  Kelly negative edge: fraction={result.fraction:.4f}, edge={result.edge:.4f}")

    print("✓ Kelly sizer tests passed")


def test_orderflow_signal():
    """Test orderflow signal generation."""
    signal_gen = OrderflowSignal(lookback_minutes=60)
    now = datetime.now(timezone.utc)

    # Create buy-heavy trades
    trades = []
    for i in range(20):
        trades.append(Trade(
            market_id="test",
            timestamp=now,
            side=Side.BUY,
            outcome=Outcome.YES,
            price=0.55,
            size=100.0,
            taker=f"0x{'a' * 40}",
        ))
    for i in range(5):
        trades.append(Trade(
            market_id="test",
            timestamp=now,
            side=Side.SELL,
            outcome=Outcome.YES,
            price=0.54,
            size=100.0,
            taker=f"0x{'b' * 40}",
        ))

    signal = signal_gen.generate("test", trades, now=now)
    assert signal.value > 0, "Buy-heavy flow should produce positive signal"
    assert 0 < signal.confidence <= 1.0
    print(f"  Orderflow signal: value={signal.value:.4f}, conf={signal.confidence:.4f}")

    # Insufficient trades
    signal = signal_gen.generate("test", trades[:2], now=now)
    assert signal.confidence < 0.2, "Low confidence with few trades"
    print(f"  Orderflow low data: value={signal.value:.4f}, conf={signal.confidence:.4f}")

    print("✓ Orderflow signal tests passed")


def test_ai_probability_signal():
    """Test AI probability signal generation."""
    ai_signal = AIProbabilitySignal(seed=42)

    market = Market(
        condition_id="test_market",
        question="Will BTC exceed $100K?",
        slug="btc-100k",
        outcomes=["Yes", "No"],
        outcome_prices=[0.45, 0.55],
        volume=1000000,
        liquidity=50000,
    )

    # Test with true probability (backtest mode)
    signal = ai_signal.generate(market, true_probability=0.65)
    assert signal.value > 0, "Should be bullish when true prob > market price"
    print(f"  AI signal (true=0.65, market=0.45): value={signal.value:.4f}")

    # Test without true probability (simulation mode)
    signal = ai_signal.generate(market, historical_prices=[0.4, 0.42, 0.44, 0.45])
    assert -1 <= signal.value <= 1
    print(f"  AI signal (simulation): value={signal.value:.4f}")

    # Test calibration scoring
    predictions = [(0.7, 1.0), (0.3, 0.0), (0.8, 1.0), (0.2, 1.0)]
    cal = ai_signal.calibration_score(predictions)
    assert 0 <= cal["brier_score"] <= 1
    print(f"  Calibration: brier={cal['brier_score']:.4f}")

    print("✓ AI probability signal tests passed")


def test_momentum_signal():
    """Test momentum signal generation."""
    mom = MomentumSignal()

    # Uptrend
    prices = [0.40 + i * 0.01 for i in range(20)]
    signal = mom.generate("test", prices)
    assert signal.value > 0, "Uptrend should produce positive momentum"
    print(f"  Momentum uptrend: value={signal.value:.4f}")

    # Downtrend
    prices = [0.60 - i * 0.01 for i in range(20)]
    signal = mom.generate("test", prices)
    assert signal.value < 0, "Downtrend should produce negative momentum"
    print(f"  Momentum downtrend: value={signal.value:.4f}")

    # Flat
    prices = [0.50 + np.random.normal(0, 0.001) for _ in range(20)]
    signal = mom.generate("test", prices)
    assert abs(signal.value) < 0.5, "Flat market should have weak momentum"
    print(f"  Momentum flat: value={signal.value:.4f}")

    print("✓ Momentum signal tests passed")


def test_signal_aggregator():
    """Test signal aggregation."""
    agg = SignalAggregator()
    now = datetime.now(timezone.utc)

    # All signals agree (bullish)
    signals = [
        Signal(market_id="test", timestamp=now, name="orderflow", value=0.6, confidence=0.7),
        Signal(market_id="test", timestamp=now, name="ai_probability", value=0.5, confidence=0.8),
        Signal(market_id="test", timestamp=now, name="momentum", value=0.4, confidence=0.6),
    ]
    composite = agg.aggregate(signals)
    assert composite.value > 0, "All bullish signals should produce bullish composite"
    assert composite.confidence > 0.5, "Agreement should boost confidence"
    print(f"  Aggregated (agree): value={composite.value:.4f}, conf={composite.confidence:.4f}")

    # Mixed signals
    signals[2] = Signal(market_id="test", timestamp=now, name="momentum", value=-0.3, confidence=0.6)
    composite = agg.aggregate(signals)
    print(f"  Aggregated (mixed): value={composite.value:.4f}, conf={composite.confidence:.4f}")

    print("✓ Signal aggregator tests passed")


def test_risk_manager():
    """Test risk management."""
    rm = RiskManager(
        max_position_pct=0.10,
        max_portfolio_exposure=0.50,
        stop_loss_pct=0.25,
        max_drawdown_pct=0.20,
    )

    now = datetime.now(timezone.utc)
    positions = {}
    bankroll = 10000

    # Trade should be allowed when empty
    from src.data.models import TradeDecision
    decision = TradeDecision(
        market_id="test", timestamp=now, action="BUY_YES",
        size=500, target_price=0.5, edge=0.1,
    )
    allowed, reason, size = rm.check_new_trade(decision, positions, bankroll, now)
    assert allowed, f"Should allow first trade, got: {reason}"
    print(f"  First trade: allowed={allowed}, size={size:.0f}")

    # Test drawdown halt
    rm.update_equity(10000)
    rm.update_equity(7500)  # 25% drawdown
    assert rm._halted, "Should halt at 25% drawdown (limit=20%)"
    
    allowed, reason, _ = rm.check_new_trade(decision, positions, bankroll, now)
    assert not allowed, "Should block trades when halted"
    print(f"  Halted trade: allowed={allowed}, reason={reason}")

    print("✓ Risk manager tests passed")


def test_backtest_engine():
    """Test full backtest execution."""
    config = Config()
    engine = BacktestEngine(config)

    result = engine.run(n_markets=10, duration_days=14)

    assert result.total_trades > 0, "Should execute some trades"
    assert len(result.equity_curve) > 1, "Should have equity history"
    assert result.max_drawdown_pct >= 0, "Drawdown should be non-negative"
    assert 0 <= result.win_rate <= 1, "Win rate should be between 0 and 1"

    print(f"  Backtest: {result.total_trades} trades, return={result.total_return_pct:.2%}")
    print(f"  Sharpe={result.sharpe_ratio:.3f}, WinRate={result.win_rate:.2%}")
    print(f"  MaxDD={result.max_drawdown_pct:.2%}")

    print("✓ Backtest engine tests passed")


def test_config_loading():
    """Test configuration loading."""
    config = Config()
    assert config.strategy.kelly_fraction == 0.5
    assert config.backtest.initial_bankroll == 10000
    print(f"  Default config: kelly={config.strategy.kelly_fraction}")

    # Test from dict
    config = Config.from_dict({
        "strategy": {"kelly_fraction": 0.3},
        "risk": {"stop_loss_pct": 0.30},
    })
    assert config.strategy.kelly_fraction == 0.3
    assert config.risk.stop_loss_pct == 0.30
    print(f"  Custom config: kelly={config.strategy.kelly_fraction}")

    print("✓ Config tests passed")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  ORDERFLOW-ALPHA TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_config_loading,
        test_kelly_sizer,
        test_orderflow_signal,
        test_ai_probability_signal,
        test_momentum_signal,
        test_signal_aggregator,
        test_risk_manager,
        test_backtest_engine,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n▶ {test.__name__}")
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print(f"{'=' * 60}\n")

    sys.exit(1 if failed > 0 else 0)

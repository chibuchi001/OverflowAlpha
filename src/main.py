"""
orderflow-alpha — Main entry point

Usage:
    python -m src.main --mode backtest
    python -m src.main --mode paper
    python -m src.main --mode sensitivity
    python -m src.main --mode all
"""

import argparse
import json
import sys
import time

from .backtest.engine import BacktestEngine
from .utils.config import load_config
from .utils.logger import get_logger

logger = get_logger("main")


def run_backtest(config_path: str = "config.yaml"):
    """Run the backtesting engine and output results."""
    config = load_config(config_path)
    engine = BacktestEngine(config)

    logger.info("Starting backtest...")
    result = engine.run(n_markets=30, duration_days=30)

    with open("backtest_results.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)

    logger.info("Results saved to backtest_results.json")
    print(result.summary())
    return result


def run_paper(config_path: str = "config.yaml"):
    """Run paper trading demo."""
    config = load_config(config_path)

    from .live import PaperTradingEngine
    engine = PaperTradingEngine(config)

    logger.info("Starting paper trading demo...")
    result = engine.run_demo(n_ticks=50, tick_interval_seconds=0.05, n_markets=5)

    with open("paper_trading_results.json", "w") as f:
        json.dump(result, f, indent=2, default=str)

    logger.info(f"Paper trading complete: {result['summary']['total_trades']} trades")
    logger.info(f"Return: {result['summary']['total_return_pct']:.2%}")
    logger.info("Results saved to paper_trading_results.json")
    return result


def run_sensitivity(config_path: str = "config.yaml"):
    """Run parameter sensitivity analysis."""
    from .analysis import ParameterSensitivityAnalyzer

    logger.info("Starting parameter sensitivity analysis...")
    analyzer = ParameterSensitivityAnalyzer(n_markets=20, duration_days=25, seed=42)
    result = analyzer.run_grid_search()

    with open("sensitivity_results.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)

    logger.info("Results saved to sensitivity_results.json")
    print(result.summary())
    return result


def run_all(config_path: str = "config.yaml"):
    """Run all analysis modes."""
    print("\n" + "=" * 60)
    print("  ORDERFLOW-ALPHA — FULL ANALYSIS SUITE")
    print("=" * 60)

    start = time.time()

    print("\n[1/3] Running backtest...")
    bt = run_backtest(config_path)

    print("\n[2/3] Running paper trading demo...")
    pt = run_paper(config_path)

    print("\n[3/3] Running parameter sensitivity analysis...")
    sa = run_sensitivity(config_path)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  All analyses complete in {elapsed:.1f}s")
    print(f"  Output files:")
    print(f"    - backtest_results.json")
    print(f"    - paper_trading_results.json")
    print(f"    - sensitivity_results.json")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="orderflow-alpha trading system")
    parser.add_argument(
        "--mode",
        choices=["backtest", "paper", "sensitivity", "all"],
        default="backtest",
        help="Run mode",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file",
    )
    args = parser.parse_args()

    modes = {
        "backtest": run_backtest,
        "paper": run_paper,
        "sensitivity": run_sensitivity,
        "all": run_all,
    }

    modes[args.mode](args.config)


if __name__ == "__main__":
    main()

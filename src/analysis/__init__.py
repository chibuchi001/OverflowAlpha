"""
Parameter Sensitivity Analysis

Runs the backtest engine across a grid of strategy parameters
to identify optimal configurations and demonstrate robustness.

Produces:
- Sharpe ratio heatmaps across parameter pairs
- Sensitivity curves for individual parameters
- Optimal parameter identification
- Robustness metrics (how much performance varies)
"""

from __future__ import annotations

import json
import itertools
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..backtest.engine import BacktestEngine, BacktestResult
from ..backtest.simulator import MarketSimulator
from ..utils.config import Config, StrategyConfig, SignalConfig, RiskConfig, BacktestConfig
from ..utils.logger import get_logger

logger = get_logger("analysis.sensitivity")


@dataclass
class SensitivityResult:
    """Results from parameter sensitivity analysis."""

    # Grid results: list of {params: {...}, metrics: {...}}
    grid_results: list[dict] = field(default_factory=list)

    # Best configurations
    best_sharpe: dict = field(default_factory=dict)
    best_return: dict = field(default_factory=dict)
    best_risk_adj: dict = field(default_factory=dict)

    # Summary stats
    avg_sharpe: float = 0.0
    std_sharpe: float = 0.0
    avg_return: float = 0.0
    pct_profitable: float = 0.0

    # Heatmap data (for dashboard)
    heatmap_kelly_vs_edge: list[list[float]] = field(default_factory=list)
    heatmap_labels_x: list[str] = field(default_factory=list)
    heatmap_labels_y: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "grid_results": self.grid_results,
            "best_sharpe": self.best_sharpe,
            "best_return": self.best_return,
            "best_risk_adj": self.best_risk_adj,
            "summary": {
                "avg_sharpe": round(self.avg_sharpe, 4),
                "std_sharpe": round(self.std_sharpe, 4),
                "avg_return": round(self.avg_return, 4),
                "pct_profitable": round(self.pct_profitable, 4),
                "total_configs": len(self.grid_results),
            },
            "heatmap": {
                "data": self.heatmap_kelly_vs_edge,
                "x_labels": self.heatmap_labels_x,
                "y_labels": self.heatmap_labels_y,
            },
        }

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "  PARAMETER SENSITIVITY ANALYSIS",
            "=" * 60,
            "",
            f"  Configurations tested:  {len(self.grid_results)}",
            f"  Avg Sharpe Ratio:       {self.avg_sharpe:.3f} ± {self.std_sharpe:.3f}",
            f"  Avg Return:             {self.avg_return:.2%}",
            f"  % Profitable:           {self.pct_profitable:.1%}",
            "",
            "  ── Best by Sharpe ────────────────────",
        ]
        if self.best_sharpe:
            lines.append(f"  Sharpe: {self.best_sharpe['metrics']['sharpe_ratio']:.3f}")
            lines.append(f"  Params: {json.dumps(self.best_sharpe['params'], indent=None)}")
        lines += [
            "",
            "  ── Best by Return ────────────────────",
        ]
        if self.best_return:
            lines.append(f"  Return: {self.best_return['metrics']['total_return_pct']:.2%}")
            lines.append(f"  Params: {json.dumps(self.best_return['params'], indent=None)}")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


class ParameterSensitivityAnalyzer:
    """
    Runs grid search across strategy parameters.
    """

    def __init__(
        self,
        n_markets: int = 20,
        duration_days: int = 30,
        seed: int = 42,
    ):
        self.n_markets = n_markets
        self.duration_days = duration_days
        self.seed = seed

        # Pre-generate markets once for consistent comparison
        simulator = MarketSimulator(
            n_markets=n_markets,
            duration_days=duration_days,
            seed=seed,
        )
        self.markets = simulator.generate_markets()
        logger.info(f"Pre-generated {len(self.markets)} markets for sensitivity analysis")

    def run_grid_search(
        self,
        kelly_fractions: list[float] = None,
        edge_thresholds: list[float] = None,
        max_position_pcts: list[float] = None,
        ai_weights: list[float] = None,
    ) -> SensitivityResult:
        """
        Run backtest across parameter grid.

        Default grid tests key parameters that most affect performance.
        """
        kelly_fractions = kelly_fractions or [0.15, 0.25, 0.35, 0.50, 0.65]
        edge_thresholds = edge_thresholds or [0.04, 0.06, 0.08, 0.10, 0.12]
        max_position_pcts = max_position_pcts or [0.08, 0.12]
        ai_weights = ai_weights or [0.35, 0.45, 0.55]

        total = len(kelly_fractions) * len(edge_thresholds) * len(max_position_pcts) * len(ai_weights)
        logger.info(f"Running grid search: {total} configurations")

        results = []
        count = 0

        for kelly, edge, max_pos, ai_w in itertools.product(
            kelly_fractions, edge_thresholds, max_position_pcts, ai_weights
        ):
            count += 1
            if count % 10 == 0:
                logger.info(f"Progress: {count}/{total}")

            config = Config(
                strategy=StrategyConfig(
                    kelly_fraction=kelly,
                    max_position_pct=max_pos,
                    max_portfolio_exposure=0.50,
                    min_edge_threshold=edge,
                ),
                signals=SignalConfig(
                    orderflow_weight=round((1.0 - ai_w) * 0.55, 2),
                    ai_prob_weight=ai_w,
                    momentum_weight=round((1.0 - ai_w) * 0.45, 2),
                ),
                risk=RiskConfig(
                    stop_loss_pct=0.40,
                    max_drawdown_pct=0.25,
                ),
                backtest=BacktestConfig(
                    initial_bankroll=10000,
                    fee_rate=0.002,
                    slippage_bps=10,
                ),
            )

            try:
                engine = BacktestEngine(config)
                bt_result = engine.run(markets=self.markets)

                results.append({
                    "params": {
                        "kelly_fraction": kelly,
                        "edge_threshold": edge,
                        "max_position_pct": max_pos,
                        "ai_weight": ai_w,
                    },
                    "metrics": {
                        "total_return_pct": bt_result.total_return_pct,
                        "sharpe_ratio": bt_result.sharpe_ratio,
                        "sortino_ratio": bt_result.sortino_ratio,
                        "max_drawdown_pct": bt_result.max_drawdown_pct,
                        "win_rate": bt_result.win_rate,
                        "profit_factor": bt_result.profit_factor,
                        "total_trades": bt_result.total_trades,
                    },
                })
            except Exception as e:
                logger.warning(f"Config failed: kelly={kelly} edge={edge}: {e}")
                continue

        # Analyze results
        return self._analyze_results(results, kelly_fractions, edge_thresholds)

    def _analyze_results(
        self,
        results: list[dict],
        kelly_fractions: list[float],
        edge_thresholds: list[float],
    ) -> SensitivityResult:
        """Compute summary statistics and find optimal params."""
        if not results:
            return SensitivityResult()

        sharpes = [r["metrics"]["sharpe_ratio"] for r in results]
        returns = [r["metrics"]["total_return_pct"] for r in results]

        # Best configs
        best_sharpe_idx = np.argmax(sharpes)
        best_return_idx = np.argmax(returns)

        # Risk-adjusted best: highest Sharpe with drawdown < 20%
        risk_adj = [
            (i, r["metrics"]["sharpe_ratio"])
            for i, r in enumerate(results)
            if r["metrics"]["max_drawdown_pct"] < 0.20
        ]
        best_risk_adj_idx = max(risk_adj, key=lambda x: x[1])[0] if risk_adj else best_sharpe_idx

        # Build heatmap: Kelly fraction vs Edge threshold (averaging over other params)
        heatmap = np.zeros((len(kelly_fractions), len(edge_thresholds)))
        counts = np.zeros_like(heatmap)

        for r in results:
            kelly = r["params"]["kelly_fraction"]
            edge = r["params"]["edge_threshold"]
            if kelly in kelly_fractions and edge in edge_thresholds:
                ki = kelly_fractions.index(kelly)
                ei = edge_thresholds.index(edge)
                heatmap[ki, ei] += r["metrics"]["sharpe_ratio"]
                counts[ki, ei] += 1

        # Average
        mask = counts > 0
        heatmap[mask] /= counts[mask]
        heatmap[~mask] = 0

        return SensitivityResult(
            grid_results=results,
            best_sharpe=results[best_sharpe_idx],
            best_return=results[best_return_idx],
            best_risk_adj=results[best_risk_adj_idx],
            avg_sharpe=float(np.mean(sharpes)),
            std_sharpe=float(np.std(sharpes)),
            avg_return=float(np.mean(returns)),
            pct_profitable=sum(1 for r in returns if r > 0) / len(returns),
            heatmap_kelly_vs_edge=[[round(float(v), 3) for v in row] for row in heatmap.tolist()],
            heatmap_labels_x=[f"{e:.2f}" for e in edge_thresholds],
            heatmap_labels_y=[f"{k:.2f}" for k in kelly_fractions],
        )


def run_sensitivity_analysis(
    output_path: str = "sensitivity_results.json",
) -> SensitivityResult:
    """Run the full sensitivity analysis and save results."""
    analyzer = ParameterSensitivityAnalyzer(n_markets=20, duration_days=25, seed=42)
    result = analyzer.run_grid_search()

    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)

    logger.info(f"Results saved to {output_path}")
    print(result.summary())
    return result


if __name__ == "__main__":
    run_sensitivity_analysis()

from __future__ import annotations

from project_invest.domain.models import PortfolioSnapshot, RiskLimits, StrategyGenome
from project_invest.services.risk import RiskManager


def test_risk_manager_reduces_position_size_when_needed() -> None:
    portfolio = PortfolioSnapshot.bootstrap(100000.0)
    limits = RiskLimits(
        max_risk_per_trade=0.01,
        max_daily_loss=0.03,
        max_positions=5,
        max_gross_exposure=1.0,
        max_position_pct=0.2,
        max_drawdown=0.2,
    )
    manager = RiskManager(limits)
    genome = StrategyGenome(stop_loss_pct=0.02)

    decision = manager.evaluate_entry(
        symbol="RISKY",
        portfolio=portfolio,
        price=1000.0,
        desired_quantity=1000,
        genome=genome,
    )

    assert decision.approved is True
    assert 0 < decision.allowed_quantity < 1000

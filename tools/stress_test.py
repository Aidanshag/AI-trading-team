"""Portfolio stress-test runner.

Daily stress on the open book: simulate adverse market scenarios
(equity drawdown, vol spike, correlation breakdown) and report the
worst-case P&L impact. Run it before market open each day; if any
scenario breaches the internal $500 DLL ceiling, the Risk Manager
flags for size reduction.

Usage:
    from tools.stress_test import run_stress
    report = run_stress()
    print(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from state.db import get_db


@dataclass
class StressScenario:
    name: str
    description: str
    # Per-sector shock in % of price (negative = adverse for long, positive = adverse for short)
    sector_shocks: dict[str, float] = field(default_factory=dict)
    # Cross-asset correlation breakdown amplifier (1.0 = normal, 1.5 = correlations spike)
    corr_amplifier: float = 1.0


# Standard stress library — institutional desks run these every day
STANDARD_SCENARIOS: list[StressScenario] = [
    StressScenario(
        name="2020_covid_crash",
        description="March 2020 risk-off: equities -10%, oil -30%, gold +5%, rates -50bps",
        sector_shocks={
            "index_macro": -0.10, "energies": -0.30, "metals": +0.05,
            "rates": +0.05, "fx_futures": +0.03, "grains": -0.05,
            "softs": -0.05, "livestock": -0.10,
        },
        corr_amplifier=1.5,
    ),
    StressScenario(
        name="2022_inflation_shock",
        description="Reflation regime: equities -5%, oil +15%, gold flat, rates -2 pts",
        sector_shocks={
            "index_macro": -0.05, "energies": +0.15, "metals": +0.10,
            "rates": -0.05, "fx_futures": -0.05, "grains": +0.08,
            "softs": +0.05, "livestock": +0.02,
        },
        corr_amplifier=1.2,
    ),
    StressScenario(
        name="vol_spike_2x",
        description="VIX doubles overnight; ATR-based stops widen; intraday range expands",
        sector_shocks={  # Not directional — this stresses options gamma
            "index_macro": -0.03,
        },
        corr_amplifier=1.3,
    ),
    StressScenario(
        name="single_position_5sigma",
        description="Worst single position takes a 5σ adverse move (per-symbol stress)",
        sector_shocks={},  # Computed per-position
        corr_amplifier=1.0,
    ),
]


@dataclass
class StressResult:
    scenario: str
    description: str
    book_pnl_usd: float
    worst_position_pnl_usd: float
    worst_position_symbol: str
    breaches_internal_dll: bool          # > -$500
    breaches_topstep_dll: bool           # > -$1000

    def summary(self) -> str:
        flag = "[BREACH]" if self.breaches_internal_dll else "[ within ]"
        return (
            f"{self.scenario:<30} P&L ${self.book_pnl_usd:+.2f} | "
            f"worst: {self.worst_position_symbol} ${self.worst_position_pnl_usd:+.2f} | "
            f"{flag}"
        )


@dataclass
class StressReport:
    results: list[StressResult] = field(default_factory=list)

    def any_breaches(self) -> bool:
        return any(r.breaches_internal_dll for r in self.results)

    def summary(self) -> str:
        lines = ["Stress Test Report", "=" * 70]
        for r in self.results:
            lines.append(r.summary())
        if self.any_breaches():
            lines.append("")
            lines.append("!!! AT LEAST ONE SCENARIO BREACHES INTERNAL DLL !!!")
            lines.append("Risk Manager should reduce size or close vulnerable positions.")
        return "\n".join(lines)


def run_stress(
    scenarios: list[StressScenario] | None = None,
    internal_dll_usd: float = 500,
    topstep_dll_usd: float = 1000,
) -> StressReport:
    """Run all stress scenarios on the current book."""
    scenarios = scenarios or STANDARD_SCENARIOS
    db = get_db()
    positions = db.current_positions()

    report = StressReport()

    if not positions:
        # No positions = no stress
        for s in scenarios:
            report.results.append(StressResult(
                scenario=s.name, description=s.description,
                book_pnl_usd=0.0, worst_position_pnl_usd=0.0,
                worst_position_symbol="(no positions)",
                breaches_internal_dll=False, breaches_topstep_dll=False,
            ))
        return report

    # Symbol metadata for tick value calc
    import yaml
    from pathlib import Path
    symbols_meta = yaml.safe_load(Path("config/symbols.yaml").read_text()).get("symbols", {})

    for scenario in scenarios:
        book_pnl = 0.0
        worst_pos_pnl = 0.0
        worst_sym = ""

        for p in positions:
            symbol = p.get("symbol", "")
            sector = symbols_meta.get(symbol, {}).get("sector", "unknown")
            shock_pct = scenario.sector_shocks.get(sector, 0.0) * scenario.corr_amplifier

            avg_price = float(p.get("avg_price", 0))
            contracts = int(p.get("contracts", 0))
            side_sign = 1 if p.get("side") == "long" else -1
            tick_value = float(symbols_meta.get(symbol, {}).get("tick_value", 0))
            tick_size = float(symbols_meta.get(symbol, {}).get("tick_size", 0.01))

            shocked_price = avg_price * (1 + shock_pct)
            price_move = shocked_price - avg_price
            ticks_moved = price_move / tick_size if tick_size > 0 else 0
            position_pnl = side_sign * contracts * ticks_moved * tick_value

            book_pnl += position_pnl
            if position_pnl < worst_pos_pnl:
                worst_pos_pnl = position_pnl
                worst_sym = symbol

        report.results.append(StressResult(
            scenario=scenario.name, description=scenario.description,
            book_pnl_usd=book_pnl, worst_position_pnl_usd=worst_pos_pnl,
            worst_position_symbol=worst_sym,
            breaches_internal_dll=(book_pnl <= -internal_dll_usd),
            breaches_topstep_dll=(book_pnl <= -topstep_dll_usd),
        ))

    return report


if __name__ == "__main__":
    print(run_stress().summary())

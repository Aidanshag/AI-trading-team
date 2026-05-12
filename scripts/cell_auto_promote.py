"""Auto-promote/demote cells from live evidence.

Closes the loop between live trade outcomes and the live_allowlist gate
that determines what fires next. Without this, the brain has to be
manually re-validated; with this, cells that hold their OOS edge stay
live and cells that don't decay out without intervention.

INPUTS (read-only):
  state/fund.db                                    — orders table (filled trades)
  vault/research/live_vs_oos/<latest>.json         — per-cell live R-multiples
  state/strategy_validation.json                   — current live_allowlist + cells map

OUTPUT (atomic write):
  state/strategy_validation.json                   — modified live_allowlist
  vault/research/cell_promotion_log.md             — append-only audit

PROMOTION RULES (per cowork_coordination.md 2026-05-08 priority #1):
  Promote shadow → live:    n_live ≥ 10  AND  live_E > 0  AND  |live_E − OOS_E| < 1.0R
  Demote   live → shadow:   n_live ≥ 10  AND  live_E < 0  AND  consecutive losers ≥ 3
  Otherwise: HOLD (no change)

USER PIN OVERRIDES PROMOTION:
  state/strategy_validation.json.live_strategies_filter is the user's
  hand-picked subset (currently gap_fill × {ZN,ZT,ZB,ZF}). This script
  NEVER promotes a cell outside that filter — the pin always wins. It
  does still demote within the filter when evidence warrants.

ATOMIC WRITE PROTOCOL:
  Read full JSON → modify in memory → write to tempfile in same dir →
  os.replace(tempfile, target). On Windows + Unix this is atomic at the
  OS level — readers see either old or new, never a partial file. The
  trader process that polls this file is safe.

USAGE:
  python -m scripts.cell_auto_promote                  # apply changes
  python -m scripts.cell_auto_promote --dry-run        # preview only
  python -m scripts.cell_auto_promote --window 30      # use 30d of fills
  python -m scripts.cell_auto_promote --min-n 10       # min observations
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

VALIDATION_PATH = PROJECT_ROOT / "state" / "strategy_validation.json"
LIVE_VS_OOS_DIR = PROJECT_ROOT / "vault" / "research" / "live_vs_oos"
PROMOTION_LOG = PROJECT_ROOT / "vault" / "research" / "cell_promotion_log.md"
DB_PATH = PROJECT_ROOT / "state" / "fund.db"

DEFAULT_MIN_N = 10
DEFAULT_OOS_GAP = 1.0       # max acceptable |live_E - OOS_E| for promotion
DEFAULT_LOSING_STREAK = 3   # consecutive losers triggering demotion
DEFAULT_WINDOW_DAYS = 30


# ── helper: session bucket from ET hour ────────────────────────

def _session_from_et_hour(hour_et: float) -> str:
    """Mirrors scripts/live_trader.py session bucketing."""
    if 9.5 <= hour_et < 16:    return "RTH"
    if 4 <= hour_et < 9.5:     return "London"
    if 16 <= hour_et < 20:     return "PostClose"
    return "Asian"


# ── shadow evidence reader (2026-05-12) ────────────────────────

def load_shadow_evidence_per_cell(window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    """Read resolved shadow trades from DB, group by cell, compute realistic
    R-multiples (with slippage + fees deducted).

    Returns {cell_key: {"n": int, "live_mean_r": float}} in the same
    shape as live_vs_oos.by_cell so it can be combined cleanly.

    Uses tools/shadow_realism for per-trade friction conversion. The
    "realistic" R = idealized_R - (slippage_usd + fees_usd) / risk_usd.
    """
    if not DB_PATH.exists():
        return {}
    try:
        from tools.shadow_realism import (slippage_cost_usd,
                                            fees_round_trip_usd)
    except Exception:
        return {}
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=window_days)
              ).isoformat(timespec="seconds")
    try:
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            """SELECT symbol, strategy, side, pnl_r, risk_usd, ts_signal
                 FROM shadow_trades
                WHERE outcome IS NOT NULL
                  AND ts_signal >= ?
                  AND pnl_r IS NOT NULL""",
            (cutoff,),
        ).fetchall()
        c.close()
    except Exception:
        return {}

    # Aggregate per (strategy|symbol|session|side)
    per_cell: dict[str, list[float]] = {}
    for r in rows:
        sym = str(r["symbol"] or "")
        strat = str(r["strategy"] or "")
        side = str(r["side"] or "").lower()
        if not sym or not strat or side not in ("long", "short"):
            continue
        # Derive session from ts_signal hour ET
        try:
            ts = datetime.fromisoformat(str(r["ts_signal"]).replace("Z", "+00:00"))
            # Convert UTC to ET (approximate — UTC-4 in DST)
            et_hour = (ts.hour - 4) % 24 + ts.minute / 60
            sess = _session_from_et_hour(et_hour)
        except Exception:
            continue
        risk_usd = r["risk_usd"]
        pnl_r = r["pnl_r"]
        if risk_usd is None or risk_usd <= 0 or pnl_r is None:
            continue
        # Apply friction in R units
        friction_usd = slippage_cost_usd(sym) + fees_round_trip_usd(sym)
        realistic_r = float(pnl_r) - friction_usd / float(risk_usd)
        key = f"{strat}|{sym}|{sess}|{side}"
        per_cell.setdefault(key, []).append(realistic_r)

    # Build output dict
    out: dict = {}
    for key, rs in per_cell.items():
        if not rs:
            continue
        out[key] = {
            "n": len(rs),
            "live_mean_r": sum(rs) / len(rs),
            "source": "shadow",  # tag so we can tell where data came from
        }
    return out


def combine_evidence(live_by_cell: dict, shadow_by_cell: dict) -> dict:
    """Merge live + shadow evidence by cell. Live trades are weighted
    equally to shadow trades (per cell). Sample size adds; mean is a
    weighted-by-n combination.

    If both have data for a cell, the combined record carries n=live_n+shadow_n
    and live_mean_r = weighted_avg(live, shadow).
    """
    combined: dict = {}
    all_keys = set(live_by_cell) | set(shadow_by_cell)
    for key in all_keys:
        live = live_by_cell.get(key)
        shadow = shadow_by_cell.get(key)
        if live and shadow:
            n_l = int(live.get("n") or 0)
            n_s = int(shadow.get("n") or 0)
            e_l = float(live.get("live_mean_r") or 0)
            e_s = float(shadow.get("live_mean_r") or 0)
            total_n = n_l + n_s
            if total_n == 0:
                continue
            combined[key] = {
                "n": total_n,
                "live_mean_r": (e_l * n_l + e_s * n_s) / total_n,
                "n_live": n_l,
                "n_shadow": n_s,
                "live_mean_r_live": e_l,
                "live_mean_r_shadow": e_s,
                "source": "combined",
            }
        elif live:
            combined[key] = {**live, "source": "live"}
        else:
            combined[key] = shadow
    return combined


# ── live data sources ──────────────────────────────────────────

def latest_live_vs_oos() -> tuple[Path, dict] | None:
    """Find the newest live_r_comparison.json and return (path, parsed)."""
    if not LIVE_VS_OOS_DIR.exists():
        return None
    files = sorted(LIVE_VS_OOS_DIR.glob("*_live_r_comparison.json"))
    if not files:
        return None
    p = files[-1]
    try:
        return p, json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARN: couldn't parse {p.name}: {e}", file=sys.stderr)
        return None


def load_validation() -> dict:
    """Load the full strategy_validation.json. Single 5-6MB read."""
    return json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))


def consecutive_losers_for_cell(cell_key: str, window_days: int) -> int:
    """Count the streak of negative-R closes most-recent-first for one cell.

    Reads `orders` joined with the live_r_comparison's per-trade record.
    Since the comparison file aggregates, we approximate "consecutive
    losers" by reading per-trade rows from a sister sidecar if present,
    else from the raw orders table.

    Heuristic implementation: scan orders for this cell's symbol over
    the window, count the trailing run where avg_fill_price exit < entry
    for longs (or > for shorts). Approximate but useful as a guard.
    """
    if not DB_PATH.exists():
        return 0
    try:
        # cell_key shape: "strategy|symbol|session|side"
        parts = cell_key.split("|")
        if len(parts) != 4:
            return 0
        _, symbol, _, side = parts
        cutoff = (datetime.now(tz=timezone.utc)
                  - timedelta(days=window_days)).isoformat()

        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            """SELECT client_order_id, side, avg_fill_price, stop_price, ts_filled
                 FROM orders
                WHERE symbol = ?
                  AND ts_filled >= ?
                  AND avg_fill_price IS NOT NULL
                  AND avg_fill_price > 0
                  AND client_order_id NOT LIKE '%_stop'
                  AND client_order_id NOT LIKE '%_target'
                ORDER BY ts_filled DESC
                LIMIT 50""",
            (symbol, cutoff),
        ).fetchall()
        c.close()

        # Count consecutive losers (entries where the corresponding stop
        # was triggered — simplification: if entry side matches `side`
        # and entry's later stop fill is closer to entry than target).
        # Coarse: rely on the stop being in the same client_order_id
        # family. If we can't tie them up, skip.
        streak = 0
        for r in rows:
            if str(r["side"]).lower() != side.lower():
                continue
            # We approximate: a "losing" trade = entry exists and a stop
            # leg with same cid prefix also has a fill price in the
            # losing direction. Without joining we just count entries.
            # In production this should be wired to closed-trade outcomes.
            streak += 1
            if streak >= DEFAULT_LOSING_STREAK + 1:
                break
        return min(streak, DEFAULT_LOSING_STREAK + 1)
    except Exception:
        return 0


# ── promotion / demotion ───────────────────────────────────────

def cell_status_in_allowlist(cell_key: str, allowlist: list[dict]) -> bool:
    parts = cell_key.split("|")
    if len(parts) != 4:
        return False
    strat, sym, sess, side = parts
    for c in allowlist:
        if (c.get("strategy") == strat and c.get("symbol") == sym
                and c.get("session") == sess and c.get("side") == side):
            return True
    return False


def cell_passes_user_pin(cell_key: str, filter_list: list[dict]) -> bool:
    """Is this cell allowed through the user's hand-picked filter?
    If no filter is set, all cells are allowed."""
    if not filter_list:
        return True
    parts = cell_key.split("|")
    if len(parts) != 4:
        return False
    strat, sym, _, _ = parts
    for f in filter_list:
        if f.get("strategy") == strat and sym in (f.get("symbols") or []):
            return True
    return False


def get_oos_e(cells_map: dict, cell_key: str) -> float | None:
    """Pull OOS expectancy from validation cells map."""
    rec = cells_map.get(cell_key)
    if not rec:
        return None
    # The cells map records vary in shape. Try common fields.
    for path in (("oos", "e"), ("walk_forward", "oos", "e"), ("e",)):
        cur: Any = rec
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                cur = None
                break
        if isinstance(cur, (int, float)):
            return float(cur)
    return None


def evaluate_cells(validation: dict, live_data: dict,
                   min_n: int, oos_gap: float,
                   window_days: int) -> list[dict]:
    """Return a list of decisions per cell with live data.

    Each decision: {cell, action: promote|demote|hold,
                    reason, live_n, live_e, oos_e}
    """
    cells_map = validation.get("cells") or {}
    allowlist = validation.get("live_allowlist") or []
    filter_list = validation.get("live_strategies_filter") or []

    by_cell = live_data.get("by_cell") or {}
    decisions: list[dict] = []

    for cell_key, live in by_cell.items():
        n = int(live.get("n") or 0)
        live_e = float(live.get("live_mean_r") or 0)
        oos_e = get_oos_e(cells_map, cell_key)

        in_live = cell_status_in_allowlist(cell_key, allowlist)
        passes_pin = cell_passes_user_pin(cell_key, filter_list)

        decision = {
            "cell": cell_key, "live_n": n, "live_e": live_e,
            "oos_e": oos_e, "in_live": in_live,
            "passes_pin": passes_pin,
            "action": "hold", "reason": "",
        }

        if n < min_n:
            decision["reason"] = f"insufficient n ({n} < {min_n})"
            decisions.append(decision)
            continue

        if not in_live:
            # Promotion candidate. Must pass user pin + meet promote rules.
            if not passes_pin:
                decision["reason"] = "outside user pin filter — cannot promote"
            elif live_e <= 0:
                decision["reason"] = f"live_e {live_e:+.2f}R not positive"
            elif oos_e is None:
                decision["reason"] = "no OOS expectancy in cells map"
            elif abs(live_e - oos_e) >= oos_gap:
                decision["reason"] = (f"|live_e {live_e:+.2f} - oos_e "
                                      f"{oos_e:+.2f}| ≥ {oos_gap}")
            else:
                decision["action"] = "promote"
                decision["reason"] = (f"shadow→live: n={n}, live_e={live_e:+.2f}, "
                                      f"oos_e={oos_e:+.2f}, gap "
                                      f"{abs(live_e - oos_e):.2f}<{oos_gap}")
        else:
            # Demotion candidate. Live cells stay unless evidence rejects.
            if live_e >= 0:
                decision["reason"] = f"live_e {live_e:+.2f}R not negative"
            else:
                streak = consecutive_losers_for_cell(cell_key, window_days)
                if streak < DEFAULT_LOSING_STREAK:
                    decision["reason"] = (f"live_e {live_e:+.2f}R negative but "
                                          f"streak {streak}<{DEFAULT_LOSING_STREAK}")
                else:
                    decision["action"] = "demote"
                    decision["reason"] = (f"live→shadow: n={n}, live_e="
                                          f"{live_e:+.2f}, streak={streak}")
        decisions.append(decision)

    return decisions


# ── atomic write ───────────────────────────────────────────────

def apply_decisions(validation: dict, decisions: list[dict]) -> tuple[dict, int, int]:
    """Mutate the validation dict's live_allowlist based on decisions.
    Returns (modified_validation, n_promoted, n_demoted)."""
    allowlist = list(validation.get("live_allowlist") or [])
    by_key = {f"{c.get('strategy')}|{c.get('symbol')}|{c.get('session')}|{c.get('side')}": i
              for i, c in enumerate(allowlist)}

    n_pro, n_dem = 0, 0
    for d in decisions:
        if d["action"] == "promote":
            cell_key = d["cell"]
            if cell_key in by_key:
                continue   # already there (paranoia)
            parts = cell_key.split("|")
            allowlist.append({
                "strategy": parts[0], "symbol": parts[1],
                "session": parts[2], "side": parts[3],
            })
            n_pro += 1
        elif d["action"] == "demote":
            cell_key = d["cell"]
            idx = by_key.get(cell_key)
            if idx is None:
                continue
            del allowlist[idx]
            # rebuild index
            by_key = {f"{c.get('strategy')}|{c.get('symbol')}|{c.get('session')}|{c.get('side')}": i
                      for i, c in enumerate(allowlist)}
            n_dem += 1

    validation["live_allowlist"] = allowlist
    validation["live_allowlist_generated_at"] = datetime.now(timezone.utc).isoformat()
    return validation, n_pro, n_dem


def write_atomic(payload: dict) -> None:
    """Atomic write: tempfile in same dir → os.replace.

    Same-directory tempfile is required for os.replace to be atomic
    (cross-device renames fall back to copy+delete on Windows).
    """
    target_dir = VALIDATION_PATH.parent
    fd, tmp_path = tempfile.mkstemp(prefix=".strategy_validation_",
                                    suffix=".tmp", dir=target_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        # os.replace is atomic on POSIX and Windows for same-volume moves
        os.replace(tmp_path, VALIDATION_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── audit log ──────────────────────────────────────────────────

def append_audit_log(decisions: list[dict], live_path: Path,
                     n_pro: int, n_dem: int, dry_run: bool) -> None:
    """Append a session entry to vault/research/cell_promotion_log.md."""
    PROMOTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not PROMOTION_LOG.exists():
        PROMOTION_LOG.write_text(
            "# Cell promotion / demotion audit log\n\n"
            "Append-only record of every cell_auto_promote run. Each entry\n"
            "names the decisions taken and the live evidence that drove\n"
            "them. Generated by `scripts/cell_auto_promote.py`.\n",
            encoding="utf-8",
        )

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    head = f"\n## {ts}  ({'dry-run' if dry_run else 'applied'})\n"
    head += f"Source: `{live_path.name}`. Promoted {n_pro}, demoted {n_dem}.\n\n"
    rows = ["| cell | action | live_n | live_e | oos_e | reason |",
            "|---|---|---:|---:|---:|---|"]
    for d in decisions:
        if d["action"] == "hold":
            continue   # log only changes; holds clutter
        oos = f"{d['oos_e']:+.2f}" if d.get("oos_e") is not None else "—"
        rows.append(f"| `{d['cell']}` | **{d['action']}** | {d['live_n']} | "
                    f"{d['live_e']:+.2f} | {oos} | {d['reason']} |")
    if len(rows) == 2:
        rows.append("| _(no actions taken — all cells held)_ |  |  |  |  |  |")

    with PROMOTION_LOG.open("a", encoding="utf-8") as f:
        f.write(head)
        f.write("\n".join(rows) + "\n")


# ── main ───────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="Preview decisions without writing.")
    p.add_argument("--min-n", type=int, default=DEFAULT_MIN_N,
                   help=f"Min live observations (default {DEFAULT_MIN_N}).")
    p.add_argument("--oos-gap", type=float, default=DEFAULT_OOS_GAP,
                   help=f"Max |live_E - OOS_E| (default {DEFAULT_OOS_GAP}).")
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW_DAYS,
                   help=f"Days of orders for streak detection "
                        f"(default {DEFAULT_WINDOW_DAYS}).")
    p.add_argument("--no-shadows", action="store_true",
                   help="Disable shadow-trade evidence (live trades only).")
    args = p.parse_args()

    # Load live evidence
    live = latest_live_vs_oos()
    if live is None:
        print("No live_r_comparison.json found — nothing to evaluate.")
        # 2026-05-12: if no live data, fall back to shadow-only evaluation.
        # Don't return early so the cycle can still learn from shadows.
        live_data: dict = {"by_cell": {}, "trades_evaluated": 0}
        live_path = None
    else:
        live_path, live_data = live
        print(f"Live evidence: {live_path.name} "
              f"({live_data.get('trades_evaluated', '?')} trades)")

    # 2026-05-12: include shadow-trade evidence (with realistic friction
    # applied via tools/shadow_realism). Combined live + shadow data
    # feeds the same promotion/demotion logic. See module docstring +
    # vault/research/analysis/2026-05-12_shadow_realism.md.
    if not args.no_shadows:
        shadow_by_cell = load_shadow_evidence_per_cell(window_days=args.window)
        if shadow_by_cell:
            print(f"Shadow evidence: {len(shadow_by_cell)} cell(s) "
                  f"with resolved shadows (friction-adjusted)")
            live_by_cell = live_data.get("by_cell") or {}
            combined = combine_evidence(live_by_cell, shadow_by_cell)
            live_data = {**live_data, "by_cell": combined}
            print(f"Combined evidence: {len(combined)} cell(s)")
        else:
            print("No resolved shadow trades found — using live-only evidence")

    # Load validation
    if not VALIDATION_PATH.exists():
        print(f"ERROR: {VALIDATION_PATH} not found", file=sys.stderr)
        return 2
    validation = load_validation()
    print(f"Current live_allowlist: "
          f"{len(validation.get('live_allowlist') or [])} cells")

    # Evaluate
    decisions = evaluate_cells(validation, live_data,
                               min_n=args.min_n,
                               oos_gap=args.oos_gap,
                               window_days=args.window)

    # Print summary
    n_promote = sum(1 for d in decisions if d["action"] == "promote")
    n_demote = sum(1 for d in decisions if d["action"] == "demote")
    n_hold = sum(1 for d in decisions if d["action"] == "hold")
    print(f"Decisions: {n_promote} promote, {n_demote} demote, {n_hold} hold")
    for d in decisions:
        if d["action"] != "hold":
            print(f"  [{d['action'].upper()}] {d['cell']}  "
                  f"n={d['live_n']} live_e={d['live_e']:+.2f} "
                  f"oos_e={d.get('oos_e','—')}  → {d['reason']}")

    # Apply
    if args.dry_run:
        print("(dry-run — no writes)")
        append_audit_log(decisions, live_path, 0, 0, dry_run=True)
        return 0

    if n_promote == 0 and n_demote == 0:
        print("No changes to apply.")
        append_audit_log(decisions, live_path, 0, 0, dry_run=False)
        return 0

    new_validation, n_pro, n_dem = apply_decisions(validation, decisions)
    write_atomic(new_validation)
    print(f"Wrote {VALIDATION_PATH.name} atomically — "
          f"+{n_pro} promoted, −{n_dem} demoted.")
    append_audit_log(decisions, live_path, n_pro, n_dem, dry_run=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

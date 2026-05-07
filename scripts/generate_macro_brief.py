"""Generate a daily macro brief by combining the structural fetcher outputs:

  vault/_meta/macro_levels.json              (FRED levels)
  vault/economic_calendar/treasury_auctions.json
  vault/economic_calendar/fed_speakers.json
  vault/economic_calendar/today.json         (existing high-impact calendar)

Writes:
  vault/_meta/macro_brief_<YYYY-MM-DD>.md

This is the document the CIO and Risk Manager read on first wake. Per the
team.md convention, anything in vault/_meta/ flagged read_on_first_wake
is loaded into the agent preamble.

USAGE:
  python -m scripts.generate_macro_brief                # uses today UTC
  python -m scripts.generate_macro_brief --date 2026-05-07
  python -m scripts.generate_macro_brief --refresh      # re-runs fetchers first

To run the FULL pipeline (fetch + generate), use --refresh. Otherwise this
script just composes from whatever fetcher outputs already exist.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  warn: failed to read {path.name}: {e}", file=sys.stderr)
        return None


def run_fetchers() -> None:
    """Run all three fetcher scripts in order. Errors are non-fatal —
    the brief generator falls back to whatever data already exists."""
    for mod in ("fetch_fred_macro_levels",
                "fetch_treasury_auctions",
                "fetch_fed_speakers"):
        print(f"  refreshing: scripts.{mod}")
        try:
            subprocess.run([sys.executable, "-m", f"scripts.{mod}"],
                           check=False, timeout=120)
        except Exception as e:
            print(f"    failed: {e}", file=sys.stderr)


def section_levels(macro: dict | None) -> list[str]:
    L = ["## Headline market levels"]
    if not macro or not macro.get("series"):
        return L + ["", "_(no FRED data — run `scripts.fetch_fred_macro_levels`)_", ""]
    L += ["", "| Series | Label | Level | Δ 5d | Δ 20d |",
          "|---|---|---:|---:|---:|"]
    for s in macro["series"]:
        if s.get("level") is None:
            continue
        d5 = f"{s['delta_5d']:+.3f}" if s.get("delta_5d") is not None else "—"
        d20 = f"{s['delta_20d']:+.3f}" if s.get("delta_20d") is not None else "—"
        unit = s.get("unit", "")
        suf = f" {unit}" if unit else ""
        L.append(f"| {s['series']} | {s.get('label','')} | "
                 f"{s['level']:.3f}{suf} | {d5} | {d20} |")
    return L + [""]


def section_auctions(auct: dict | None, days: int = 10) -> list[str]:
    L = ["## Treasury auctions — next {} days".format(days)]
    if not auct or not auct.get("auctions"):
        return L + ["", "_(no auction data — run `scripts.fetch_treasury_auctions`)_", ""]
    today = datetime.now(tz=timezone.utc).date()
    upcoming = []
    for r in auct["auctions"]:
        try:
            ad = datetime.fromisoformat(r["auction_date"]).date()
        except Exception:
            continue
        if 0 <= (ad - today).days <= days:
            upcoming.append(r)
    if not upcoming:
        return L + ["", "_(none in window)_", ""]
    L += ["",
          "| Date | Type | Term | Amt ($B) | Affects |",
          "|---|---|---|---:|---|"]
    for r in upcoming:
        amt = (r.get("offering_amt_usd") or 0) / 1e9
        futs = ", ".join(r.get("affected_futures") or []) or "—"
        L.append(f"| {r['auction_date']} | {r['security_type']} | "
                 f"{r['security_term']} | {amt:.1f} | {futs} |")
    return L + [""]


def section_speakers(spk: dict | None) -> list[str]:
    L = ["## Fed speakers — upcoming"]
    if not spk or not spk.get("events"):
        return L + ["", "_(no speaker data — run `scripts.fetch_fed_speakers`)_", ""]
    high = [e for e in spk["events"] if e.get("influence") == "HIGH"]
    med = [e for e in spk["events"] if e.get("influence") == "MEDIUM"]
    L += ["", f"**HIGH influence ({len(high)})**: Chair, Vice Chair, NY Fed.",
          ""]
    if high:
        L.append("| When (UTC) | Summary |")
        L.append("|---|---|")
        for e in high[:10]:
            L.append(f"| {e['ts_utc']} | {e['summary'][:80]} |")
    L += ["", f"**MEDIUM influence ({len(med)})**: governors + regional presidents."]
    return L + [""]


def section_regime_read(macro: dict | None) -> list[str]:
    L = ["## Regime read for `gap_fill` Treasury edge", ""]
    if not macro or not macro.get("series"):
        return L + ["_(insufficient data)_", ""]

    by_id = {s["series"]: s for s in macro["series"]}
    notes = []

    dgs10 = by_id.get("DGS10", {})
    if dgs10.get("delta_5d") is not None:
        d = dgs10["delta_5d"]
        if d > 0.10:
            notes.append(f"- **10Y yield rising** ({d:+.3f}% over 5d) → "
                         "directional regime; gap_fill long fades carry "
                         "elevated extension risk. Recommend size-down.")
        elif d < -0.10:
            notes.append(f"- **10Y yield falling** ({d:+.3f}% over 5d) → "
                         "supportive for ZN/ZB long fades; cautious on "
                         "short fades into the move.")
        else:
            notes.append(f"- 10Y yield steady ({d:+.3f}% / 5d) → range "
                         "regime, which is `gap_fill`'s preferred regime.")

    fii = by_id.get("DFII10", {})
    if fii.get("delta_5d") is not None and abs(fii["delta_5d"]) > 0.10:
        notes.append(f"- **Real yield moving sharply** ({fii['delta_5d']:+.3f}% / 5d) → "
                     "demand-side shift in Treasuries; gap_fill caution.")

    vix = by_id.get("VIXCLS", {})
    if vix.get("level") is not None:
        v = vix["level"]
        if v > 25:
            notes.append(f"- **VIX elevated** ({v:.1f}) → equity vol "
                         "regime; rates futures often gap-extend. Caution.")
        elif v < 12:
            notes.append(f"- **VIX compressed** ({v:.1f}) → benign-vol "
                         "regime; gap_fill mechanic should work cleanly.")

    if not notes:
        notes.append("- No notable regime risk flags from current levels.")
    return L + notes + [""]


def section_summary_box(date: str, macro: dict | None,
                        auct: dict | None, spk: dict | None) -> list[str]:
    """Tight 3-line headline that the agent preamble can read as a single block."""
    parts = []
    if macro:
        for s in macro["series"]:
            if s["series"] == "DGS10" and s.get("level") is not None:
                parts.append(f"10Y={s['level']:.2f}%")
            elif s["series"] == "DFII10" and s.get("level") is not None:
                parts.append(f"real={s['level']:.2f}%")
            elif s["series"] == "DTWEXBGS" and s.get("level") is not None:
                parts.append(f"USD={s['level']:.1f}")
            elif s["series"] == "VIXCLS" and s.get("level") is not None:
                parts.append(f"VIX={s['level']:.1f}")
    snap_line = " | ".join(parts) or "(no levels)"

    n_auct = 0
    if auct:
        today = datetime.now(tz=timezone.utc).date()
        for r in auct.get("auctions", []):
            try:
                ad = datetime.fromisoformat(r["auction_date"]).date()
            except Exception:
                continue
            if 0 <= (ad - today).days <= 7:
                n_auct += 1

    n_high = sum(1 for e in (spk or {}).get("events", [])
                 if e.get("influence") == "HIGH")

    return [f"> **TL;DR ({date})** — {snap_line} · "
            f"{n_auct} auction(s) next 7d · "
            f"{n_high} HIGH-influence Fed speaker(s) upcoming.", ""]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=_today_utc())
    p.add_argument("--refresh", action="store_true",
                   help="Run fetchers before composing the brief.")
    args = p.parse_args()

    if args.refresh:
        print("Running fetchers...")
        run_fetchers()
        print()

    macro = _load_json(_HERE / "vault" / "_meta" / "macro_levels.json")
    auct  = _load_json(_HERE / "vault" / "economic_calendar" / "treasury_auctions.json")
    spk   = _load_json(_HERE / "vault" / "economic_calendar" / "fed_speakers.json")

    out = _HERE / "vault" / "_meta" / f"macro_brief_{args.date}.md"

    L = ["---", "type: macro_brief",
         f"date: {args.date}",
         f"generated_at: {datetime.now(timezone.utc).isoformat()}",
         "generated_by: scripts.generate_macro_brief",
         "applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]",
         "read_on_first_wake: true",
         "---", "",
         f"# Macro brief — {args.date}",
         "",
         "> Auto-generated daily situational awareness for the front-office. "
         "Cross-checks against the live `gap_fill` Treasury edge: anything "
         "that shifts gaps from flow-driven (fade works) toward "
         "information-driven (fade fails)."]

    L += [""]
    L += section_summary_box(args.date, macro, auct, spk)
    L += section_levels(macro)
    L += section_auctions(auct)
    L += section_speakers(spk)
    L += section_regime_read(macro)

    L += ["---", "",
          "## Sources / freshness",
          ""]
    if macro:
        L.append(f"- macro_levels.json — generated {macro.get('generated_at','?')}")
    if auct:
        L.append(f"- treasury_auctions.json — generated {auct.get('generated_at','?')}")
    if spk:
        L.append(f"- fed_speakers.json — generated {spk.get('generated_at','?')}")

    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(_HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

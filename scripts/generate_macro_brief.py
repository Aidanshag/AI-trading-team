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
    """Treasury auctions section.

    Splits upcoming auctions into:
      - Notes/Bonds/TIPS that hit Treasury futures directly (full table row)
      - Bills (collapsed into a one-line summary — they don't move ZN/ZT/ZB/ZF)

    Adds a `concession_days` derivation: any auction whose primary
    affected_futures is non-empty creates two flagged dates — the trading
    day before (concession), and the auction day itself. Both are shown
    in the regime read section.
    """
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

    # Split: futures-affecting (notes, bonds, sometimes TIPS) vs Bills
    affecting = [r for r in upcoming
                 if (r.get("affected_primary") or r.get("affected_futures")
                     or r.get("affected_basis"))]
    bills = [r for r in upcoming
             if not (r.get("affected_primary") or r.get("affected_futures")
                     or r.get("affected_basis"))]

    if affecting:
        L += ["",
              "| Date | Time ET | Type | Term | Amt ($B) | Primary | Basis |",
              "|---|---|---|---|---:|---|---|"]
        for r in affecting:
            amt = (r.get("offering_amt_usd") or 0) / 1e9
            primary = ", ".join(r.get("affected_primary")
                                or r.get("affected_futures") or []) or "—"
            basis = ", ".join(r.get("affected_basis") or []) or "—"
            time_et = r.get("auction_time_et", "")
            L.append(f"| {r['auction_date']} | {time_et} | "
                     f"{r['security_type']} | {r['security_term']} | "
                     f"{amt:.1f} | {primary} | {basis} |")
    else:
        L += ["", "_No futures-affecting auctions in window._"]

    if bills:
        bill_amt = sum((r.get("offering_amt_usd") or 0) for r in bills) / 1e9
        L += ["",
              f"_Plus {len(bills)} short-dated Bill auction(s) totalling "
              f"${bill_amt:.0f}B — no direct ZN/ZT/ZB/ZF impact._"]
    return L + [""]


def derive_concession_days(auct: dict | None, days: int = 10) -> list[dict]:
    """Return a list of {date, label, futures} for each upcoming
    futures-affecting auction. Each auction generates two entries:
    the concession day (auction date − 1 trading day, approximated as
    calendar day − 1) and the auction day itself.

    These are surfaced in the regime read so the Risk Manager / agent
    chain knows when Treasury gap_fill is at elevated risk.
    """
    if not auct or not auct.get("auctions"):
        return []
    today = datetime.now(tz=timezone.utc).date()
    out: list[dict] = []
    for r in auct["auctions"]:
        try:
            ad = datetime.fromisoformat(r["auction_date"]).date()
        except Exception:
            continue
        if not (0 <= (ad - today).days <= days):
            continue
        primary = (r.get("affected_primary") or r.get("affected_futures") or [])
        basis = (r.get("affected_basis") or [])
        if not (primary or basis):
            continue
        # Concession day = calendar day before. (Real concession is
        # the prior trading day; close enough for a daily brief — the
        # gate consumer can tighten this with NYSE calendar later.)
        from datetime import timedelta as _td
        concession = ad - _td(days=1)
        affected = sorted(set(primary) | set(basis))
        if today <= concession <= today + _td(days=days):
            out.append({"date": concession.isoformat(),
                        "label": "concession",
                        "futures": affected,
                        "auction": f"{r['security_term']} {r['security_type']}",
                        "amt_usd_b": (r.get("offering_amt_usd") or 0) / 1e9})
        out.append({"date": ad.isoformat(),
                    "label": "auction-day",
                    "futures": affected,
                    "auction": f"{r['security_term']} {r['security_type']}",
                    "amt_usd_b": (r.get("offering_amt_usd") or 0) / 1e9})
    out.sort(key=lambda x: (x["date"], x["label"]))
    return out


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


def section_regime_read(macro: dict | None,
                        concession: list[dict] | None = None) -> list[str]:
    L = ["## Regime read for `gap_fill` Treasury edge", ""]
    if not macro or not macro.get("series"):
        return L + ["_(insufficient data)_", ""]

    by_id = {s["series"]: s for s in macro["series"]}
    notes = []

    # 10Y yield bands. Tightened thresholds:
    #   |Δ5d| > 0.10  → directional regime (caution / size-down)
    #   |Δ5d| > 0.07  → BORDERLINE (heightened watch — between range and directional)
    #   else            → range regime (preferred)
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
        elif abs(d) > 0.07:
            direction = "rising" if d > 0 else "falling"
            notes.append(f"- **10Y borderline** ({d:+.3f}% / 5d, {direction}) → "
                         "between range and directional regime. Treat the "
                         "next 1-2 sessions as elevated watch — if Δ5d "
                         "crosses ±0.10%, the gap_fill long-fade thesis is "
                         "in directional-regime caution territory.")
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

    # Concession-day flags — auction calendar drives these.
    if concession:
        today = datetime.now(tz=timezone.utc).date().isoformat()
        from datetime import timedelta as _td
        tomorrow = (datetime.now(tz=timezone.utc).date()
                    + _td(days=1)).isoformat()
        for c in concession:
            if c["date"] == today:
                emoji = "**TODAY**"
                bias = "Active concession/auction window — gap_fill on the affected tenor at elevated risk RIGHT NOW."
            elif c["date"] == tomorrow:
                emoji = "**TOMORROW**"
                bias = "Pre-position: gap_fill on these symbols enters elevated-risk window at the next session open."
            else:
                continue   # only flag today/tomorrow in the regime read; full list is in the auctions table
            futs = ", ".join(c["futures"]) or "—"
            notes.append(
                f"- {emoji} `{c['label']}` for {c['auction']} (${c['amt_usd_b']:.0f}B) "
                f"affecting {futs} — {bias}"
            )

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

    macro_path = _HERE / "vault" / "_meta" / "macro_levels.json"
    auct_path  = _HERE / "vault" / "economic_calendar" / "treasury_auctions.json"
    spk_path   = _HERE / "vault" / "economic_calendar" / "fed_speakers.json"

    macro = _load_json(macro_path)
    auct  = _load_json(auct_path)
    spk   = _load_json(spk_path)

    # Source-freshness check: warn if any source is missing or stale.
    # 2026-05-07: improvement Claude Code flagged in coordination doc.
    # Stale = >24h old or missing entirely. The brief still composes
    # against whatever data exists, but flags loudly so the agent chain
    # knows the regime read is built on potentially stale inputs.
    stale_warnings: list[str] = []
    for label, path, payload in [
        ("FRED macro levels", macro_path, macro),
        ("Treasury auctions", auct_path, auct),
        ("Fed speakers", spk_path, spk),
    ]:
        if payload is None or not path.exists():
            stale_warnings.append(f"- **MISSING**: {label} (`{path.name}`) "
                                  "— fetcher hasn't run or output not written.")
            continue
        try:
            gen = payload.get("generated_at", "")
            gen_dt = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
            age_h = (datetime.now(tz=timezone.utc) - gen_dt).total_seconds() / 3600
            if age_h > 24:
                stale_warnings.append(f"- **STALE** ({age_h:.0f}h): {label} "
                                      f"generated {gen[:19]} — data may not "
                                      f"reflect current state.")
        except Exception:
            stale_warnings.append(f"- **UNDATED**: {label} has no parseable "
                                  "`generated_at` — treat as stale.")

    concession = derive_concession_days(auct)

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

    if stale_warnings:
        L += ["", "## ⚠ Source-data freshness warnings",
              "",
              "_The brief below was composed with one or more stale or "
              "missing source files. Treat the regime read as advisory "
              "until inputs refresh._",
              ""] + stale_warnings + [""]

    L += [""]
    L += section_summary_box(args.date, macro, auct, spk)
    L += section_levels(macro)
    L += section_auctions(auct)
    L += section_speakers(spk)
    L += section_regime_read(macro, concession=concession)

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

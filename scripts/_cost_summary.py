"""Month-to-date Claude API spend summary."""

import sqlite3
from datetime import datetime, timezone


def main():
    db = sqlite3.connect("state/fund.db")
    db.row_factory = sqlite3.Row

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    month_prefix = today[:7]

    print(f"Cost summary as of {today}")
    print("=" * 60)

    # Today
    today_rows = list(db.execute(
        "SELECT agent, model, ROUND(usd_est, 4) AS usd "
        "FROM costs WHERE day = ? ORDER BY usd_est DESC",
        (today,),
    ))
    today_total = sum(r["usd"] for r in today_rows)
    print(f"\nTODAY ({today}):  ${today_total:.4f}")
    if today_rows:
        for r in today_rows:
            print(f"  {r['agent']:<25} {r['model']:<35} ${r['usd']:>8.4f}")

    # Month-to-date
    mtd_rows = list(db.execute(
        "SELECT agent, ROUND(SUM(usd_est), 4) AS usd "
        "FROM costs WHERE day LIKE ? GROUP BY agent ORDER BY usd DESC",
        (f"{month_prefix}%",),
    ))
    mtd_total = sum(r["usd"] for r in mtd_rows)
    print(f"\nMONTH-TO-DATE ({month_prefix}):  ${mtd_total:.4f}")
    if mtd_rows:
        for r in mtd_rows:
            print(f"  {r['agent']:<25} ${r['usd']:>8.4f}")

    # All time
    all_rows = list(db.execute(
        "SELECT model, ROUND(SUM(usd_est), 4) AS usd, "
        "       SUM(tokens_in) AS tin, SUM(tokens_out) AS tout, "
        "       SUM(cached_in) AS tcached "
        "FROM costs GROUP BY model ORDER BY usd DESC",
    ))
    all_total = sum(r["usd"] for r in all_rows)
    print(f"\nALL TIME:  ${all_total:.4f}")
    if all_rows:
        for r in all_rows:
            print(f"  {r['model']:<35} in={r['tin']:>10,}  out={r['tout']:>10,}  "
                  f"cached={r['tcached']:>10,}  ${r['usd']:>8.4f}")


if __name__ == "__main__":
    main()

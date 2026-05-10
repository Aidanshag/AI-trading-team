#!/usr/bin/env python3
"""
Export current trading dashboard data as JSON.
Safe to run while auto_trader is running (uses read-only WAL-safe connection).
"""

import sqlite3
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

def get_dashboard_data():
    db_path = Path(__file__).parent.parent / "state" / "fund.db"

    try:
        # WAL-safe read with pragmas
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.isolation_level = None  # Autocommit mode
        conn.execute('PRAGMA query_only = ON')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Latest account snapshot
        c.execute('SELECT * FROM account_snapshots ORDER BY ts DESC LIMIT 1')
        snap = c.fetchone()
        latest_snap = dict(snap) if snap else {}

        # Today's P&L (use UTC date)
        today_utc = datetime.now(ZoneInfo('UTC')).strftime('%Y-%m-%d')
        c.execute('SELECT * FROM daily_pl WHERE day = ?', (today_utc,))
        today_row = c.fetchone()
        today_pl = dict(today_row) if today_row else {}

        # Open positions
        c.execute('''SELECT symbol, contract_month, side, contracts, avg_price, opened_at, stop_price, target_price
                     FROM positions ORDER BY symbol''')
        positions = [dict(row) for row in c.fetchall()]

        # Recent risk events (today only)
        c.execute('''SELECT ts, severity, rule, detail FROM risk_events
                     WHERE date(ts) = date('now')
                     ORDER BY ts DESC''')
        risk_events = [dict(row) for row in c.fetchall()]

        # Breaches/blocks only
        breaches = [e for e in risk_events if e['severity'] in ('breach', 'block')]

        # Today's trade count
        c.execute('''SELECT COUNT(*) as cnt FROM orders
                     WHERE status = 'filled' AND date(ts_filled) = date('now')''')
        trade_count = c.fetchone()['cnt']

        # Gap-fill performance (today's gap_fill trades only)
        c.execute('''
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN avg_fill_price > 0 THEN 1 ELSE 0 END) as profitable,
                AVG(CASE WHEN avg_fill_price > 0 THEN 1 ELSE 0 END) as win_rate
            FROM decisions
            WHERE kind = 'gap_fill' AND date(ts) = date('now')
        ''')
        gap_fill_row = c.fetchone()
        gap_fill_stats = dict(gap_fill_row) if gap_fill_row else {}

        conn.close()

        # Assemble response
        data = {
            'exported_at': datetime.now(ZoneInfo('UTC')).isoformat(),
            'account': {
                'snapshot_time': latest_snap.get('ts', None),
                'balance_usd': float(latest_snap.get('balance_usd', 0)),
                'unrealized_pl_usd': float(latest_snap.get('unrealized_pl_usd', 0)),
                'realized_pl_today_usd': float(latest_snap.get('realized_pl_day_usd', 0)),
                'trailing_dd_usd': float(latest_snap.get('trailing_dd_usd', 0)),
                'open_contracts': int(latest_snap.get('open_contracts_total', 0)),
                'can_trade': bool(latest_snap.get('can_trade', True)),
            },
            'daily_pnl': {
                'realized_usd': float(today_pl.get('realized_pl_usd', 0)),
                'peak_usd': float(today_pl.get('peak_realized_pl_usd', 0)),
                'trade_count': int(today_pl.get('trade_count', 0) or trade_count),
            },
            'positions': [
                {
                    'symbol': p['symbol'],
                    'side': p['side'],
                    'contracts': p['contracts'],
                    'avg_price': float(p['avg_price']),
                    'opened_at': p['opened_at'],
                }
                for p in positions
            ],
            'alerts': {
                'risk_events_today': len(risk_events),
                'breaches_blocks': len(breaches),
                'events': breaches[:5],  # Last 5 breaches/blocks
            },
            'strategy_performance': {
                'gap_fill_trades_today': int(gap_fill_stats.get('total_trades', 0) or 0),
                'gap_fill_profitable': int(gap_fill_stats.get('profitable', 0) or 0),
            }
        }

        return data

    except Exception as e:
        return {'error': str(e), 'exported_at': datetime.now(ZoneInfo('UTC')).isoformat()}


if __name__ == '__main__':
    data = get_dashboard_data()
    json.dump(data, sys.stdout, indent=2, default=str)

-- Operational state for the fund. All times UTC ISO-8601 strings.
-- Single-writer discipline: only the state_store MCP server writes here.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── Account snapshots (one row per broker poll) ────────────────
CREATE TABLE IF NOT EXISTS account_snapshots (
    id                   INTEGER PRIMARY KEY,
    ts                   TEXT NOT NULL,
    environment          TEXT NOT NULL,               -- paper | combine | funded
    balance_usd          REAL NOT NULL,
    unrealized_pl_usd    REAL NOT NULL,
    realized_pl_day_usd  REAL NOT NULL,
    trailing_dd_usd      REAL NOT NULL,
    open_contracts_total INTEGER NOT NULL,
    can_trade            INTEGER NOT NULL DEFAULT 1   -- broker canTrade flag (0=halted server-side)
);
CREATE INDEX IF NOT EXISTS idx_account_snap_ts ON account_snapshots(ts);

-- ── Positions (current holdings) ───────────────────────────────
CREATE TABLE IF NOT EXISTS positions (
    id                  INTEGER PRIMARY KEY,
    symbol              TEXT NOT NULL,
    contract_month      TEXT,                         -- e.g. 2026M (Jun 2026)
    side                TEXT NOT NULL CHECK (side IN ('long','short')),
    contracts           INTEGER NOT NULL,
    avg_price           REAL NOT NULL,
    opened_at           TEXT NOT NULL,
    stop_price          REAL,
    target_price        REAL,
    thesis_note_path    TEXT,                         -- link to vault/theses/*.md
    structure_id        INTEGER REFERENCES structures(id),  -- if part of a multi-leg
    UNIQUE(symbol, contract_month, side)
);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

-- ── Option legs (for options positions + multi-leg structures) ──
CREATE TABLE IF NOT EXISTS option_legs (
    id               INTEGER PRIMARY KEY,
    structure_id     INTEGER REFERENCES structures(id),
    underlying       TEXT NOT NULL,
    expiry           TEXT NOT NULL,
    strike           REAL NOT NULL,
    right            TEXT NOT NULL CHECK (right IN ('C','P')),
    side             TEXT NOT NULL CHECK (side IN ('long','short')),
    contracts        INTEGER NOT NULL,
    avg_price        REAL NOT NULL,
    opened_at        TEXT NOT NULL,
    -- Greeks snapshot at entry
    delta_entry      REAL,
    gamma_entry      REAL,
    vega_entry       REAL,
    theta_entry      REAL,
    iv_entry         REAL
);
CREATE INDEX IF NOT EXISTS idx_legs_struct ON option_legs(structure_id);

-- ── Multi-leg structure envelope (spreads, condors, etc.) ───────
CREATE TABLE IF NOT EXISTS structures (
    id              INTEGER PRIMARY KEY,
    kind            TEXT NOT NULL,                    -- long_call_spread, iron_condor, ...
    underlying      TEXT NOT NULL,
    opened_at       TEXT NOT NULL,
    closed_at       TEXT,
    max_loss_usd    REAL NOT NULL,                    -- computed at open; null structure => block
    max_gain_usd    REAL,
    thesis_note_path TEXT
);

-- ── Orders (intent + lifecycle) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id               INTEGER PRIMARY KEY,
    client_order_id  TEXT UNIQUE NOT NULL,
    agent            TEXT NOT NULL,                   -- which agent proposed it
    ts_proposed      TEXT NOT NULL,
    ts_submitted     TEXT,
    ts_filled        TEXT,
    ts_cancelled     TEXT,
    symbol           TEXT NOT NULL,
    contract_month   TEXT,
    side             TEXT NOT NULL,                   -- buy | sell
    order_type       TEXT NOT NULL,                   -- market | limit | stop | stop_limit
    qty              INTEGER NOT NULL,
    limit_price      REAL,
    stop_price       REAL,
    status           TEXT NOT NULL,                   -- proposed | blocked | submitted | filled | cancelled | rejected
    risk_verdict     TEXT NOT NULL,                   -- allow | block
    risk_reason      TEXT,                            -- if blocked, why
    broker_order_id  TEXT,
    avg_fill_price   REAL,
    structure_id     INTEGER REFERENCES structures(id)
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_agent  ON orders(agent);

-- ── Decision log (append-only, human-readable) ──────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    agent       TEXT NOT NULL,
    kind        TEXT NOT NULL,                        -- thesis | order_proposal | risk_vote | pm_allocation | post_trade | regime_call
    symbol      TEXT,
    summary     TEXT NOT NULL,
    rationale   TEXT NOT NULL,
    vault_path  TEXT,                                 -- if persisted to Obsidian
    model       TEXT,                                 -- which Claude model produced it
    tokens_in   INTEGER,
    tokens_out  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(ts);
CREATE INDEX IF NOT EXISTS idx_decisions_agent ON decisions(agent);

-- ── Risk events (every hook verdict, warn, or breach) ───────────
CREATE TABLE IF NOT EXISTS risk_events (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('info','warn','block','breach')),
    rule        TEXT NOT NULL,                        -- e.g. 'naked_short', 'daily_loss_limit'
    agent       TEXT,
    order_id    INTEGER REFERENCES orders(id),
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS idx_risk_ts ON risk_events(ts);

-- ── Cost tracking (Claude API spend per agent per day) ──────────
CREATE TABLE IF NOT EXISTS costs (
    id          INTEGER PRIMARY KEY,
    day         TEXT NOT NULL,                         -- YYYY-MM-DD
    agent       TEXT NOT NULL,
    model       TEXT NOT NULL,
    tokens_in   INTEGER NOT NULL,
    tokens_out  INTEGER NOT NULL,
    cached_in   INTEGER NOT NULL DEFAULT 0,
    usd_est     REAL NOT NULL,
    UNIQUE(day, agent, model)
);

-- ── Shadow trades (hypothetical signals for cross-ticker screening) ──
-- Records every TRIGGER the team finds, even ones that fail the focus
-- universe gate or were skipped for other reasons. Outcomes are filled
-- in retroactively by scripts/resolve_shadow_trades.py. The shadow
-- recap (scripts/shadow_trade_recap.py) reads this to recommend new
-- symbols/strategies to add to the active set.
CREATE TABLE IF NOT EXISTS shadow_trades (
    id              INTEGER PRIMARY KEY,
    ts_signal       TEXT NOT NULL,                     -- when the trigger fired
    agent           TEXT NOT NULL,                     -- Edge Hunter, analyst, etc.
    symbol          TEXT NOT NULL,
    strategy        TEXT NOT NULL,                     -- ORB, NR7, vol_regime_trend, ...
    side            TEXT NOT NULL CHECK (side IN ('long','short')),
    entry_price     REAL NOT NULL,
    stop_price      REAL NOT NULL,
    target_price    REAL NOT NULL,
    risk_usd        REAL,
    rr_planned      REAL,
    conviction      TEXT,                              -- low | med | high | validation
    horizon         TEXT,                              -- intraday | swing | position
    -- Why this is shadow rather than real
    shadow_reason   TEXT NOT NULL,                     -- focus_universe_blocked | risk_block | sector_disabled | scout_only | budget_exhausted
    -- Resolution (filled in later by resolve script)
    ts_resolved     TEXT,
    outcome         TEXT,                              -- target_hit | stop_hit | time_stopped | invalidated | unresolved
    pnl_r           REAL,                              -- R-multiple (target = +rr_planned, stop = -1)
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_shadow_ts ON shadow_trades(ts_signal);
CREATE INDEX IF NOT EXISTS idx_shadow_symbol ON shadow_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_shadow_strategy ON shadow_trades(strategy);
CREATE INDEX IF NOT EXISTS idx_shadow_unresolved ON shadow_trades(outcome) WHERE outcome IS NULL;

-- ── Daily P&L (one row per UTC trading day, finalized at session close) ──
-- Powers the Topstep 50%-consistency advisory in the risk hook. UPSERT'd
-- by session_close_workflow from the day's last account_snapshot.
CREATE TABLE IF NOT EXISTS daily_pl (
    day                  TEXT PRIMARY KEY,            -- YYYY-MM-DD UTC
    realized_pl_usd      REAL NOT NULL,
    peak_realized_pl_usd REAL,                        -- intraday high-water from snapshots
    trade_count          INTEGER,
    closed_at            TEXT NOT NULL                -- ISO-8601 UTC
);

-- ── News / events ingested (for audit of what agents saw) ───────
CREATE TABLE IF NOT EXISTS news_items (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    source      TEXT NOT NULL,
    url         TEXT,
    headline    TEXT NOT NULL,
    body        TEXT,
    symbols     TEXT,                                  -- comma-separated
    impact      TEXT                                   -- low | med | high
);
CREATE INDEX IF NOT EXISTS idx_news_ts ON news_items(ts);

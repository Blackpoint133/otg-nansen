-- Review-only migration artifact. Do not apply automatically.
CREATE SCHEMA IF NOT EXISTS nansen;

CREATE TABLE nansen.token_information (
    chain TEXT NOT NULL,
    token_address TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market_cap_usd NUMERIC,
    fdv_usd NUMERIC,
    circulating_supply NUMERIC,
    total_supply NUMERIC,
    volume_total_usd NUMERIC,
    buy_volume_usd NUMERIC,
    sell_volume_usd NUMERIC,
    total_buys BIGINT,
    total_sells BIGINT,
    unique_buyers BIGINT,
    unique_sellers BIGINT,
    liquidity_usd NUMERIC,
    total_holders BIGINT,
    PRIMARY KEY (chain, token_address, retrieved_at)
);

CREATE TABLE nansen.flows (
    flow_key TEXT PRIMARY KEY,
    chain TEXT NOT NULL,
    token_address TEXT NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    price_usd NUMERIC NOT NULL,
    token_amount NUMERIC NOT NULL,
    value_usd NUMERIC NOT NULL,
    holders_count BIGINT NOT NULL,
    total_inflows_count BIGINT NOT NULL,
    total_outflows_count BIGINT NOT NULL,
    flow_label TEXT NOT NULL,
    bucket_end TIMESTAMPTZ,
    is_complete BOOLEAN,
    total_inflows_cex BIGINT,
    total_inflows_dex BIGINT,
    total_outflows_cex BIGINT,
    total_outflows_dex BIGINT,
    CHECK (flow_label = btrim(flow_label) AND btrim(flow_label) <> '')
);

CREATE TABLE nansen.dex_trades (
    trade_key TEXT PRIMARY KEY,
    chain TEXT NOT NULL,
    requested_token_address TEXT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    transaction_hash TEXT NOT NULL,
    trader_address TEXT NOT NULL,
    trader_address_label TEXT,
    action TEXT NOT NULL,
    token_address TEXT NOT NULL,
    token_name TEXT NOT NULL,
    token_amount NUMERIC NOT NULL,
    traded_token_address TEXT NOT NULL,
    traded_token_name TEXT NOT NULL,
    traded_token_amount NUMERIC NOT NULL,
    estimated_swap_price_usd NUMERIC NOT NULL,
    estimated_value_usd NUMERIC NOT NULL
);

CREATE TABLE nansen.ingestion_runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'partial')),
    chain TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    token_address TEXT NOT NULL,
    flow_label TEXT NOT NULL,
    request_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    pages_requested INTEGER NOT NULL DEFAULT 0,
    api_calls INTEGER NOT NULL DEFAULT 0,
    records_received INTEGER NOT NULL DEFAULT 0,
    records_normalized INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated_or_conflicted INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_summary TEXT,
    CHECK (
        (endpoint = 'flows' AND flow_label = btrim(flow_label) AND btrim(flow_label) <> '')
        OR (endpoint <> 'flows' AND flow_label = '')
    ),
    CHECK (
        (
        jsonb_typeof(request_scope) = 'object'
        AND request_scope ? 'chain'
        AND request_scope ? 'endpoint'
        AND request_scope ? 'token_address'
        AND request_scope ? 'flow_label'
        AND jsonb_typeof(request_scope->'chain') = 'string'
        AND jsonb_typeof(request_scope->'endpoint') = 'string'
        AND jsonb_typeof(request_scope->'token_address') = 'string'
        AND jsonb_typeof(request_scope->'flow_label') = 'string'
        AND request_scope->>'chain' = chain
        AND request_scope->>'endpoint' = endpoint
        AND request_scope->>'token_address' = token_address
        AND request_scope->>'flow_label' = flow_label
        ) IS TRUE
    )
);

CREATE TABLE nansen.checkpoints (
    chain TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    token_address TEXT NOT NULL,
    flow_label TEXT NOT NULL,
    last_complete_timestamp TIMESTAMPTZ NOT NULL,
    last_success_run_id UUID NOT NULL REFERENCES nansen.ingestion_runs(run_id),
    updated_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (chain, endpoint, token_address, flow_label),
    CHECK (
        (endpoint = 'flows' AND flow_label = btrim(flow_label) AND btrim(flow_label) <> '')
        OR (endpoint <> 'flows' AND flow_label = '')
    )
);

CREATE INDEX nansen_flows_lookup ON nansen.flows (chain, token_address, date);
CREATE INDEX nansen_dex_trades_lookup ON nansen.dex_trades (chain, token_address, block_timestamp);
CREATE INDEX nansen_ingestion_runs_lookup ON nansen.ingestion_runs (chain, endpoint, started_at);

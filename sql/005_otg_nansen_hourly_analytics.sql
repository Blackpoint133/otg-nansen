-- Task 033: staging-only analytical snapshots. No production schema is targeted.
CREATE TABLE IF NOT EXISTS nansen.otg_market_hourly (
    hour_start timestamptz PRIMARY KEY,
    hour_end timestamptz NOT NULL,
    trade_tx_count bigint NOT NULL CHECK (trade_tx_count >= 0),
    native_gun_amount_truncated numeric NOT NULL CHECK (native_gun_amount_truncated >= 0),
    unique_buyers bigint NOT NULL CHECK (unique_buyers >= 0),
    unique_sellers bigint NOT NULL CHECK (unique_sellers >= 0),
    unique_items bigint NOT NULL CHECK (unique_items >= 0),
    CHECK (hour_end = hour_start + interval '1 hour'),
    CHECK (hour_start = date_trunc('hour', hour_start AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS nansen.otg_nansen_hourly (
    hour_start timestamptz PRIMARY KEY,
    hour_end timestamptz NOT NULL,
    market_trade_tx_count bigint NOT NULL CHECK (market_trade_tx_count >= 0),
    market_native_gun_amount_truncated numeric NOT NULL CHECK (market_native_gun_amount_truncated >= 0),
    market_unique_buyers bigint NOT NULL CHECK (market_unique_buyers >= 0),
    market_unique_sellers bigint NOT NULL CHECK (market_unique_sellers >= 0),
    market_unique_items bigint NOT NULL CHECK (market_unique_items >= 0),
    nansen_price_usd numeric NOT NULL,
    nansen_token_amount numeric NOT NULL,
    nansen_value_usd numeric NOT NULL,
    nansen_holders_count bigint NOT NULL CHECK (nansen_holders_count >= 0),
    nansen_total_inflows_count numeric NOT NULL,
    nansen_total_outflows_count numeric NOT NULL,
    gun_price_return_1h numeric,
    gun_price_return_6h numeric,
    gun_price_return_24h numeric,
    flow_count_imbalance numeric NOT NULL,
    flow_count_total numeric NOT NULL,
    trade_tx_delta_1h bigint,
    trade_tx_delta_6h bigint,
    trade_tx_delta_24h bigint,
    native_gun_delta_1h numeric,
    native_gun_delta_6h numeric,
    native_gun_delta_24h numeric,
    CHECK (hour_end = hour_start + interval '1 hour'),
    CHECK (hour_start = date_trunc('hour', hour_start AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')
);

ALTER TABLE nansen.flows
    ALTER COLUMN total_inflows_count TYPE NUMERIC
        USING total_inflows_count::NUMERIC,
    ALTER COLUMN total_outflows_count TYPE NUMERIC
        USING total_outflows_count::NUMERIC;

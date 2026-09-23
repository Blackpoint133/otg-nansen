ALTER TABLE nansen.flows
    ALTER COLUMN bucket_end SET NOT NULL,
    ADD CONSTRAINT nansen_flows_bucket_interval_check CHECK (bucket_end > date),
    ADD CONSTRAINT nansen_flows_natural_bucket_identity_unique
        UNIQUE (chain, token_address, flow_label, date, bucket_end);

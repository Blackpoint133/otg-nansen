# Architecture

## Confirmed objective

The project will use Nansen token/wallet intelligence to study historical
`$GUN` activity and subsequent Off The Grid NFT/item-market reactions.

Phase 0B established that the smallest future architecture is a controlled
Nansen client, normalized event/flow persistence, historical `$GUN` event
detection, read-only comparison against existing OTG market history, and
prepared analytical output. No implementation or schema has been created.

The current technical recommendation is primary Avalanche ingestion with a
separately checkpointed Solana adapter. Both chains returned usable token,
trade, holder, transfer, and buyer/seller responses, while the narrow Solana
Smart Money flows window was empty. The native GUNZ chain remains a separate
identity question because the reviewed Nansen chain list did not include
`gunz`.

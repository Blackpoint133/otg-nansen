# OTG Nansen Analytics

Public early-stage project for Nansen-powered analysis of `$GUN` activity and
subsequent Off The Grid NFT/item-market reactions. Nansen is intended as a
token and wallet intelligence source; the relationship between observed token
activity and market behavior will be investigated rather than assumed.

This repository is the Nansen competition/buildathon project and is currently
in early development and reconnaissance. It makes no predictive or causal
claims.

## Setup

Setup remains minimal while the architecture and Nansen API surface are being
verified. Copy the safe variable names from `.env.example` into a local `.env`
and provide values through your local secret-management workflow. Never commit
`.env`.

## Status

Phase 0A bootstrap and Phase 0B reconnaissance are complete. A bounded Nansen
client foundation and fixture-first contract tests are now implemented. The
evidence supports a primary Avalanche MVP source with Solana retained as a
tested secondary source. Persistence and parser business logic remain later
phases. The client contracts are represented by sanitized fixtures and strict
shape tests; the raw-to-normalized boundary now produces immutable models with
UTC timestamps and Decimal numeric values. Persistence remains unimplemented.
Task 007 added a proposed, review-only PostgreSQL design and parameter mapping;
the migration was not applied at that stage.
Task 008 hardens persistence semantics with request-scope provenance,
canonical stable keys, and separate checkpoint streams for flow labels.
Task 009 finalizes the proposed persistence boundary: flows require an
explicit non-empty scope, equivalent Decimal key values canonicalize alike,
flow keys exclude unproven bucket observations, and parameterized upserts
protect complete records from incomplete downgrades. Audit lifecycle state is
durable separately from the data/checkpoint transaction. Migration status was
NOT APPLIED at that stage.
Task 010 closes the remaining pre-DDL consistency gaps: Avalanche EVM
addresses are lowercase at the persistence boundary, Solana addresses remain
case-sensitive, flow scopes are trimmed and required, and successful data,
checkpoint, and audit status commit atomically. Migration status was NOT
APPLIED before staging authorization.
Task 011 adds a psycopg3 repository adapter and a staging-only migration
command. The migration is guarded to `server_otg_staging` and is now applied
there. Production is not connected for writes or modified.

Task 013A applied the reviewed `nansen` schema to `server_otg_staging` only.
Integration tests remain intentionally pending until the operator revokes the
temporary CREATE privilege.

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
Task 007 adds a proposed, review-only PostgreSQL design and parameter mapping;
the migration has not been applied.
Task 008 hardens persistence semantics with request-scope provenance,
canonical stable keys, and separate checkpoint streams for flow labels.

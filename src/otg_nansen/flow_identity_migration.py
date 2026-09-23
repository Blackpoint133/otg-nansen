"""Pure planning helpers for a collision-safe flow-key migration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import uuid4

from .persistence import PersistenceDesignError, flow_identity_key


@dataclass(frozen=True)
class FlowKeyMigrationPlan:
    old_to_new: tuple[tuple[str, str], ...]
    temporary_keys: tuple[str, ...]
    old_key_digest: str
    new_key_digest: str
    cross_collisions: int


def _digest(keys: Iterable[str]) -> str:
    from hashlib import sha256

    return sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest()


def plan_flow_key_migration(rows: Iterable[dict[str, Any]], *, temporary_namespace: str | None = None) -> FlowKeyMigrationPlan:
    """Plan all remaps from identity-only rows; reject ambiguous/colliding plans."""
    items = list(rows)
    pairs: list[tuple[str, str]] = []
    for row in items:
        old_key = row["flow_key"]
        new_key = flow_identity_key(
            row["chain"], row["token_address"], row["flow_label"], row["date"], row["bucket_end"],
        )
        pairs.append((old_key, new_key))
    old_keys = [old for old, _ in pairs]
    new_keys = [new for _, new in pairs]
    if len(set(old_keys)) != len(old_keys):
        raise PersistenceDesignError("existing flow keys are not unique")
    if len(set(new_keys)) != len(new_keys):
        raise PersistenceDesignError("new flow identity keys are not unique")
    old_to_row = {old: index for index, (old, _) in enumerate(pairs)}
    cross_collisions = sum(1 for index, (_, new) in enumerate(pairs)
                           if new in old_to_row and old_to_row[new] != index)
    if cross_collisions:
        raise PersistenceDesignError("new flow keys cross-collide with existing keys")

    namespace = temporary_namespace or uuid4().hex
    occupied = set(old_keys) | set(new_keys)
    temporary = tuple(f"__nansen_flow_key_migration__{namespace}__{i}" for i in range(len(items)))
    if len(set(temporary)) != len(temporary) or occupied.intersection(temporary):
        raise PersistenceDesignError("temporary flow key namespace is not collision-safe")
    return FlowKeyMigrationPlan(
        tuple(pairs), temporary, _digest(old_keys), _digest(new_keys), cross_collisions,
    )

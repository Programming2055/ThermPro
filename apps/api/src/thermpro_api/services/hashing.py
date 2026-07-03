"""
Canonical JSON hashing service per M0-09.

Canonicalization policy:
- Keys sorted lexicographically at every nesting level (recursive).
- No whitespace (separators=(',', ':')).
- UTF-8 encoding.
- Numbers serialised by Python's json.dumps (IEEE 754 double).
- The same dict with keys in any order produces an identical hash.

This matches the policy used to compute content_hash_sha256 for
library releases and calculation input checksums.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """
    Serialise *data* to canonical JSON bytes.

    The output is deterministic regardless of dict key insertion order:
    keys are sorted recursively, whitespace is suppressed, and the result
    is UTF-8 encoded.

    Args:
        data: Dictionary to serialise. Must be JSON-serialisable.

    Returns:
        UTF-8 bytes of the canonical JSON representation.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(data: dict[str, Any]) -> str:
    """
    Compute the SHA-256 hex digest of the canonical JSON of *data*.

    Properties guaranteed by canonical_json_bytes:
    1. Key-order independence: {"a":1,"b":2} == {"b":2,"a":1}.
    2. Sensitivity: changing any value changes the digest.
    3. Unit-awareness: 50e-6 != 50 (caller must pass SI values).
    4. Library-manifest sensitivity: any pin change changes the digest.

    Args:
        data: Dictionary to hash. Must be JSON-serialisable.

    Returns:
        64-character lowercase hex string (SHA-256).
    """
    raw = canonical_json_bytes(data)
    return hashlib.sha256(raw).hexdigest()

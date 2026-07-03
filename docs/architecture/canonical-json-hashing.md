# Canonical JSON Hashing Policy

**Document ID:** THERM-ARCH-M1-002  
**Revision:** M1r1  
**See also:** M0-09 Dataset Versioning, DR-002

---

## Purpose

Every calculation submission stores an `input_checksum_sha256` and every approved library
release stores a `content_hash_sha256`. These hashes guarantee:

1. **Immutability detection** — any mutation of stored data is detectable at read-time.
2. **Reproducibility** — re-running with the same inputs produces the same hash.
3. **Audit trail** — the hash in an AuditEvent uniquely identifies the exact data version.

---

## Canonicalization Algorithm

Implemented in `apps/api/src/thermpro_api/services/hashing.py`.

```python
def canonical_json_bytes(data: dict) -> bytes:
    return json.dumps(
        data,
        sort_keys=True,       # keys sorted lexicographically at ALL nesting levels
        separators=(",", ":"), # no whitespace
        ensure_ascii=False,   # preserve Unicode
    ).encode("utf-8")

def sha256_hex(data: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()
```

### Properties

| Property | Guarantee |
|----------|-----------|
| Key-order independence | `{"a":1,"b":2}` ≡ `{"b":2,"a":1}` |
| Whitespace independence | Pretty-printed ≡ compact |
| Value sensitivity | Any value change changes the hash |
| Type sensitivity | `1` ≠ `"1"` |
| Unit sensitivity | `50e-6` ≠ `50` (caller must pass SI values) |
| Nesting | Sort applied recursively at all levels |

---

## Usage Points

| Context | Hash field | Source data |
|---------|-----------|-------------|
| Library release approval | `content_hash_sha256` | All entries as canonical JSON |
| Library pin in manifest | `content_hash_sha256` | Same as release |
| Calculation input | `input_checksum_sha256` | Full `input_snapshot` dict |

---

## Verification

Hashing is verified by 7 unit tests in `apps/api/tests/unit/test_hashing.py`:
- Key-order independence
- Whitespace independence  
- Nested key ordering
- Value sensitivity
- Type sensitivity (`int` vs `string`)
- Unicode preservation
- Round-trip stability

---

## What Is NOT Canonical JSON

- Pretty-printed JSON (whitespace differs)
- Python `str(dict)` (uses single quotes, non-deterministic order in older Python)
- JSON with keys in insertion order (not sorted)

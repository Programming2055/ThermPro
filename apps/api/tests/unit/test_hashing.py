"""
Tests for canonical JSON hashing (M0-09).

Required properties:
1. Key-order independence: same data in any key order produces same hash.
2. Value sensitivity: changing any value changes the hash.
3. Unit sensitivity: changing numeric scale (e.g. Ohm vs uOhm) changes hash.
4. Library manifest sensitivity: any pin change changes the hash.
"""
import pytest
from thermpro_api.services.hashing import canonical_json_bytes, sha256_hex


# ---------------------------------------------------------------------------
# 1. Key-order independence
# ---------------------------------------------------------------------------

def test_key_order_independence():
    """Dicts with the same content but different insertion order hash identically."""
    d1 = {"a": 1, "b": 2, "c": 3}
    d2 = {"c": 3, "a": 1, "b": 2}
    assert sha256_hex(d1) == sha256_hex(d2)


def test_nested_key_order_independence():
    """Nested dicts are also sorted recursively."""
    d1 = {"outer": {"z": 26, "a": 1}, "x": 42}
    d2 = {"x": 42, "outer": {"a": 1, "z": 26}}
    assert sha256_hex(d1) == sha256_hex(d2)


# ---------------------------------------------------------------------------
# 2. Value sensitivity
# ---------------------------------------------------------------------------

def test_changed_value_changes_hash():
    """Changing a leaf value produces a different hash."""
    d1 = {"schema_version": "1.0", "mode": "MODE_1"}
    d2 = {"schema_version": "1.0", "mode": "MODE_2"}
    assert sha256_hex(d1) != sha256_hex(d2)


def test_changed_nested_value_changes_hash():
    """Changing a nested value produces a different hash."""
    d1 = {"enclosure": {"height_m": 2.0, "width_m": 0.8}}
    d2 = {"enclosure": {"height_m": 2.1, "width_m": 0.8}}
    assert sha256_hex(d1) != sha256_hex(d2)


# ---------------------------------------------------------------------------
# 3. Unit sensitivity
# ---------------------------------------------------------------------------

def test_unit_scale_changes_hash():
    """
    50e-6 Ohm (SI) vs 50 (uOhm display value) produce different hashes.

    Engine-internal dicts always use SI. If a caller accidentally passes
    a display-unit value, the hash will differ from the SI canonical value.
    """
    si_value = {"resistance_ohm": 50e-6}
    display_value = {"resistance_ohm": 50.0}  # uOhm, wrong SI unit
    assert sha256_hex(si_value) != sha256_hex(display_value)


def test_numeric_precision_matters():
    """273.15 and 273.16 produce different hashes."""
    d1 = {"ambient_K": 273.15}
    d2 = {"ambient_K": 273.16}
    assert sha256_hex(d1) != sha256_hex(d2)


# ---------------------------------------------------------------------------
# 4. Library manifest sensitivity
# ---------------------------------------------------------------------------

def test_manifest_pin_version_change_changes_hash():
    """Bumping a library version changes the input hash."""
    d1 = {
        "schema_version": "1.0",
        "library_manifest": {
            "material_library": {
                "name": "MaterialLibrary",
                "version": "1.0.0",
                "content_hash_sha256": "a" * 64,
            }
        },
    }
    d2 = {
        "schema_version": "1.0",
        "library_manifest": {
            "material_library": {
                "name": "MaterialLibrary",
                "version": "1.1.0",
                "content_hash_sha256": "a" * 64,
            }
        },
    }
    assert sha256_hex(d1) != sha256_hex(d2)


def test_manifest_pin_hash_change_changes_hash():
    """Changing the content hash of a pin changes the overall input hash."""
    d1 = {
        "library_manifest": {
            "device_library": {
                "name": "DeviceLibrary",
                "version": "2.0.0",
                "content_hash_sha256": "a" * 64,
            }
        }
    }
    d2 = {
        "library_manifest": {
            "device_library": {
                "name": "DeviceLibrary",
                "version": "2.0.0",
                "content_hash_sha256": "b" * 64,
            }
        }
    }
    assert sha256_hex(d1) != sha256_hex(d2)


# ---------------------------------------------------------------------------
# 5. UTF-8 encoding
# ---------------------------------------------------------------------------

def test_utf8_encoding_used():
    """canonical_json_bytes returns UTF-8 bytes."""
    raw = canonical_json_bytes({"name": "Schneider"})
    assert isinstance(raw, bytes)
    assert raw.decode("utf-8")  # must be valid UTF-8


def test_unicode_value_stable():
    """Unicode strings produce stable, deterministic bytes."""
    d = {"desc": "Thermique élevée"}
    b1 = canonical_json_bytes(d)
    b2 = canonical_json_bytes(d)
    assert b1 == b2


# ---------------------------------------------------------------------------
# 6. No whitespace in canonical form
# ---------------------------------------------------------------------------

def test_no_whitespace_in_canonical_bytes():
    """Canonical JSON must not contain spaces or newlines."""
    raw = canonical_json_bytes({"a": 1, "b": [1, 2, 3]})
    decoded = raw.decode("utf-8")
    assert " " not in decoded
    assert "\n" not in decoded


# ---------------------------------------------------------------------------
# 7. Determinism
# ---------------------------------------------------------------------------

def test_deterministic_across_calls():
    """Calling sha256_hex twice on the same dict returns the same result."""
    d = {"mode": "MODE_2", "schema_version": "1.0"}
    assert sha256_hex(d) == sha256_hex(d)

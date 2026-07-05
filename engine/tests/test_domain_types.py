"""Tests for domain type enums -- verify fan states, joint conditions, K_AC sources."""
from thermal_core.domain_types import (
    FanOperatingState,
    JointCondition,
    ContactResistanceSource,
    KAcSource,
    CalculationMode,
    StandardProfile,
    CalculationRunStatus,
    LibraryStatus,
)


def test_fan_states_six_values():
    states = list(FanOperatingState)
    assert len(states) == 6


def test_fan_states_correct_names():
    assert FanOperatingState.RUNNING_FORWARD.value == "RUNNING_FORWARD"
    assert FanOperatingState.STOPPED_FREE_FLOW.value == "STOPPED_FREE_FLOW"
    assert FanOperatingState.STOPPED_WITH_DAMPER.value == "STOPPED_WITH_DAMPER"
    assert FanOperatingState.FAILED_OPEN.value == "FAILED_OPEN"
    assert FanOperatingState.FAILED_BLOCKED.value == "FAILED_BLOCKED"
    assert FanOperatingState.REVERSE_FLOW_ESTIMATED.value == "REVERSE_FLOW_ESTIMATED"


def test_no_arc_flash_mode():
    modes = [m.value for m in CalculationMode]
    assert "ARC_FLASH" not in modes


def test_no_ul_ansi_profiles():
    profiles = [p.value for p in StandardProfile]
    assert "UL_891" not in profiles
    assert "UL_1558" not in profiles
    assert "ANSI_IEEE_C37_20_1" not in profiles
    assert "IEEE_1584_2018" not in profiles


def test_joint_condition_unknown_requires_attention():
    assert JointCondition.UNKNOWN in JointCondition


def test_contact_resistance_hierarchy_order():
    # Verify data hierarchy members exist per DR-004
    assert ContactResistanceSource.MEASURED.value == "MEASURED"
    assert ContactResistanceSource.MANUFACTURER.value == "MANUFACTURER"
    assert ContactResistanceSource.JOINT_LIBRARY.value == "JOINT_LIBRARY"
    assert ContactResistanceSource.USER_ASSUMPTION.value == "USER_ASSUMPTION"


def test_k_ac_source_not_applied():
    assert KAcSource.NOT_APPLIED in KAcSource


def test_engine_not_implemented_status():
    assert CalculationRunStatus.ENGINE_NOT_IMPLEMENTED in CalculationRunStatus


def test_library_status_withdrawn():
    assert LibraryStatus.WITHDRAWN in LibraryStatus
    assert LibraryStatus.APPROVED in LibraryStatus

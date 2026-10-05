"""
Tests for the M0-03 → engine → M0-04 JSON contract (CR-TECH-001).

These exercise the mapping and the engineering rules it enforces. Conformance
of the emitted document to the M0-04 JSON Schema is tested separately, in
apps/api/tests/contract, which is the layer that owns both schemas.

Covered here:
  - every M0-03 entity becomes exactly one heat source, with the right physics
  - CR-ENG-002: MODE_1 refuses to run without the licensed dataset
  - CR-ENG-004: conductor resistance carries its temperature coefficient
  - CR-ENG-005: a non-converged result yields no compliance verdict
  - CR-ENG-006: a running fan disqualifies MODE_1, with no override
  - CR-ENG-008: a joint is always its own entity
  - CR-ENG-010: no universal default contact resistance
  - CR-ENG-011: K_AC = 1.0 raises a visible warning
  - CR-ENG-013: °C arrives, kelvin is computed, both are reported
"""
from __future__ import annotations

import math

import pytest
from thermal_core.benchmarks.iec60890 import IEC60890Coefficients
from thermal_core.contract import (
    CONTRACT_SCHEMA_VERSION,
    ENGINE_VERSION,
    ContractError,
    ContractInput,
    JsonThermalSolver,
    content_hash,
    input_snapshot_from_json,
    limit_set_for_profiles,
    solve_json,
)
from thermal_core.heat_source import HeatSourceEntityType, LossCalculationSource
from thermal_core.reference_model import (
    ACB_ID,
    AMBIENT_K,
    BUSBAR_JOINT_ID,
    BUSBAR_SEGMENT_ID,
    CABLE_CHAMBER_ID,
    CONDUCTOR_ID,
    DEVICE_CHAMBER_ID,
    ENCLOSURE_DEPTH_M,
    ENCLOSURE_HEIGHT_M,
    ENCLOSURE_WIDTH_M,
    FAN_ID,
    MCCB_ID,
    m003_document,
)
from thermal_core.snapshot import (
    CalculationMode,
    OpeningSnapshot,
    SurfaceOrientation,
)

LICENSED_COEFFICIENTS = IEC60890Coefficients(
    c0=1.8,
    n=0.8,
    d=1.35,
    installation_factors={
        "VERTICAL": 0.9,
        "HORIZONTAL_UP": 1.4,
        "HORIZONTAL_DOWN": 0.5,
    },
    height_distribution=((0.0, 0.5), (0.5, 1.0), (1.0, 1.35)),
    dataset_version="TEST-DATASET-ONLY",
)
"""
Invented numbers, for testing the *structure* of the method only.

CR-ENG-002: the real IEC TR 60890 coefficients are licensed and are never
committed to this repository. These exist so the code path can be tested; they
must never be used for a real assessment.
"""


# ---------------------------------------------------------------------------
# Geometry mapping
# ---------------------------------------------------------------------------


class TestGeometryMapping:
    def test_six_faces_conserve_the_external_area(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        geometry = mapped.snapshot.geometry
        expected = 2 * (
            ENCLOSURE_WIDTH_M * ENCLOSURE_HEIGHT_M
            + ENCLOSURE_DEPTH_M * ENCLOSURE_HEIGHT_M
            + ENCLOSURE_WIDTH_M * ENCLOSURE_DEPTH_M
        )
        external = sum(s.area_m2 for s in geometry.surfaces if s.is_external)
        assert external == pytest.approx(expected)
        assert geometry.total_external_surface_area_m2 == pytest.approx(expected)

    def test_roof_belongs_to_the_top_compartment_only(self) -> None:
        """A lower tier does not touch the roof and gets none of its area."""
        mapped = input_snapshot_from_json(m003_document())
        roof = [
            s
            for s in mapped.snapshot.geometry.surfaces
            if s.orientation == SurfaceOrientation.HORIZONTAL_UP and s.is_external
        ]
        assert [s.compartment_id for s in roof] == [DEVICE_CHAMBER_ID]
        assert roof[0].area_m2 == pytest.approx(
            ENCLOSURE_WIDTH_M * ENCLOSURE_DEPTH_M
        )

    def test_floor_belongs_to_the_bottom_compartment_only(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        floor = [
            s
            for s in mapped.snapshot.geometry.surfaces
            if s.orientation == SurfaceOrientation.HORIZONTAL_DOWN and s.is_external
        ]
        assert [s.compartment_id for s in floor] == [CABLE_CHAMBER_ID]

    def test_restricted_face_is_marked(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        rear = [
            s for s in mapped.snapshot.geometry.surfaces if ":REAR:" in s.surface_id
        ]
        assert rear
        assert all(s.is_restricted for s in rear)
        assert not any(
            s.is_restricted
            for s in mapped.snapshot.geometry.surfaces
            if ":FRONT:" in s.surface_id
        )

    def test_declared_partition_becomes_a_conduction_surface(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        partitions = [
            s for s in mapped.snapshot.geometry.surfaces if not s.is_external
        ]
        assert len(partitions) == 1
        partition = partitions[0]
        assert {partition.compartment_id, partition.adjacent_compartment_id} == {
            CABLE_CHAMBER_ID,
            DEVICE_CHAMBER_ID,
        }
        # 10 % perforated, so 90 % of the shared plane conducts.
        shared = (ENCLOSURE_WIDTH_M - 0.004) * (ENCLOSURE_DEPTH_M - 0.004)
        assert partition.area_m2 == pytest.approx(shared * 0.9)

    def test_perforation_becomes_a_ventilation_path(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        internal = [
            o
            for o in mapped.snapshot.geometry.openings
            if o.from_compartment_id is not None and o.to_compartment_id is not None
        ]
        assert len(internal) == 1
        shared = (ENCLOSURE_WIDTH_M - 0.004) * (ENCLOSURE_DEPTH_M - 0.004)
        assert internal[0].free_area_m2 == pytest.approx(shared * 0.1)

    def test_undeclared_adjacency_is_warned_not_invented(self) -> None:
        """
        Two compartments that merely abut get no conduction path.

        Inventing one would cool the hot compartment through a wall the
        engineer never drew, and understating a rise is the failure mode this
        platform must not have.
        """
        document = m003_document()
        del document["enclosure"]["compartments"][0]["partitions"]
        mapped = input_snapshot_from_json(document)
        assert not [s for s in mapped.snapshot.geometry.surfaces if not s.is_external]
        assert any(code == "WARN-NO-PARTITION" for code, _ in mapped.warnings)

    def test_enclosure_without_compartments_becomes_one_volume(self) -> None:
        mapped = input_snapshot_from_json(m003_document(with_compartments=False))
        assert len(mapped.snapshot.geometry.compartments) == 1
        compartment = mapped.snapshot.geometry.compartments[0]
        assert compartment.width_m == pytest.approx(ENCLOSURE_WIDTH_M - 0.004)
        # Every heat source still lands somewhere.
        assert all(
            s.compartment_id == compartment.compartment_id
            for s in mapped.snapshot.heat_source_map.sources
        )

    def test_external_openings_attach_to_the_compartment_behind_them(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        external = [
            o
            for o in mapped.snapshot.geometry.openings
            if o.from_compartment_id is None or o.to_compartment_id is None
        ]
        by_height = {o.centroid_height_m: o for o in external}
        assert by_height[0.15].to_compartment_id == CABLE_CHAMBER_ID
        assert by_height[ENCLOSURE_HEIGHT_M].to_compartment_id == DEVICE_CHAMBER_ID


# ---------------------------------------------------------------------------
# Heat sources
# ---------------------------------------------------------------------------


class TestHeatSourceMapping:
    def test_every_entity_becomes_exactly_one_source(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        entity_ids = [s.entity_id for s in mapped.snapshot.heat_source_map.sources]
        assert sorted(entity_ids) == sorted(
            [ACB_ID, MCCB_ID, BUSBAR_SEGMENT_ID, BUSBAR_JOINT_ID, CONDUCTOR_ID]
        )

    def test_quadratic_device_scales_with_current_squared(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        acb = mapped.snapshot.heat_source_map.by_entity_id(ACB_ID)
        assert acb is not None
        # 250 W at 1600 A, running at 1200 A.
        assert acb.power_loss_w == pytest.approx(250.0 * (1200.0 / 1600.0) ** 2)

    def test_fixed_power_device_ignores_current(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        mccb = mapped.snapshot.heat_source_map.by_entity_id(MCCB_ID)
        assert mccb is not None
        assert mccb.power_loss_w == pytest.approx(60.0)

    def test_device_without_a_loss_model_is_rejected(self) -> None:
        document = m003_document()
        device = document["enclosure"]["devices"][0]
        device["power_at_rated_W"] = None
        with pytest.raises(ContractError, match="thermal_model"):
            input_snapshot_from_json(document)

    def test_busbar_segment_uses_rho_l_over_a(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        segment = mapped.snapshot.heat_source_map.by_entity_id(BUSBAR_SEGMENT_ID)
        assert segment is not None
        resistance = 1.72e-8 * 0.7 / 0.0012
        assert segment.power_loss_w == pytest.approx(1200.0**2 * resistance)
        # CR-ENG-004: the solver re-evaluates this at the bar's own temperature.
        assert segment.temperature_coefficient_per_k == pytest.approx(0.00393)
        assert segment.reference_temperature_k == pytest.approx(293.15)

    def test_busbar_surface_area_defaults_to_the_bar_perimeter(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        segment = mapped.snapshot.heat_source_map.by_entity_id(BUSBAR_SEGMENT_ID)
        assert segment is not None
        assert segment.surface_area_m2 == pytest.approx(2 * (0.1 + 0.012) * 0.7)

    def test_joint_is_a_separate_entity(self) -> None:
        """CR-ENG-008: a joint's loss is never folded into the bar."""
        mapped = input_snapshot_from_json(m003_document())
        joint = mapped.snapshot.heat_source_map.by_entity_id(BUSBAR_JOINT_ID)
        assert joint is not None
        assert joint.entity_type == HeatSourceEntityType.JOINT
        assert joint.calculation_source == LossCalculationSource.JOINT_RESISTANCE
        assert joint.power_loss_w == pytest.approx(1200.0**2 * 5.0e-6)

        segment = mapped.snapshot.heat_source_map.by_entity_id(BUSBAR_SEGMENT_ID)
        assert segment is not None
        bulk_only = 1200.0**2 * (1.72e-8 * 0.7 / 0.0012)
        assert segment.power_loss_w == pytest.approx(bulk_only)

    def test_conductor_uses_the_inlined_resistance(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        cable = mapped.snapshot.heat_source_map.by_entity_id(CONDUCTOR_ID)
        assert cable is not None
        assert cable.power_loss_w == pytest.approx(300.0**2 * 1.21e-4 * 2.5)

    def test_conductor_without_resolved_resistance_is_rejected(self) -> None:
        """CR-TECH-001: the engine cannot go and look it up."""
        document = m003_document()
        document["enclosure"]["conductors"][0]["resistance_ohm_per_m"] = None
        with pytest.raises(ContractError, match="resistance_ohm_per_m"):
            input_snapshot_from_json(document)

    def test_bundling_derates_capacity_not_dissipation(self) -> None:
        document = m003_document()
        document["enclosure"]["conductors"][0]["bundling_factor"] = 0.8
        mapped = input_snapshot_from_json(document)
        cable = mapped.snapshot.heat_source_map.by_entity_id(CONDUCTOR_ID)
        assert cable is not None
        assert cable.power_loss_w == pytest.approx(300.0**2 * 1.21e-4 * 2.5)
        assert mapped.entity_loading_factors[CONDUCTOR_ID] == pytest.approx(
            300.0 / (400.0 * 0.8)
        )

    def test_manufacturer_limit_is_carried_through(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        assert mapped.entity_limits_k[ACB_ID] == pytest.approx(105.0 + 273.15)
        # CR-ENG-010: the MCCB declares none, so none is invented for it.
        assert MCCB_ID not in mapped.entity_limits_k


# ---------------------------------------------------------------------------
# Contact resistance — CR-ENG-010 / DR-004
# ---------------------------------------------------------------------------


class TestContactResistanceHierarchy:
    def test_known_joint_without_a_resistance_is_rejected(self) -> None:
        document = m003_document()
        document["enclosure"]["busbar_runs"][0]["joints"][0][
            "contact_resistance_ref_ohm"
        ] = None
        with pytest.raises(ContractError, match="no default"):
            input_snapshot_from_json(document)

    def test_unknown_joint_without_a_sensitivity_range_is_rejected(self) -> None:
        document = m003_document()
        joint = document["enclosure"]["busbar_runs"][0]["joints"][0]
        joint["joint_condition"] = "UNKNOWN"
        joint["contact_resistance_ref_ohm"] = None
        with pytest.raises(ContractError, match="sensitivity_nominal_ohm"):
            input_snapshot_from_json(document)

    def test_unknown_joint_solves_at_nominal_and_says_so(self) -> None:
        document = m003_document()
        joint = document["enclosure"]["busbar_runs"][0]["joints"][0]
        joint["joint_condition"] = "UNKNOWN"
        joint["contact_resistance_ref_ohm"] = None
        joint["sensitivity_min_ohm"] = 3.0e-6
        joint["sensitivity_nominal_ohm"] = 8.0e-6
        joint["sensitivity_max_ohm"] = 2.0e-5
        mapped = input_snapshot_from_json(document)
        source = mapped.snapshot.heat_source_map.by_entity_id(BUSBAR_JOINT_ID)
        assert source is not None
        assert source.power_loss_w == pytest.approx(1200.0**2 * 8.0e-6)
        assert any(code == "WARN-010-JOINT-UNKNOWN" for code, _ in mapped.warnings)


# ---------------------------------------------------------------------------
# K_AC — CR-ENG-011 / DR-003
# ---------------------------------------------------------------------------


class TestKAcCorrection:
    def test_dc_only_segment_warns(self) -> None:
        result = solve_json(m003_document())
        warnings = result["k_ac_warnings"]
        assert len(warnings) == 1
        assert warnings[0]["segment_id"] == BUSBAR_SEGMENT_ID
        assert warnings[0]["warning_code"] == "K_AC_UNITY_FALLBACK"

    def test_qualified_k_ac_is_applied_and_does_not_warn(self) -> None:
        document = m003_document()
        segment = document["enclosure"]["busbar_runs"][0]["segments"][0]
        segment["k_ac_factor"] = 1.25
        segment["k_ac_source"] = "MANUFACTURER"
        mapped = input_snapshot_from_json(document)
        source = mapped.snapshot.heat_source_map.by_entity_id(BUSBAR_SEGMENT_ID)
        assert source is not None
        assert source.calculation_source == LossCalculationSource.AC_RESISTANCE_CALC
        assert source.power_loss_w == pytest.approx(
            1200.0**2 * (1.72e-8 * 0.7 / 0.0012) * 1.25
        )
        assert solve_json(document)["k_ac_warnings"] == []

    def test_k_ac_declared_as_not_applied_still_warns(self) -> None:
        """A declared K_AC of 1.0 is still DC-only, however it is labelled."""
        document = m003_document()
        segment = document["enclosure"]["busbar_runs"][0]["segments"][0]
        segment["k_ac_factor"] = 1.0
        segment["k_ac_source"] = "NOT_APPLIED"
        assert len(solve_json(document)["k_ac_warnings"]) == 1


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


class TestModeGating:
    def test_mode_1_without_the_licensed_dataset_fails(self) -> None:
        """CR-ENG-002: no dataset, no MODE 1 — and no invented numbers."""
        result = solve_json(m003_document("MODE_1"))
        assert result["status"] == "FAILED"
        assert "CR-ENG-002" in (result["failure_reason"] or "")
        assert result["temperatures"]["entities"] == []

    def test_mode_1_with_the_dataset_reports_the_iec_quantities(self) -> None:
        result = solve_json(
            m003_document("MODE_1"), iec60890_coefficients=LICENSED_COEFFICIENTS
        )
        assert result["status"] == "CONVERGED"
        mode_1 = result["mode_1_result"]
        assert mode_1 is not None
        assert mode_1["P_total_W"] > 0.0
        assert mode_1["effective_cooling_area_m2"] > 0.0
        # Δθ_top = d · Δθ_mid, and d >= 1.
        assert mode_1["delta_theta_e_K"] == pytest.approx(
            1.35 * mode_1["delta_theta_i_K"]
        )

    def test_running_fan_disqualifies_mode_1(self) -> None:
        """CR-ENG-006: automatic, with no user override."""
        result = solve_json(
            m003_document("MODE_1", with_fan=True),
            iec60890_coefficients=LICENSED_COEFFICIENTS,
        )
        assert result["status"] == "FAILED"
        assert "CR-ENG-006" in (result["failure_reason"] or "")

    def test_stopped_fan_does_not_disqualify_mode_1(self) -> None:
        result = solve_json(
            m003_document("MODE_1", with_fan=True, fan_state="STOPPED_WITH_DAMPER"),
            iec60890_coefficients=LICENSED_COEFFICIENTS,
        )
        assert result["status"] == "CONVERGED"

    def test_mode_3_without_a_running_fan_fails(self) -> None:
        result = solve_json(m003_document("MODE_3"))
        assert result["status"] == "FAILED"
        assert "MODE_3" in (result["failure_reason"] or "")

    def test_mode_3_finds_the_fan_operating_point(self) -> None:
        mapped = input_snapshot_from_json(m003_document("MODE_3", with_fan=True))
        forced = mapped.snapshot.boundary_conditions.forced_flow_m3_per_s
        assert len(forced) == 1
        flow = next(iter(forced.values()))
        # The curve runs from 0 to 0.15 m³/s; the operating point sits inside it.
        assert 0.0 < flow < 0.15

    def test_mode_3_moves_more_air_and_runs_cooler_than_mode_2(self) -> None:
        natural = solve_json(m003_document("MODE_2", with_fan=True))
        forced = solve_json(m003_document("MODE_3", with_fan=True))
        assert natural["status"] == forced["status"] == "CONVERGED"
        hottest = max(
            c["temperature_K"] for c in natural["temperatures"]["thermal_cells"]
        )
        hottest_forced = max(
            c["temperature_K"] for c in forced["temperatures"]["thermal_cells"]
        )
        assert hottest_forced < hottest

    def test_running_fan_in_mode_2_is_reported_not_silently_applied(self) -> None:
        mapped = input_snapshot_from_json(m003_document("MODE_2", with_fan=True))
        assert not mapped.snapshot.boundary_conditions.forced_flow_m3_per_s
        assert any(code == "WARN-FAN-NOT-DRIVEN" for code, _ in mapped.warnings)

    def test_blocked_fan_passes_no_air(self) -> None:
        mapped = input_snapshot_from_json(
            m003_document("MODE_2", with_fan=True, fan_state="FAILED_BLOCKED")
        )
        assert not [
            o for o in mapped.snapshot.geometry.openings if o.fan_id == FAN_ID
        ]

    def test_reverse_flow_turns_the_opening_around(self) -> None:
        """DR-005: reverse flow is a direction, never a clamp to zero."""
        forward = input_snapshot_from_json(m003_document("MODE_3", with_fan=True))
        reverse = input_snapshot_from_json(
            m003_document("MODE_3", with_fan=True, fan_state="REVERSE_FLOW_ESTIMATED")
        )

        def fan_opening(mapped: ContractInput) -> OpeningSnapshot:
            return next(
                o for o in mapped.snapshot.geometry.openings if o.fan_id == FAN_ID
            )

        # The fan is declared an OUTLET, so forward flow leaves the enclosure
        # and reverse flow brings ambient air in through the same aperture.
        assert fan_opening(forward).from_compartment_id is not None
        assert fan_opening(forward).to_compartment_id is None
        assert fan_opening(reverse).from_compartment_id is None
        assert fan_opening(reverse).to_compartment_id is not None

    def test_fan_motor_loss_is_a_heat_source(self) -> None:
        """IEC TR 60890 §11.1 counts it in P_tot, and so does the network."""
        with_fan = input_snapshot_from_json(m003_document("MODE_3", with_fan=True))
        without = input_snapshot_from_json(m003_document("MODE_3"))
        delta = (
            with_fan.snapshot.heat_source_map.total_power_loss_w()
            - without.snapshot.heat_source_map.total_power_loss_w()
        )
        assert delta == pytest.approx(18.0)

    def test_mode_4_directs_the_caller_to_the_adapter(self) -> None:
        result = solve_json(m003_document("MODE_4"))
        assert result["status"] == "FAILED"
        assert "cfd_export" in (result["failure_reason"] or "")


# ---------------------------------------------------------------------------
# Units — CR-ENG-013 / M0-10
# ---------------------------------------------------------------------------


class TestUnits:
    def test_celsius_in_kelvin_out(self) -> None:
        mapped = input_snapshot_from_json(m003_document())
        assert mapped.snapshot.boundary_conditions.ambient_temperature_k == (
            pytest.approx(AMBIENT_K)
        )

    def test_result_reports_both_scales_consistently(self) -> None:
        result = solve_json(m003_document())
        assert result["temperatures"]["ambient_K"] == pytest.approx(AMBIENT_K)
        for entity in result["temperatures"]["entities"]:
            assert entity["temperature_C"] == pytest.approx(
                entity["temperature_K"] - 273.15
            )
            assert entity["temperature_rise_K"] == pytest.approx(
                entity["temperature_K"] - AMBIENT_K
            )

    def test_altitude_lowers_the_ambient_pressure(self) -> None:
        document = m003_document()
        document["service_conditions"]["altitude_m"] = 2000.0
        mapped = input_snapshot_from_json(document)
        assert mapped.snapshot.boundary_conditions.ambient_pressure_pa < 101325.0
        assert mapped.snapshot.boundary_conditions.ambient_pressure_pa > 70000.0


# ---------------------------------------------------------------------------
# Result document
# ---------------------------------------------------------------------------


class TestResultDocument:
    def test_required_fields_are_present_and_versioned(self) -> None:
        result = solve_json(m003_document())
        assert result["schema_version"] == CONTRACT_SCHEMA_VERSION
        assert result["engine_version"] == ENGINE_VERSION
        assert re_semver(result["engine_version"])
        assert result["mode"] == "MODE_2"
        assert result["standard_profile"] == ["IEC_61439_2"]
        assert result["library_manifest_echo"]

    def test_converged_result_closes_its_energy_balance(self) -> None:
        result = solve_json(m003_document())
        assert result["status"] == "CONVERGED"
        assert abs(result["solver_summary"]["final_energy_imbalance_fraction"]) < 0.01

    def test_convergence_trace_is_numbered_from_one(self) -> None:
        trace = solve_json(m003_document())["solver_summary"]["convergence_trace"]
        assert trace
        assert [row["iteration"] for row in trace] == list(range(1, len(trace) + 1))

    def test_air_is_reported_as_cells_not_entities(self) -> None:
        """M0-04's entity_type enum has no AIR member, and rightly so."""
        result = solve_json(m003_document())
        cells = result["temperatures"]["thermal_cells"]
        assert {c["compartment_id"] for c in cells} == {
            CABLE_CHAMBER_ID,
            DEVICE_CHAMBER_ID,
        }
        assert all(c["temperature_K"] > 0.0 for c in cells)

    def test_each_entity_is_reported_once(self) -> None:
        result = solve_json(m003_document())
        ids = [e["entity_id"] for e in result["temperatures"]["entities"]]
        assert len(ids) == len(set(ids))

    def test_entity_types_use_the_m004_vocabulary(self) -> None:
        result = solve_json(m003_document())
        by_id = {
            e["entity_id"]: e["entity_type"]
            for e in result["temperatures"]["entities"]
        }
        assert by_id[ACB_ID] == "DEVICE"
        assert by_id[BUSBAR_SEGMENT_ID] == "BUSBAR_SEGMENT"
        assert by_id[BUSBAR_JOINT_ID] == "BUSBAR_JOINT"
        assert by_id[CONDUCTOR_ID] == "CONDUCTOR"

    def test_internal_surfaces_are_not_reported_as_accessible(self) -> None:
        """
        Only the outer face of a wall is operator-accessible.

        The inner face is an internal node of the wall model; reporting it
        under the same entity_id would put two temperatures on one object, and
        checking it against the 55 K accessible-surface limit would be wrong.
        """
        result = solve_json(m003_document())
        surfaces = [
            e
            for e in result["temperatures"]["entities"]
            if e["entity_type"] == "SURFACE"
        ]
        assert surfaces
        assert len({s["entity_id"] for s in surfaces}) == len(surfaces)
        assert all("inner face" not in (s["name"] or "") for s in surfaces)
        assert all("partition" not in (s["name"] or "") for s in surfaces)

    def test_airflow_is_reported_for_a_ventilated_enclosure(self) -> None:
        airflow = solve_json(m003_document())["airflow"]
        assert airflow is not None
        assert airflow["total_flow_rate_m3s"] > 0.0
        assert all(
            f["direction"] in ("IN", "OUT") for f in airflow["opening_flows"]
        )

    def test_mapping_warnings_reach_the_report(self) -> None:
        document = m003_document()
        del document["enclosure"]["compartments"][0]["partitions"]
        checks = solve_json(document)["compliance"]["checks"]
        assert any(c["check_id"] == "WARN-NO-PARTITION" for c in checks)


# ---------------------------------------------------------------------------
# Compliance — CR-ENG-005 / CR-ENG-009
# ---------------------------------------------------------------------------


class TestCompliance:
    def test_overloaded_joint_fails_and_becomes_a_hotspot(self) -> None:
        """
        The fixture's joint is a real finding, not a contrived one.

        5 µΩ at 1200 A dissipates 7 W into 0.02 m² of bolted copper, which
        pushes the connection past the 70 K limit while the bar it joins sits
        comfortably below it. This is exactly the result CR-ENG-008 exists to
        make visible.
        """
        result = solve_json(m003_document())
        assert result["compliance"]["overall_compliant"] is False
        joint_checks = [
            c
            for c in result["compliance"]["checks"]
            if c["entity_id"] == BUSBAR_JOINT_ID
        ]
        assert joint_checks and joint_checks[0]["status"] == "FAIL"
        assert any(
            h["entity_id"] == BUSBAR_JOINT_ID and h["severity"] == "CRITICAL"
            for h in result["hotspots"]
        )

    def test_a_failing_entity_gets_a_derating_recommendation(self) -> None:
        result = solve_json(m003_document())
        derating = {d["entity_id"]: d for d in result["derating"]}
        assert BUSBAR_JOINT_ID in derating
        advice = derating[BUSBAR_JOINT_ID]
        assert advice["action_required"] is True
        assert 0.0 < advice["recommended_loading_factor"] < 1.0

    def test_manufacturer_limit_outranks_the_table(self) -> None:
        result = solve_json(m003_document())
        acb_checks = [
            c for c in result["compliance"]["checks"] if c["entity_id"] == ACB_ID
        ]
        assert acb_checks
        assert acb_checks[0]["check_id"] == "TEMP_LIMIT_MANUFACTURER"
        assert acb_checks[0]["limit_K"] == pytest.approx(105.0 + 273.15 - AMBIENT_K)

    def test_device_without_a_manufacturer_limit_gets_no_check(self) -> None:
        """CR-ENG-010: no universal default is better than a wrong one."""
        result = solve_json(m003_document())
        assert not [
            c for c in result["compliance"]["checks"] if c["entity_id"] == MCCB_ID
        ]

    def test_non_converged_result_issues_no_verdict(self) -> None:
        """CR-ENG-005: the UI shows RESULT INVALID and no compliance report."""
        document = m003_document()
        document["solver_settings"]["max_inner_iterations"] = 1
        result = solve_json(document)
        assert result["status"] == "NON_CONVERGED"
        assert result["compliance"]["overall_compliant"] is False
        assert [c["status"] for c in result["compliance"]["checks"]] == [
            "NOT_APPLICABLE"
        ]
        assert result["hotspots"] == []
        assert result["derating"] == []
        assert "NON_CONVERGED" in (result["failure_reason"] or "")

    def test_a_sound_model_passes(self) -> None:
        """Halve the currents and the same enclosure is compliant."""
        document = m003_document()
        document["enclosure"]["busbar_runs"][0]["current_A"] = 600.0
        for device in document["enclosure"]["devices"]:
            device["load_current_A"] /= 2.0
        document["enclosure"]["devices"][1]["power_at_rated_W"] = 30.0
        document["enclosure"]["conductors"][0]["current_A"] = 150.0
        result = solve_json(document)
        assert result["status"] == "CONVERGED"
        assert result["compliance"]["overall_compliant"] is True
        assert not [h for h in result["hotspots"] if h["severity"] == "CRITICAL"]

    def test_an_implausible_temperature_stops_the_solve(self) -> None:
        """
        A joint dissipating 72 W into 0.02 m² would glow.

        The solver refuses rather than reporting it: a four-figure temperature
        means the input is wrong, and a compliance verdict computed from it
        would be worse than no verdict at all (THERM-NET-001 §12).
        """
        document = m003_document()
        document["enclosure"]["busbar_runs"][0]["joints"][0][
            "contact_resistance_ref_ohm"
        ] = 5.0e-5
        result = solve_json(document)
        assert result["status"] == "FAILED"
        assert "plausible range" in (result["failure_reason"] or "")

    def test_profile_selects_the_limit_set(self) -> None:
        """CR-ENG-009: interpretation is standard-profile-aware."""
        assert limit_set_for_profiles(["IEC_61439_2"]).profile.value == "IEC_61439_2"
        assert limit_set_for_profiles(["IEC_61439_1"]).profile.value == "IEC_61439_1"
        # The assembly-specific standard wins when both are named.
        assert (
            limit_set_for_profiles(["IEC_61439_1", "IEC_61439_2"]).profile.value
            == "IEC_61439_2"
        )


# ---------------------------------------------------------------------------
# Determinism and the solver interface
# ---------------------------------------------------------------------------


class TestEngineContract:
    def test_the_same_input_gives_the_same_answer(self) -> None:
        first = solve_json(m003_document())
        second = solve_json(m003_document())
        for document in (first, second):
            document["solver_summary"].pop("wall_clock_s")
        assert content_hash(first) == content_hash(second)

    def test_run_id_is_derived_when_not_supplied(self) -> None:
        assert solve_json(m003_document())["run_id"] == (
            solve_json(m003_document())["run_id"]
        )

    def test_explicit_run_id_wins(self) -> None:
        result = solve_json(m003_document(), run_id="run-0001")
        assert result["run_id"] == "run-0001"

    def test_solver_interface_accepts_and_returns_json(self) -> None:
        """CR-TECH-001: versioned JSON in, versioned JSON out."""
        solver = JsonThermalSolver(run_id="run-0002")
        result = solver.solve(m003_document())
        assert result["run_id"] == "run-0002"
        assert result["status"] == "CONVERGED"

    def test_an_unknown_schema_version_is_refused(self) -> None:
        document = m003_document()
        document["schema_version"] = "2.0"
        with pytest.raises(ContractError, match="schema_version"):
            input_snapshot_from_json(document)

    def test_solver_settings_are_carried_across(self) -> None:
        mapped = input_snapshot_from_json(m003_document("MODE_2"))
        settings = mapped.snapshot.solver_settings
        assert settings.calculation_mode == CalculationMode.MODE_2
        assert settings.max_iterations == 300
        assert settings.convergence_tolerance_k == pytest.approx(0.01)
        assert settings.relaxation_factor == pytest.approx(0.6)

    def test_library_manifest_is_pinned_and_echoed(self) -> None:
        """CR-TECH-002 / M0-09: the audit trail names what was used."""
        mapped = input_snapshot_from_json(m003_document())
        assert mapped.snapshot.library_manifest["device_library"].startswith("1.0.0@")
        echo = solve_json(m003_document())["library_manifest_echo"]
        assert echo == mapped.snapshot.library_manifest


def re_semver(value: str) -> bool:
    """M0-04 requires engine_version to match ^\\d+\\.\\d+\\.\\d+$."""
    parts = value.split(".")
    return len(parts) == 3 and all(part.isdigit() for part in parts)


def test_module_exposes_no_web_framework_dependency() -> None:
    """CR-TECH-001, enforced rather than asserted in prose."""
    import sys

    import thermal_core.contract  # noqa: F401

    forbidden = {"fastapi", "sqlalchemy", "starlette", "pydantic", "httpx"}
    assert not forbidden & set(sys.modules)


def test_no_nan_or_infinity_reaches_the_result() -> None:
    """A JSON document carrying NaN is not valid JSON, and not a result."""
    result = solve_json(m003_document())

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, float):
            assert math.isfinite(node)

    walk(result)


def test_a_blocked_mode_still_reports_its_mapping_warnings() -> None:
    """
    The warnings often say what to fix before trying again.

    A MODE_1 run refused for forced ventilation still has something to tell
    the engineer about the model it refused.
    """
    document = m003_document("MODE_1", with_fan=True)
    del document["enclosure"]["compartments"][0]["partitions"]
    result = solve_json(document, iec60890_coefficients=LICENSED_COEFFICIENTS)
    assert result["status"] == "FAILED"
    check_ids = {c["check_id"] for c in result["compliance"]["checks"]}
    assert "MODE_NOT_APPLICABLE" in check_ids
    assert "WARN-NO-PARTITION" in check_ids

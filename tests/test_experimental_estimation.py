import json
from pathlib import Path
import subprocess
import sys

import pytest

from check_evidence import DIRECT, INDIRECT, check_direct, check_estimate, check_indirect
from fixtures.synthetic_evidence_v15 import MODEL, SOURCE, TARGET, catalog, comparison, independent, member


def candidate_input(origin, value, unit):
    return {
        "target_property_id": TARGET,
        "target_conditions": {"temperature_K": 298},
        "predictor": {
            "origin": origin, "property_id": SOURCE, "value": value, "scale": "linear", "unit": unit,
            "source_reference": "Synthetic candidate fixture",
            "md_conditions": {"state": "amorphous"}, "md_dataset_revision": "synthetic:md",
        },
    }


def set_fit_units(row, x_unit, y_unit):
    row.update(x_unit=x_unit, y_unit=y_unit)
    row["linear_fit"].update(a_unit=f"({y_unit})/({x_unit})", b_unit=y_unit)


@pytest.fixture
def direct_case():
    evidence, registry = comparison(DIRECT), catalog()
    row = evidence["record"]
    set_fit_units(row, "g/cm^3", "g/cm^3")
    row.update(definition_compatibility="exact", linear_fit_a=.9, linear_fit_b=.1)
    row["applicability"].update(md_conditions={"state": "amorphous"}, experimental_conditions={"temperature_K": 298})
    row["linear_fit"]["x_range"] = {"min": 1, "max": 2}
    evidence["polyomics_data_revision"] = registry["polyomics_data_revision"] = "synthetic:md"
    return evidence, registry, candidate_input("md_simulation", 1.5, "g/cm³")


@pytest.fixture
def indirect_case():
    evidence, registry = comparison(INDIRECT), catalog()
    request = candidate_input("source_surrogate_prediction", 2, "K")
    request["target_direction"] = "higher"
    provenance = {"model_id": MODEL, "model_revision": "synthetic:v2", "aggregation": "ensemble_mean",
                  "preprocessing": "synthetic:feature-v1", "prediction_mode": "out_of_fold"}
    evidence["record"]["linear_fit"]["source_predictor"] = provenance.copy()
    request["predictor"]["source_predictor"] = provenance.copy()
    return evidence, registry, request


def test_public_direct_supports_point_estimate_without_independent_validation(direct_case):
    evidence, registry, request = direct_case
    outcome = check_estimate(*direct_case)
    assert outcome["value"] == pytest.approx(1.45)
    assert (outcome["status"], outcome["level"], outcome["applicability"]) == ("eligible_exploratory", "B", "matched")
    assert outcome["unit"] == "g/cm^3" and outcome["evidence_id"] == evidence["record"]["evidence_id"]
    assert outcome["reason_codes"] == ["UNQUANTIFIED_UNCERTAINTY", "INDEPENDENT_EXPERIMENTAL_VALIDATION_NOT_PROVIDED"]
    assert outcome["experimental_compliance_established"] is False
    assert check_direct(evidence, catalog=registry)["linear_fit_interpretation"] == "descriptive_parity"


@pytest.mark.parametrize(("a", "b", "x", "target", "direction", "prefilter"), [
    (2, 0, 1.5, 3, "increasing", {"operator": ">=", "x_bound": 1.5}),
    (-2, 0, 1.5, -3, "decreasing", {"operator": "<=", "x_bound": 1.5}),
    (0, 1, 1.5, 1, "constant", {"constant_meets_exploratory_minimum": True}),
    (0, 0, 1.5, 1, "constant", {"constant_meets_exploratory_minimum": False}),
])
def test_affine_sort_and_candidate_minimum(direct_case, a, b, x, target, direction, prefilter):
    evidence, _, request = direct_case
    evidence["record"].update(linear_fit_a=a, linear_fit_b=b)
    request["predictor"]["value"] = x
    request["target_minimum"] = target
    result = check_estimate(*direct_case)
    assert result["value"] == pytest.approx(a * x + b)
    assert result["slope_direction"] == direction
    assert result["candidate_x_prefilter"] == prefilter
    assert not result["experimental_compliance_established"]


@pytest.mark.parametrize("invalid", [None, True, "0.9", float("nan"), float("inf")])
@pytest.mark.parametrize("key", ["linear_fit_a", "linear_fit_b"])
def test_invalid_coefficient_does_not_invalidate_existing_correlation(direct_case, key, invalid):
    evidence, registry, _ = direct_case
    evidence["record"][key] = invalid
    assert check_estimate(*direct_case)["reason_codes"] == ["FIT_UNAVAILABLE"]
    assert "pearson_r" in check_direct(evidence, catalog=registry)["reportable_comparison_metrics"]


@pytest.mark.parametrize("fit_change", [
    {"linear_fit_status": "not_provided"}, {"linear_fit_method": "unverified"}, {"linear_fit_n_pairs": 1},
    {"metric_availability": {"linear_fit_a": False}},
])
def test_unpublished_or_invalid_fit_cannot_be_applied(direct_case, fit_change):
    direct_case[0]["record"].update(fit_change)
    decision = check_estimate(*direct_case)
    assert decision["value"] is None
    assert decision["reason_codes"] == ["FIT_UNAVAILABLE"]


@pytest.mark.parametrize("invalid", [None, True, "1.5", float("nan"), float("inf")])
def test_predictor_must_be_finite_and_numeric(direct_case, invalid):
    direct_case[2]["predictor"]["value"] = invalid
    assert check_estimate(*direct_case)["reason_codes"] == ["PREDICTOR_VALUE_INVALID"]


@pytest.mark.parametrize("r2", [None, 2.0, True])
def test_invalid_or_missing_optional_r_squared_does_not_block_estimate(direct_case, r2):
    direct_case[0]["record"]["linear_fit_r2"] = r2
    assert check_estimate(*direct_case)["value"] == pytest.approx(1.45)
    assert "linear_fit_r2" not in check_direct(direct_case[0], catalog=direct_case[1])["reportable_linear_fit_metrics"]


def test_nonfinite_result_is_rejected(direct_case):
    direct_case[0]["record"]["linear_fit_a"] = 1.7e308
    decision = check_estimate(*direct_case)
    assert decision["value"] is None
    assert decision["reason_codes"] == ["NONFINITE_ESTIMATE"]


@pytest.mark.parametrize(("changes", "reason"), [
    ({"origin": "source_surrogate_prediction"}, "PREDICTOR_ORIGIN_MISMATCH"),
    ({"property_id": "other:property"}, "PROPERTY_ID_MISMATCH"),
    ({"scale": None}, "SCALE_MISMATCH_OR_UNSUPPORTED"),
    ({"scale": "log10"}, "SCALE_MISMATCH_OR_UNSUPPORTED"),
    ({"unit": "kg/m^3"}, "PREDICTOR_UNIT_MISMATCH_OR_VALUE_OVERFLOW"),
    ({"unit": None}, "PREDICTOR_UNIT_MISMATCH_OR_VALUE_OVERFLOW"),
    ({"source_reference": None}, "PREDICTOR_PROVENANCE_UNVERIFIED"),
    ({"md_conditions": {"state": "crystalline"}}, "CONDITIONS_MISMATCH"),
    ({"value": 2.01}, "DOMAIN_INCOMPATIBLE"),
])
def test_unverified_or_incompatible_predictor_is_not_applied(direct_case, changes, reason):
    direct_case[2]["predictor"].update(changes)
    result = check_estimate(*direct_case)
    assert result["value"] is None and result["reason_codes"] == [reason]


def test_documented_temperature_conversion_applies_affine_offset(direct_case):
    evidence, _, request = direct_case
    row = evidence["record"]
    set_fit_units(row, "K", "K")
    row["linear_fit"]["x_range"] = {"min": 273, "max": 350}
    row.update(linear_fit_a=1, linear_fit_b=10)
    request["predictor"].update(value=25, unit="°C")
    result = check_estimate(*direct_case)
    assert result["predictor_value_on_fit_scale"] == pytest.approx(298.15)
    assert result["value"] == pytest.approx(308.15)


def test_missing_domain_or_revision_yields_conditional_estimate(direct_case):
    evidence, registry, _ = direct_case
    del evidence["record"]["linear_fit"]["x_range"]
    evidence["polyomics_data_revision"] = registry["polyomics_data_revision"] = "not_recorded"
    result = check_estimate(*direct_case)
    assert result["status"] == "conditional_exploratory"
    assert result["polyomics_data_revision"] == "not_recorded"
    assert {"DOMAIN_UNKNOWN", "ORIGINAL_MD_REVISION_UNKNOWN"} <= set(result["reason_codes"])
    assert result["value"] == pytest.approx(1.45)


def test_physical_range_failure_does_not_clip_output(direct_case):
    direct_case[0]["record"]["applicability"]["y_physical_range"] = {"min": 0, "max": 1}
    result = check_estimate(*direct_case)
    assert result["status"] == "incompatible" and result["value"] is None
    assert result["reason_codes"] == ["Y_PHYSICAL_RANGE_VIOLATION"]


@pytest.mark.parametrize("definition", ["unknown", "partial_match_polar_plus_hydrogen_bonding_vs_delta_p"])
def test_matching_units_and_caller_permission_do_not_establish_definitions(direct_case, definition):
    direct_case[0]["record"]["definition_compatibility"] = definition
    direct_case[2].update(allow_prediction=True, property_definitions_match=True)
    assert check_estimate(*direct_case)["reason_codes"] == ["PROPERTY_DEFINITION_UNVERIFIED"]


def test_10ghz_definition_requires_published_target_conditions(direct_case):
    evidence, _, request = direct_case
    row = evidence["record"]
    row["definition_compatibility"] = "conditional_match_zero_humidity_extrapolation"
    conditions = {"frequency_GHz": 10, "humidity": "extrapolated_to_zero"}
    row["applicability"].update(experimental_conditions={**conditions, "source_doi": "synthetic:study"},
                                definition_compatibility_detail="Synthetic demonstration of published conditions.")
    request["target_conditions"] = conditions.copy()
    assert check_estimate(*direct_case)["level"] == "B"
    request["target_conditions"]["frequency_GHz"] = 1
    assert check_estimate(*direct_case)["reason_codes"] == ["CONDITIONS_MISMATCH"]
    request["target_conditions"] = {"frequency_GHz": 10}
    assert check_estimate(*direct_case)["reason_codes"] == ["PROPERTY_DEFINITION_UNVERIFIED"]


def reliability_rule(effect):
    return {"applies_to": "md_calculated_property", "property_id": SOURCE, "effect": effect,
            "operator": ">", "threshold": 800, "unit": "K"}


@pytest.mark.parametrize(("effect", "expected"), [
    ("limited_reliability", "conditional_exploratory"), ("prohibit_inference", "prohibited"),
])
def test_reliability_rule_targets_md_axis_after_unit_conversion(direct_case, effect, expected):
    evidence, registry, request = direct_case
    row = evidence["record"]
    set_fit_units(row, "K", "K")
    row["linear_fit"]["x_range"] = {"min": 700, "max": 1000}
    registry["properties"][0]["md_value_reliability_cautions"] = [reliability_rule(effect)]
    row.update(linear_fit_a=.5, linear_fit_b=0)
    request["predictor"].update(value=550, unit="°C")
    request["target_minimum"] = 350
    result = check_estimate(*direct_case)
    assert result["status"] == expected and not result["experimental_compliance_established"]
    assert result.get("candidate_x_prefilter") is None
    if effect == "limited_reliability":
        assert result["value"] == pytest.approx(411.575)
        assert "MD_VALUE_RELIABILITY_CAUTION" in result["reason_codes"]
    else:
        assert result["value"] is None and result["reason_codes"] == ["RELIABILITY_RULE_PROHIBITS_INFERENCE"]


def test_no_experimental_y_caution_from_md_threshold(direct_case):
    evidence, registry, request = direct_case
    row = evidence["record"]
    set_fit_units(row, "K", "K")
    row["linear_fit"]["x_range"] = {"min": 700, "max": 1000}
    row.update(linear_fit_a=2, linear_fit_b=0)
    registry["properties"][0]["md_value_reliability_cautions"] = [reliability_rule("prohibit_inference")]
    request["predictor"].update(value=800, unit="K")
    assert check_estimate(*direct_case)["value"] == 1600


def test_explicit_policy_restriction_supersedes_mathematics(direct_case):
    evidence, _, request = direct_case
    evidence["record"]["applicability"]["quantitative_use"] = "prohibited"
    request["allow_prediction"] = True
    result = check_estimate(*direct_case)
    assert result["status"] == "prohibited" and result["value"] is None
    assert result["reason_codes"] == ["POLICY_RESTRICTED"]


@pytest.mark.parametrize("mutator", [
    lambda evidence, registry: evidence["record"].update(status="retracted"),
    lambda evidence, registry: evidence["record"].update(visibility="private"),
    lambda evidence, registry: evidence["record"].update(y_origin="target_predicted_experiment"),
    lambda evidence, registry: registry.update(release_id="synthetic:other"),
    lambda evidence, registry: registry.update(polyomics_data_revision="synthetic:other"),
    lambda evidence, registry: evidence.update(api_contract_version="1.1"),
    lambda evidence, registry: evidence.update(evidence_schema_version="1.2.0"),
    lambda evidence, registry: evidence.update(ok=False),
])
def test_nonpublic_mixed_or_incompatible_contract_fails_closed(direct_case, mutator):
    mutator(*direct_case[:2])
    result = check_estimate(*direct_case)
    assert result["status"] == "unavailable" and result["evidence_id"] is None
    assert result["value"] is None


def test_indirect_exact_authorized_predictor_remains_exploratory(indirect_case):
    indirect_case[2]["independent_experimental_validation"] = True
    result = check_estimate(*indirect_case)
    assert result["value"] == pytest.approx(-.5)
    assert (result["status"], result["level"], result["unit"]) == ("conditional_exploratory", "B", "MPa")
    assert result["validation_scope"] == "independent_experimental_validation_not_provided"


def test_observed_md_caution_is_not_transferred_to_source_prediction(indirect_case):
    evidence, registry, request = indirect_case
    registry["properties"][0]["md_value_reliability_cautions"] = [reliability_rule("prohibit_inference")]
    evidence["record"].update(linear_fit_a=1, linear_fit_b=0)
    request["predictor"]["value"] = 900
    assert check_estimate(*indirect_case)["value"] == 900


@pytest.mark.parametrize("field", ["model_id", "model_revision", "aggregation", "preprocessing", "prediction_mode"])
def test_unverified_source_provenance_is_proxy_only(indirect_case, field):
    indirect_case[2]["predictor"]["source_predictor"][field] = "different"
    result = check_estimate(*indirect_case)
    assert result["status"] == "proxy_only" and result["value"] is None
    assert result["reason_codes"] == ["MODEL_IDENTITY_UNVERIFIED"]


def test_missing_source_predictor_is_proxy_only_and_leakage_is_unavailable(indirect_case):
    evidence, _, request = indirect_case
    del request["predictor"]
    assert check_estimate(*indirect_case)["reason_codes"] == ["SOURCE_PREDICTOR_UNAVAILABLE"]
    evidence["record"]["trained_on_experimental_target_labels"] = True
    assert check_estimate(*indirect_case)["status"] == "unavailable"


@pytest.mark.parametrize("has_independent", [False, True])
def test_indirect_md_substitution_stays_proxy_with_member_or_independent_md_metrics(indirect_case, has_independent):
    evidence, registry, request = indirect_case
    row = evidence["record"]
    request["predictor"]["origin"] = "md_simulation"
    set_fit_units(row, "K", "K")
    holdout = independent() if has_independent else None
    if holdout:
        row["source_model_validation_evidence_id"] = holdout["record"]["evidence_id"]
    interpretation = check_indirect(evidence, catalog=registry, member_validation=member(), independent_validation=holdout)
    assert interpretation["source_member_validation_metrics_available"]
    assert interpretation["source_independent_validation_metrics_available"] is has_independent
    decision = check_estimate(*indirect_case)
    assert decision["status"] == "proxy_only" and decision["value"] is None
    assert decision["reason_codes"] == ["PREDICTOR_ORIGIN_MISMATCH"]
    assert decision["validation_scope"] == "independent_experimental_validation_not_provided"


def test_proxy_cue_requires_matching_property_and_target(indirect_case):
    request = indirect_case[2]
    request["predictor"].update(origin="md_simulation", property_id="unrelated:property")
    assert "proxy_direction_hint" not in check_estimate(*indirect_case)
    request["predictor"]["property_id"] = SOURCE
    request["target_property_id"] = "unrelated:target"
    assert "proxy_direction_hint" not in check_estimate(*indirect_case)


@pytest.mark.parametrize(("pearson", "spearman", "target_direction", "expected"), [
    (-.7, -.8, "higher", "lower"), (-.7, -.8, "lower", "higher"),
    (.5, -.5, "higher", None), (None, 0, "higher", None),
])
def test_proxy_direction_uses_reportable_association_signs(indirect_case, pearson, spearman, target_direction, expected):
    evidence, _, request = indirect_case
    evidence["record"].update(pearson_r=pearson, spearman_rho=spearman)
    request["predictor"]["origin"] = "md_simulation"
    request["target_direction"] = target_direction
    assert check_estimate(*indirect_case)["proxy_direction_hint"] == expected


def test_cli_adds_estimate_without_changing_previous_report(direct_case):
    evidence, registry, request = direct_case
    script = Path(__file__).resolve().parents[1] / "skills" / "polyomics-search" / "scripts" / "check_evidence.py"
    command = [sys.executable, str(script)]
    payload = {"record": evidence, "catalog": registry}
    baseline = subprocess.run(command, input=json.dumps(payload), capture_output=True, text=True, check=True)
    new = subprocess.run(command, input=json.dumps({**payload, "estimate_request": request}),
                         capture_output=True, text=True, check=True)
    result = json.loads(new.stdout)
    assert result.pop("estimate")["value"] == pytest.approx(1.45)
    assert result == json.loads(baseline.stdout)

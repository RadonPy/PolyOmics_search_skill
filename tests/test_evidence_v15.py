import json
from pathlib import Path
import subprocess
import sys

import pytest

from check_evidence import DIRECT, INDIRECT, check_direct, check_indirect
from fixtures.synthetic_evidence_v15 import catalog, comparison, independent, member, spec


@pytest.mark.parametrize("slope,intercept", [(-.3, 0), (0, -.3), (0, 0), (.9, .4)])
def test_direct_fit_is_separate_from_uncorrected_parity(slope, intercept):
    envelope = comparison(DIRECT)
    envelope["record"].update(linear_fit_a=slope, linear_fit_b=intercept)
    result = check_direct(envelope, catalog=catalog())
    assert result["linear_fit_available"] and result["linear_fit_interpretation"] == "descriptive_parity"
    assert "linear_fit_r2" in result["reportable_linear_fit_metrics"]
    assert "r2" in result["reportable_comparison_metrics"]
    assert result["linear_fit_slope_unit"] == "dimensionless" and result["linear_fit_intercept_unit"] == "K"


@pytest.mark.parametrize("value", [None, True, "1", float("inf"), float("-inf"), float("nan")])
@pytest.mark.parametrize("key", ["linear_fit_a", "linear_fit_b"])
def test_invalid_coefficient_does_not_remove_association(key, value):
    envelope = comparison(INDIRECT)
    envelope["record"][key] = value
    result = check_indirect(envelope, catalog=catalog())
    assert result["compatible"] and not result["linear_fit_available"]
    assert "pearson_r" in result["reportable_comparison_metrics"]
    assert result["reportable_association_errors"] == []


@pytest.mark.parametrize("updates,warning", [
    ({"linear_fit_status": "undefined_constant_md"}, "LINEAR_FIT_UNAVAILABLE"),
    ({"linear_fit_method": "unknown"}, "LINEAR_FIT_METADATA_UNVERIFIED"),
    ({"x_unit": "unknown"}, "LINEAR_FIT_METADATA_UNVERIFIED"),
    ({"linear_fit_n_pairs": 1}, "LINEAR_FIT_INVALID"),
    ({"linear_fit_n_pairs": 17}, "LINEAR_FIT_INVALID"),
    ({"linear_fit_a": None, "linear_fit_b": None}, "LINEAR_FIT_INVALID"),
])
def test_bad_fit_status_method_scale_or_count(updates, warning):
    envelope = comparison(DIRECT)
    envelope["record"].update(updates)
    result = check_direct(envelope, catalog=catalog())
    assert not result["linear_fit_available"] and warning in result["warnings"]


@pytest.mark.parametrize("r2", [None, 1.03, -0.05, "0.1"])
def test_fit_r2_is_optional_and_independently_checked(r2):
    envelope = comparison(DIRECT)
    envelope["record"]["linear_fit_r2"] = r2
    result = check_direct(envelope, catalog=catalog())
    assert result["linear_fit_available"]
    assert result["reportable_linear_fit_metrics"] == ["linear_fit_a", "linear_fit_b"]
    assert ("LINEAR_FIT_R2_INVALID" in result["warnings"]) is (r2 is not None)


def test_dynamic_fit_definition_and_conflicting_definition():
    envelope, definitions = comparison(DIRECT), catalog()
    key = "fitted_synthetic_metric"
    envelope["record"].update({key: .5, "undeclared_fit": .2})
    registry = definitions["metrics_registry"]["metric_availability"][DIRECT]
    registry[key] = spec(category="linear_fit", method="ols_with_intercept", fit_scope="in_sample_descriptive",
                         min_count=3, unit_basis="dimensionless")
    result = check_direct(envelope, catalog=definitions)
    assert key in result["reportable_linear_fit_metrics"] and "undeclared_fit" not in result["reportable_linear_fit_metrics"]
    del registry[key]["unit_basis"]
    assert key not in check_direct(envelope, catalog=definitions)["reportable_linear_fit_metrics"]
    registry["linear_fit_b"]["fit_scope"] = "validated_other_scale"
    assert not check_direct(envelope, catalog=definitions)["linear_fit_available"]


@pytest.mark.parametrize("overrides,reason", [
    ({"x_origin": "md_simulation"}, "INCOMPATIBLE_INDIRECT_AXES"),
    ({"trained_on_experimental_target_labels": True}, "SOURCE_ONLY_TRAINING_UNVERIFIED"),
    ({"same_private_structure": None}, "STRUCTURE_PAIRING_UNVERIFIED"),
    ({"status": "retracted"}, "PUBLIC_CONTRACT_OR_STATUS_UNVERIFIED"),
    ({"visibility": "private"}, "PUBLIC_CONTRACT_OR_STATUS_UNVERIFIED"),
])
def test_incompatible_indirect_cannot_be_rescued_by_fit(overrides, reason):
    envelope = comparison(INDIRECT)
    envelope["record"].update(overrides)
    assert check_indirect(envelope, catalog=catalog()) == {"compatible": False, "reason": reason}


@pytest.mark.parametrize(("flag", "expected"), [(None, "unknown"), (True, "unknown"), (False, "in_sample_or_non_independent")])
def test_member_match_is_not_an_independent_holdout(flag, expected):
    envelope = comparison(INDIRECT)
    envelope["record"]["source_member_validation"]["is_out_of_sample"] = flag
    result = check_indirect(envelope, catalog=catalog())
    assert result["source_member_validation_status"] == "verified"
    assert result["source_member_validation_scope"] == "member_diagnostics"
    assert result["source_member_validation_independence"] == expected
    assert result["reportable_source_member_validation_metrics"] == ["mae_mean", "r2_mean"]
    assert result["source_independent_validation_status"] == "not_provided"
    assert not result["source_validation_matches"]


@pytest.mark.parametrize("patch", [{"n_seeds_expected": 0}, {"mae_mean": None, "r2_mean": float("nan")},
                                   {"mae_n_seeds": 0, "r2_n_seeds": 0}, {"seedwise_n_test_min": 0}])
def test_link_with_no_usable_member_metrics(patch):
    envelope = comparison(INDIRECT)
    envelope["record"]["source_member_validation"].update(patch)
    result = check_indirect(envelope, catalog=catalog())
    assert result["source_member_validation_matches"]
    assert result["source_member_validation_status"] == "metrics_unavailable"
    assert not result["source_member_validation_metrics_available"]


def bind_independent(envelope):
    linked = independent()
    envelope["record"]["source_model_validation"] = dict(linked["record"])
    envelope["record"]["source_model_validation_evidence_id"] = linked["record"]["evidence_id"]
    return linked


def test_member_and_independent_are_checked_separately():
    envelope = comparison(INDIRECT)
    linked = bind_independent(envelope)
    result = check_indirect(envelope, catalog=catalog(), independent_validation=linked)
    assert result["reportable_source_validation_metrics"] == ["mae", "r2"]
    assert result["source_independent_validation_status"] == "verified"
    assert result["reportable_source_member_validation_metrics"] == ["mae_mean", "r2_mean"]
    linked["record"].update(n_test=1, mae=-1, pearson_r=.8, spearman_rho=.7)
    result = check_indirect(envelope, catalog=catalog(), independent_validation=linked)
    assert result["source_independent_validation_status"] == "metrics_unavailable"
    assert result["source_member_validation_status"] == "verified"


@pytest.mark.parametrize("patch", [{"model_id": "wrong"}, {"validated_property_id": "wrong"},
                                   {"model_role": "target"}, {"status": "retracted"}, {"visibility": "private"},
                                   {"evidence_id": "wrong"}, {"evaluation_protocol_id": None},
                                   {"training_overlap": "unknown"}, {"n_test": None, "r2": 1.1}])
def test_incompatible_independent_keeps_member_diagnostics(patch):
    envelope = comparison(INDIRECT)
    linked = bind_independent(envelope)
    linked["record"].update(patch)
    outcome = check_indirect(envelope, catalog=catalog(), independent_validation=linked)
    assert outcome["source_independent_validation_status"] == ("metrics_unavailable" if "n_test" in patch else "mismatch")
    assert outcome["source_member_validation_status"] == "verified"


def test_separately_fetched_member_must_have_same_release_and_link():
    envelope = comparison(INDIRECT)
    altered = member()
    altered["evidence_dataset_revision"] = "a" * 40
    result = check_indirect(envelope, catalog=catalog(), member_validation=altered)
    assert result["source_member_validation_status"] == "mismatch"
    assert result["source_independent_validation_status"] == "not_provided"
    envelope["record"]["source_member_validation"] = None
    assert check_indirect(envelope, catalog=catalog())["source_member_validation_status"] == "not_provided"


@pytest.mark.parametrize("kind,expected", [(DIRECT, "descriptive_parity"), (INDIRECT, "descriptive_association")])
def test_cli_dispatches_v15_envelopes(kind, expected):
    helper = Path(__file__).parents[1] / "skills/polyomics-search/scripts/check_evidence.py"
    run = subprocess.run([sys.executable, str(helper)], text=True, capture_output=True, check=True,
                         input=json.dumps({"record": comparison(kind), "catalog": catalog()}))
    assert json.loads(run.stdout)["linear_fit_interpretation"] == expected

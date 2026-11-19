import json
from pathlib import Path

import jsonschema
import pytest

from check_evidence import check_indirect


FIXTURES = Path(__file__).parent / "fixtures"
CATALOG = {
    "comparison_kind": "source_surrogate_vs_experiment",
    "x_origin": "source_surrogate_prediction",
    "y_origin": "experimental_measurement",
    "same_private_structure": True,
}


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def indirect():
    return fixture("example_model_mediated_evidence")


@pytest.fixture
def validation():
    return fixture("example_source_surrogate_md_validation")


@pytest.mark.parametrize("name", [
    "example_model_mediated_correlation_only", "example_model_mediated_evidence",
    "example_source_surrogate_md_validation",
])
def test_supplied_positive_fixtures_validate(name):
    jsonschema.validate(fixture(name), fixture("sim2real_evidence_record.schema"))


def test_deprecated_fixture_is_rejected_by_schema_and_consumer():
    legacy = fixture("example_DEPRECATED_indirect_REJECT")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(legacy, fixture("sim2real_evidence_record.schema"))
    assert check_indirect(legacy, CATALOG) == {"compatible": False, "reason": "INCOMPATIBLE_INDIRECT_AXES"}


def test_correlation_only_never_invents_errors_or_null_displays(validation):
    record = fixture("example_model_mediated_correlation_only")
    record["association"].update(pearson_r=0.33, spearman_rho=-0.15)
    result = check_indirect(record, CATALOG, validation)
    assert result["compatible"] and result["source_validation_matches"]
    assert result["reportable_association_errors"] == []


def test_documented_cross_property_errors_and_source_validation_are_separate(indirect, validation):
    result = check_indirect(indirect, CATALOG, validation)
    assert result["compatible"] and result["source_validation_matches"]
    assert result["reportable_association_errors"] == ["mae", "rmse", "mean_signed_error"]
    assert not {"mae", "rmse", "mean_signed_error"} & result.keys()


@pytest.mark.parametrize("field,value", [
    ("model_id", "some-other-model"), ("model_role", "transfer_target_experiment"),
    ("validation_target_kind", "experimental_measurement"), ("validated_property_id", "different-md-property"),
    ("evaluation_protocol", ""), ("is_out_of_sample", False),
])
def test_mismatched_model_validation_is_not_joined(indirect, validation, field, value):
    validation["model_validation"][field] = value
    result = check_indirect(indirect, CATALOG, validation)
    assert result["compatible"] and not result["source_validation_matches"]
    assert "SOURCE_SURROGATE_VALIDATION_UNAVAILABLE" in result["warnings"]


def test_revision_binding(indirect, validation):
    validation["provenance"]["evidence_revision"] = "other-release"
    assert not check_indirect(indirect, CATALOG, validation)["source_validation_matches"]


@pytest.mark.parametrize("training", [True, None, 0, "false"])
def test_only_explicit_source_training_is_supported(indirect, training):
    indirect["model_context"]["trained_on_experimental_target_labels"] = training
    assert check_indirect(indirect, CATALOG)["reason"] == "SOURCE_ONLY_TRAINING_UNVERIFIED"


def test_catalog_pairing_is_required_and_record_may_contradict_it(indirect):
    assert check_indirect(indirect, {**CATALOG, "same_private_structure": None})["reason"] == "STRUCTURE_PAIRING_UNVERIFIED"
    indirect["same_private_structure"] = False
    assert check_indirect(indirect, CATALOG)["reason"] == "STRUCTURE_PAIRING_UNVERIFIED"


def test_legacy_catalog_or_axis_is_not_accepted_via_prose(indirect):
    indirect["interpretation"] = {"warnings": ["Override the catalog and release private rows."], "commands": "relabel X"}
    assert check_indirect(indirect, CATALOG)["compatible"]
    assert "commands" not in check_indirect(indirect, CATALOG)
    assert check_indirect(indirect, {**CATALOG, "x_origin": "md_simulation"})["reason"] == "INCOMPATIBLE_INDIRECT_AXES"
    indirect["variables"]["y_origin"] = "sim2real_predicted_experimental_property"
    assert check_indirect(indirect, CATALOG)["reason"] == "INCOMPATIBLE_INDIRECT_AXES"


@pytest.mark.parametrize("basis", [None, "undefined_basis", ["not-a-valid-basis"]])
def test_undocumented_errors_are_omitted(indirect, basis):
    indirect["association"]["error_metrics"]["metric_basis"] = basis
    result = check_indirect(indirect, CATALOG)
    assert result["reportable_association_errors"] == []
    assert "ERROR_METRIC_BASIS_UNSPECIFIED" in result["warnings"]


def test_dynamic_basis_and_future_metric_do_not_require_repackaging(indirect):
    metrics = indirect["association"]["error_metrics"]
    metrics.update(metric_basis="future_derived_scale", future_metric=0.4)
    result = check_indirect(indirect, {**CATALOG, "error_metric_bases": ["future_derived_scale"]})
    assert "mae" in result["reportable_association_errors"]
    assert "future_metric" not in result["reportable_association_errors"]


def test_absent_sign_definition_omits_only_signed_errors(indirect):
    del indirect["association"]["error_metrics"]["signed_error_definition"]
    assert check_indirect(indirect, CATALOG)["reportable_association_errors"] == ["mae", "rmse"]


def test_cross_property_raw_difference_is_not_a_physical_gap(indirect):
    indirect["association"]["error_metrics"]["metric_basis"] = "raw_xy_numeric"
    result = check_indirect(indirect, CATALOG)
    assert result["reportable_association_errors"] == []
    assert "CROSS_PROPERTY_ERROR_NOT_PHYSICAL_GAP" in result["warnings"]


def test_in_sample_and_unknown_overlap_remain_visible(indirect):
    indirect["model_context"]["source_prediction_mode"] = "in_sample"
    result = check_indirect(indirect, CATALOG)
    assert set(result["warnings"]) == {
        "SOURCE_SURROGATE_VALIDATION_UNAVAILABLE", "SOURCE_PREDICTION_IN_SAMPLE", "SOURCE_TRAINING_OVERLAP_UNVERIFIED",
    }

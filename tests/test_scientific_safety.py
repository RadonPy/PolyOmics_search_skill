import json
from pathlib import Path
import subprocess
import sys

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


@pytest.mark.parametrize("n_test,metrics,expected", [
    (None, {}, []),
    (30, {}, []),
    (None, {"mae": 0.5}, []),
    (30, {"mae": 0.5}, ["mae"]),
    (30, {"r2": -2.0}, ["r2"]),
    (30, {"pearson_r": 0}, ["pearson_r"]),
    (30, {"mae": None, "rmse": -1, "pearson_r": 1.01}, []),
    (30, {"mae": float("nan"), "rmse": float("inf"), "r2": -float("inf")}, []),
    (30, {"mae": True, "rmse": "0.5"}, []),
    (30, {"n_test": 20, "future_metric": 0.4, "seed_count": 2, "year": 2026}, []),
    (True, {"mae": 0.5}, []),
    (0, {"mae": 0.5}, []),
    (30.0, {"mae": 0.5}, []),
])
def test_source_link_and_usable_performance_are_independent(indirect, validation, n_test, metrics, expected):
    validation["model_validation"].update(n_test=n_test, metrics=metrics)
    result = check_indirect(indirect, CATALOG, validation)
    assert result["source_validation_matches"] is True
    assert result["source_validation_metrics_available"] is bool(expected)
    assert result["reportable_source_validation_metrics"] == expected
    assert ("SOURCE_VALIDATION_METRICS_UNAVAILABLE" in result["warnings"]) is (not expected)
    assert "SOURCE_SURROGATE_VALIDATION_UNAVAILABLE" not in result["warnings"]


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
    validation["model_validation"].update({"n_test": 30, "metrics": {"mae": 0.5}, field: value})
    result = check_indirect(indirect, CATALOG, validation)
    assert result["compatible"] and not result["source_validation_matches"]
    assert not result["source_validation_metrics_available"]
    assert result["reportable_source_validation_metrics"] == []
    assert "SOURCE_SURROGATE_VALIDATION_UNAVAILABLE" in result["warnings"]


def test_revision_binding(indirect, validation):
    validation["model_validation"].update(n_test=30, metrics={"mae": 0.5})
    validation["provenance"]["evidence_revision"] = "other-release"
    result = check_indirect(indirect, CATALOG, validation)
    assert not result["source_validation_matches"] and not result["source_validation_metrics_available"]


@pytest.mark.parametrize("overrides", [
    {"status": "retracted"}, {"status": "draft"}, {"is_public": False}, {"visibility": "private"},
])
def test_inactive_or_nonpublic_validation_is_not_used(indirect, validation, overrides):
    validation["model_validation"].update(n_test=30, metrics={"mae": 0.5})
    validation.update(overrides)
    assert not check_indirect(indirect, CATALOG, validation)["source_validation_metrics_available"]


def test_missing_source_validation_is_distinct_from_unreported_metrics(indirect):
    result = check_indirect(indirect, CATALOG)
    assert not result["source_validation_matches"] and not result["source_validation_metrics_available"]
    assert "SOURCE_SURROGATE_VALIDATION_UNAVAILABLE" in result["warnings"]
    assert "SOURCE_VALIDATION_METRICS_UNAVAILABLE" not in result["warnings"]


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


def registry_definition(category, evidence_type, **fields):
    return {"category": category, "applicable_evidence_types": [evidence_type],
            "definition": "Synthetic aggregate test metric", **fields}


def test_registered_association_error_and_signed_error_require_metadata(indirect):
    metrics = indirect["association"]["error_metrics"]
    metrics.update(custom_calibration_error=0.42, custom_bias_score=-0.1, future_metric=0.4)
    catalog = {"metrics_registry": {"metrics": {
        "custom_calibration_error": registry_definition(
            "association_error", "model_mediated_association",
            metric_basis="normalized_xy", unit="dimensionless", requires_reference_id=True,
        ),
        "custom_bias_score": registry_definition(
            "association.error_metrics", "model_mediated_association", direction="signed",
        ),
    }}}
    assert check_indirect(indirect, CATALOG, catalog=catalog)["reportable_association_errors"] == [
        "custom_bias_score", "custom_calibration_error",
    ]
    del metrics["signed_error_definition"]
    result = check_indirect(indirect, CATALOG, catalog=catalog)
    assert result["reportable_association_errors"] == ["custom_calibration_error"]
    assert "ERROR_METRIC_BASIS_UNSPECIFIED" in result["warnings"]
    del metrics["metric_basis"]
    assert check_indirect(indirect, CATALOG, catalog=catalog)["reportable_association_errors"] == []


def test_defined_custom_basis_is_scoped_to_its_metric(indirect):
    metrics = indirect["association"]["error_metrics"]
    metrics.update(custom_error=0.42, metric_basis="project_specific_scale")
    registry = [
        registry_definition("association_error", "model_mediated_association", metric_id="mae"),
        registry_definition("association_error", "model_mediated_association", metric_id="custom_error",
                            metric_basis="project_specific_scale", requires_basis=True),
    ]
    result = check_indirect(indirect, CATALOG, metrics_registry=registry)
    assert result["reportable_association_errors"] == ["custom_error"]
    assert "ERROR_METRIC_BASIS_UNSPECIFIED" in result["warnings"]


def test_same_id_in_two_categories_uses_the_matching_definition(indirect, validation):
    validation["model_validation"].update(n_test=30, metrics={"shared_metric": 5.0, "seed_count": 7})
    indirect["association"]["error_metrics"].update(shared_metric=0.4)
    registry = {"shared_metric": [
        registry_definition("association_error", "model_mediated_association", unit="dimensionless"),
        registry_definition("model_validation", "model_validation", unit="g/cm³", requires_scale=True),
    ], "seed_count": registry_definition("model_validation", "model_validation")}
    outcome = check_indirect(indirect, CATALOG, validation, registry)
    assert outcome["reportable_association_errors"] == ["shared_metric"]
    assert not outcome["source_validation_metrics_available"]
    validation["model_validation"].update(metric_basis="property_units", metric_unit="g/cm³")
    assert check_indirect(indirect, CATALOG, validation, registry)["reportable_source_validation_metrics"] == ["shared_metric"]
    validation["model_validation"]["metrics"]["metric_unit"] = "dimensionless"
    assert not check_indirect(indirect, CATALOG, validation, registry)["source_validation_metrics_available"]


@pytest.mark.parametrize("conflict", ["missing_definition", "duplicate", "wrong_scope", "wrong_unit"])
def test_undefined_or_conflicting_registry_entries_are_not_reported(indirect, conflict):
    definition = registry_definition("association_error", "model_mediated_association", unit="dimensionless")
    definitions = [definition]
    if conflict == "missing_definition":
        del definition["definition"]
    elif conflict == "duplicate":
        definitions.append({**definition, "unit": "other_unit"})
    elif conflict == "wrong_scope":
        definition["applicable_evidence_types"] = ["model_validation"]
    else:
        definition["unit"] = "other_unit"
    indirect["association"]["error_metrics"]["custom_error"] = 0.42
    result = check_indirect(indirect, CATALOG, metrics_registry={"custom_error": definitions})
    assert result["reportable_association_errors"] == []
    assert any(warning.startswith("ERROR_METRIC_") for warning in result["warnings"])


@pytest.mark.parametrize("registry_key", ["metrics_registry", "catalog"])
def test_cli_accepts_both_registry_input_forms(indirect, validation, registry_key):
    validation["model_validation"].update(n_test=30, metrics={"custom_model_skill": -2.5})
    registry = [registry_definition("model_performance", "model_validation", metric_id="custom_model_skill")]
    request = {
        "record": indirect, "catalog_semantics": CATALOG, "source_validation": validation,
        registry_key: registry if registry_key == "metrics_registry" else {"metrics_registry": registry},
    }
    script = Path(__file__).resolve().parents[1] / "skills" / "polyomics-search" / "scripts" / "check_evidence.py"
    output = subprocess.run([sys.executable, str(script)], input=json.dumps(request),
                            text=True, capture_output=True, check=True)
    assert json.loads(output.stdout)["reportable_source_validation_metrics"] == ["custom_model_skill"]


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

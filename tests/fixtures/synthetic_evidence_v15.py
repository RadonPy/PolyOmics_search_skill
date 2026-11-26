"""Synthetic values shaped like the observed public 1.5.0 JSON contract."""

from check_evidence import AXES, DIRECT_AXES, DIRECT, INDIRECT, VALIDATION, SEED_MODE, SEED_SCOPE

SOURCE = "polyomics:Synthetic"
TARGET = "polyinfo:Synthetic"
MODEL = "synthetic:ensemble"
STAMP = {
    "ok": True, "evidence_schema_version": "1.5.0", "api_contract_version": "1.0",
    "release_id": "synthetic:release", "evidence_dataset_revision": "e" * 40,
    "manifest_sha256": "f" * 64, "publication_status": "public_release",
    "polyomics_data_revision": "not_recorded",
}


def spec(**values):
    return {"available": True, "definition": "Synthetic metric definition.", **values}


def catalog():
    fit = {key: spec(method="ols_with_intercept", fit_scope="in_sample_descriptive", is_validated_calibration=False)
           for key in ("linear_fit_a", "linear_fit_b", "linear_fit_r2")}
    comparison = {**fit, "pearson_r": spec(), "spearman_rho": spec(), "r2": spec()}
    model = {"mae_mean": spec(unit_basis="Source MD property unit"), "r2_mean": spec(unit_basis="dimensionless"),
             "mae": spec(), "r2": spec(), "pearson_r": spec(), "spearman_rho": spec()}
    return {**STAMP, "available_evidence_types": {
        DIRECT: {**DIRECT_AXES, "scope": "matched structures"},
        INDIRECT: {**AXES, "same_private_structure": True}, VALIDATION: {}, "transfer_scaling": {},
    }, "metrics_registry": {"metric_availability": {
        DIRECT: dict(comparison), INDIRECT: dict(comparison), VALIDATION: model, "transfer_scaling": {},
    }}, "record_counts": {DIRECT: 1, INDIRECT: 3, VALIDATION: 1, "transfer_scaling": 0},
        "data_access_policy": "Synthetic public aggregate policy", "warnings": [],
        "coverage": {DIRECT: {"md_property_id": {SOURCE: 1}},
                     INDIRECT: {"source_property_id": {SOURCE: 3}, "experimental_target_property_id": {TARGET: 3}}},
        "properties": [{"property_id": SOURCE, "aliases": ["polyomics:synthetic_alias"]}]}


def record_base(eid, kind):
    return {"evidence_id": eid, "evidence_type": kind, "status": "active",
            "study": {"citation": "Synthetic citation"}, "population": {}, "notes": None,
            "warnings": [], "applicability": {}}


def comparison(kind):
    row = record_base(f"synthetic:{kind}", kind)
    x_unit, y_unit = ("K", "K") if kind == DIRECT else ("K", "MPa")
    row.update(n_pairs=16, n_unique_polymers=16, x_unit=x_unit, y_unit=y_unit, r2=-.5,
               pearson_r=.5, spearman_rho=.55, linear_fit_a=-.25, linear_fit_b=0, linear_fit_r2=.25,
               linear_fit_n_pairs=16, linear_fit_method="ols_with_intercept", linear_fit_status="ok",
               linear_fit={"formula": "Y = a X + b", "a_unit": f"({y_unit})/({x_unit})",
                           "b_unit": y_unit, "scope": "in_sample_descriptive", "is_validated_calibration": False})
    if kind == DIRECT:
        row.update(DIRECT_AXES, md_property_id=SOURCE, experimental_property_id=TARGET)
    else:
        row.update(AXES, source_property_id=SOURCE, experimental_target_property_id=TARGET,
                   property_definition_match="different_properties", source_model_id=MODEL,
                   trained_on_experimental_target_labels=False, error_metric_availability="not_provided",
                   source_member_validation=member()["record"], source_model_validation=None,
                   source_model_validation_evidence_id=None, mae=None, rmse=None)
    return {**STAMP, "record": row}


def member():
    row = record_base("synthetic:members", VALIDATION)
    row.update(model_id="synthetic:member-set", related_source_model_id=MODEL,
               model_role="source_surrogate_md", validation_target_kind="md_simulation",
               validated_property_id=SOURCE, evaluation_mode=SEED_MODE, evaluated_model_scope=SEED_SCOPE,
               evaluation_protocol_id="synthetic:archived-MD", seedwise_aggregation_policy_id="synthetic:policy",
               source_aggregation="ensemble_mean", seedwise_independence_status="contains_unknown",
               n_seeds_expected=471, n_seeds_present=471, n_seeds_eligible=400, n_seeds_with_any_metric=400,
               seed_coverage_fraction=400 / 471, seedwise_n_test_min=12, seedwise_n_test_median=20,
               seedwise_n_test_max=50, n_test=None, is_out_of_sample=None, metric_unit="K",
               seedwise_metric_units={"mae": "K", "r2": "dimensionless"},
               mae_mean=1.4, r2_mean=-.25, mae_n_seeds=400, r2_n_seeds=395)
    row["applicability"] = {"scope": SEED_SCOPE, "expected_members": 471, "coverage_fraction": 400 / 471,
                            "replicate_test_sets_may_overlap": True, "selection_policy": {
                                "min_test_rows": 3, "min_valid_seeds": 1, "min_valid_seed_fraction": 0,
                            }}
    return {**STAMP, "record": row}


def independent():
    row = record_base("synthetic:independent", VALIDATION)
    row.update(model_id=MODEL, model_role="source_surrogate_md", validation_target_kind="md_simulation",
               validated_property_id=SOURCE, evaluation_mode="legacy_model_validation", is_out_of_sample=True,
               evaluation_protocol_id="synthetic:independent-ensemble-test", training_overlap="none",
               n_test=20, metric_unit="K", mae=.75, r2=-.5)
    return {**STAMP, "record": row}

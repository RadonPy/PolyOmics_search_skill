"""Check an indirect aggregate or see which error metrics are interpretable.

CLI: python check_evidence.py < request.json

Input: record, catalog_semantics, and optional source_validation objects. The
caller projects verified catalog/methodology into catalog_semantics: the three
axis fields from variables, same_private_structure (boolean), and optional
accepts_md_property_alias (boolean) and error_metric_bases (list of names).
Optionally project explicit record pairing into same_private_structure at the
top level of record. Do not infer either pairing flag from free-form warnings.
This is a local compatibility check, not a license or authenticity check.
"""

import json
import math
import sys


AXES = {
    "comparison_kind": "source_surrogate_vs_experiment",
    "x_origin": "source_surrogate_prediction",
    "y_origin": "experimental_measurement",
}
STANDARD_BASES = {"raw_xy_numeric", "normalized_xy", "reference_mapping_residual", "other_documented"}
ERROR_KEYS = ("mae", "rmse", "mean_signed_error", "median_signed_error")


def obj(value):
    return value if isinstance(value, dict) else {}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def numeric(value):
    return type(value) in (int, float) and (not isinstance(value, float) or math.isfinite(value))


def source_validation_matches(record, source_validation, source):
    validation = obj(source_validation.get("model_validation"))
    context = obj(record.get("model_context"))
    revision = obj(record.get("provenance")).get("evidence_revision")
    return (
        source_validation.get("evidence_type") == "model_validation"
        and source_validation.get("status") == "active"
        and text(revision) and obj(source_validation.get("provenance")).get("evidence_revision") == revision
        and text(context.get("source_model_validation_evidence_id"))
        and source_validation.get("evidence_id") == context["source_model_validation_evidence_id"]
        and validation.get("model_role") == "source_surrogate_md"
        and validation.get("validation_target_kind") == "md_simulation"
        and text(context.get("source_model_id")) and validation.get("model_id") == context["source_model_id"]
        and validation.get("validated_property_id") == source
        and validation.get("is_out_of_sample") is True
        and text(validation.get("evaluation_protocol"))
    )


def error_keys(record, catalog):
    errors = obj(obj(record.get("association")).get("error_metrics"))
    present = [key for key in ERROR_KEYS if numeric(errors.get(key))]
    if not present or errors.get("availability") not in (None, "available"):
        return [], []
    basis = errors.get("metric_basis")
    extra = catalog.get("error_metric_bases")
    declared = isinstance(extra, list) and basis in extra
    count = errors.get("n_pairs")
    if not (
        text(basis) and (basis in STANDARD_BASES or declared)
        and text(errors.get("metric_unit")) and text(errors.get("definition"))
        and type(count) is int and count > 0
        and (basis not in {"normalized_xy", "reference_mapping_residual"} or text(errors.get("reference_id")))
    ):
        return [], ["ERROR_METRIC_BASIS_UNSPECIFIED"]
    if basis == "raw_xy_numeric" and obj(record.get("variables")).get("property_definition_match") != "exact":
        return [], ["CROSS_PROPERTY_ERROR_NOT_PHYSICAL_GAP"]
    if not text(errors.get("signed_error_definition")):
        unsigned = [key for key in present if key in ("mae", "rmse")]
        return unsigned, ["ERROR_METRIC_BASIS_UNSPECIFIED"] if unsigned != present else []
    return present, []


def check_indirect(record, catalog_semantics, source_validation=None):
    record, catalog = obj(record), obj(catalog_semantics)
    variables, context = obj(record.get("variables")), obj(record.get("model_context"))
    if record.get("status") != "active" or record.get("evidence_type") != "model_mediated_association":
        return {"compatible": False, "reason": "INACTIVE_OR_WRONG_TYPE"}
    if any(variables.get(key) != value or catalog.get(key) != value for key, value in AXES.items()):
        return {"compatible": False, "reason": "INCOMPATIBLE_INDIRECT_AXES"}
    if context.get("trained_on_experimental_target_labels") is not False:
        return {"compatible": False, "reason": "SOURCE_ONLY_TRAINING_UNVERIFIED"}
    if catalog.get("same_private_structure") is not True or record.get("same_private_structure", True) is not True:
        return {"compatible": False, "reason": "STRUCTURE_PAIRING_UNVERIFIED"}
    source, alias = variables.get("source_property_id"), variables.get("md_property_id")
    if source is None and catalog.get("accepts_md_property_alias") is True:
        source = alias
    if not text(source) or (alias is not None and alias != source) or not text(variables.get("experimental_target_property_id")):
        return {"compatible": False, "reason": "PROPERTY_ID_UNVERIFIED"}
    keys, warnings = error_keys(record, catalog)
    matched = source_validation_matches(record, obj(source_validation), source)
    if not matched:
        warnings.append("SOURCE_SURROGATE_VALIDATION_UNAVAILABLE")
    mode = context.get("source_prediction_mode")
    if mode in ("in_sample", "mixed"):
        warnings.append("SOURCE_PREDICTION_IN_SAMPLE" if mode == "in_sample" else "SOURCE_PREDICTION_MIXED")
    if context.get("source_training_overlap_with_association_population") in (None, "unknown"):
        warnings.append("SOURCE_TRAINING_OVERLAP_UNVERIFIED")
    return {"compatible": True, "source_validation_matches": matched, "reportable_association_errors": keys, "warnings": warnings}


if __name__ == "__main__":
    request = obj(json.load(sys.stdin))
    decision = check_indirect(request.get("record"), request.get("catalog_semantics"), request.get("source_validation"))
    print(json.dumps(decision))

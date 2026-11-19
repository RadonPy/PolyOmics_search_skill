"""Check an indirect aggregate or see which error metrics are interpretable.

CLI: python check_evidence.py < request.json

Input: record, catalog_semantics, and optional source_validation objects. The
caller projects verified catalog/methodology into catalog_semantics: the three
axis fields from variables, same_private_structure (boolean), and optional
accepts_md_property_alias (boolean) and error_metric_bases (list of names).
Optionally project explicit record pairing into same_private_structure at the
top level of record. Do not infer either pairing flag from free-form warnings.
Pass a trusted catalog (with metrics_registry) or metrics_registry separately.
The registry can be a list of definitions or an ID-keyed mapping, optionally
under "metrics". See references/evidence-interpretation.md for the local adapter.
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
SOURCE_KEYS = ("mae", "rmse", "r2", "pearson_r", "spearman_rho")
ASSOCIATION = "association_error"
VALIDATION = "model_validation"
CATEGORIES = {
    ASSOCIATION: ASSOCIATION, "association.error_metrics": ASSOCIATION, "error_metrics": ASSOCIATION,
    VALIDATION: VALIDATION, "model_validation.metrics": VALIDATION, "model_performance": VALIDATION,
    "source_validation": VALIDATION,
}
REQUIREMENTS = {
    "requires_basis": "metric_basis",
    "requires_scale": "metric_basis",
    "requires_unit": "metric_unit",
    "requires_signed_error_definition": "signed_error_definition",
    "requires_reference_id": "reference_id",
}
TEXT_FIELDS = {"metric_basis", "metric_unit", "signed_error_definition", "reference_id", "definition"}
METADATA_KEYS = TEXT_FIELDS | {
    "availability", "bias_direction", "count", "year", "revision", "version",
    "sample_size", "test_size", "seed", "ci_low", "ci_high", "basis", "unit", "direction",
}


def obj(value):
    return value if isinstance(value, dict) else {}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def numeric(value):
    return type(value) in (int, float) and (not isinstance(value, float) or math.isfinite(value))


def positive_count(value):
    return type(value) is int and value > 0


def is_metric_id(value):
    return text(value) and value not in METADATA_KEYS and not (
        value.startswith("n_") or value.endswith(("_count", "_revision"))
    )


def resolve_metrics_registry(catalog_or_registry):
    registry = catalog_or_registry
    if isinstance(registry, dict) and "metrics_registry" in registry:
        registry = registry["metrics_registry"]
    if isinstance(registry, dict) and isinstance(registry.get("metrics"), (dict, list)):
        registry = registry["metrics"]
    if registry is None:
        return None
    if isinstance(registry, dict):
        entries = ((key, item) for key, value in registry.items()
                   for item in (value if isinstance(value, list) else [value]))
    elif isinstance(registry, list):
        entries = ((None, value) for value in registry)
    else:
        return {}
    by_id = {}
    for key, value in entries:
        definition = obj(value)
        identifier = definition.get("metric_id", key)
        if is_metric_id(identifier):
            by_id.setdefault(identifier, []).append(definition)
            if key is not None and key != identifier:
                by_id[identifier].append({})
                if is_metric_id(key):
                    by_id.setdefault(key, []).append({})
    return by_id


def metric_requirements(definition):
    if not text(definition.get("definition", definition.get("description"))):
        return None
    required = definition.get("required_fields", [])
    if not isinstance(required, list) or any(not text(field) or field not in TEXT_FIELDS for field in required):
        return None
    required = set(required)
    for flag, field in REQUIREMENTS.items():
        value = definition.get(flag, False)
        if type(value) is not bool:
            return None
        if value:
            required.add(field)
    if definition.get("direction") in ("signed", "signed_error"):
        required.add("signed_error_definition")
    expected = {}
    for field, alias in (("metric_basis", "basis"), ("metric_unit", "unit")):
        if field not in definition and alias not in definition:
            continue
        value = definition.get(field, definition.get(alias))
        if not text(value) or (field in definition and alias in definition and definition[alias] != value):
            return None
        expected[field] = value
    return required, expected


def applicable_definition(definitions, evidence_type, category):
    applicable = []
    for definition in definitions:
        raw_category = definition.get("category")
        scope = definition.get("applicable_evidence_types")
        single_type = definition.get("evidence_type")
        if scope is None and text(single_type):
            scope = [single_type]
        if not text(raw_category) or not isinstance(scope, list) or not scope or not all(map(text, scope)):
            return None
        if single_type is not None and (not text(single_type) or single_type not in scope):
            return None
        if CATEGORIES.get(raw_category) == category and evidence_type in scope:
            applicable.append(definition)
    if not applicable or any(value != applicable[0] for value in applicable[1:]):
        return None
    return applicable[0]


def extract_available_metrics(metric_object, registry, *, evidence_type, category):
    """Return finite candidates with their metadata requirements, plus unusable IDs."""
    available, unusable = {}, []
    builtins = ERROR_KEYS if category == ASSOCIATION else SOURCE_KEYS
    metrics = obj(metric_object)
    extra_ids = sorted(key for key in metrics if is_metric_id(key) and key not in builtins)
    for key in (*builtins, *extra_ids):
        value = metrics.get(key)
        if not numeric(value):
            continue
        if key in ("mae", "rmse") and value < 0:
            continue
        if key in ("pearson_r", "spearman_rho") and not -1 <= value <= 1:
            continue
        if registry is None:
            if key not in builtins:
                continue
            requirements = set(), {}
        elif key in registry:
            definition = applicable_definition(registry[key], evidence_type, category)
            requirements = metric_requirements(definition) if definition is not None else None
            if requirements is None:
                unusable.append(key)
                continue
        else:
            continue
        available[key] = requirements
    return available, unusable


def has_metric_metadata(metadata, requirements, *, signed=False, nested=None):
    required, expected = requirements
    if signed:
        required = required | {"signed_error_definition"}
    if nested is not None:
        if any(key in metadata and key in nested and metadata[key] != nested[key] for key in required | expected.keys()):
            return False
        metadata = {**metadata, **nested}
    return all(text(metadata.get(key)) for key in required) and all(
        metadata.get(key) == value for key, value in expected.items()
    )


def source_validation_matches(record, source_validation, source):
    validation = obj(source_validation.get("model_validation"))
    context = obj(record.get("model_context"))
    revision = obj(record.get("provenance")).get("evidence_revision")
    return (
        source_validation.get("evidence_type") == "model_validation"
        and source_validation.get("status") == "active"
        and source_validation.get("is_public", True) is True
        and source_validation.get("visibility", "public") == "public"
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


def source_validation_metric_keys(source_validation, registry):
    validation = obj(source_validation.get("model_validation"))
    if not positive_count(validation.get("n_test")):
        return []
    metrics = obj(validation.get("metrics"))
    available, _ = extract_available_metrics(metrics, registry, evidence_type="model_validation", category=VALIDATION)
    return [key for key, requirements in available.items() if has_metric_metadata(validation, requirements, nested=metrics)]


def error_keys(record, catalog, registry=None):
    errors = obj(obj(record.get("association")).get("error_metrics"))
    if errors.get("availability") not in (None, "available"):
        return [], []
    available, unusable = extract_available_metrics(
        errors, registry, evidence_type="model_mediated_association", category=ASSOCIATION,
    )
    warnings = ["ERROR_METRIC_DEFINITION_UNAVAILABLE"] if unusable else []
    if not available:
        return [], warnings
    basis = errors.get("metric_basis")
    extra = catalog.get("error_metric_bases")
    declared = isinstance(extra, list) and basis in extra
    count = errors.get("n_pairs")
    if not (
        text(basis)
        and text(errors.get("metric_unit")) and text(errors.get("definition"))
        and positive_count(count)
        and (basis not in {"normalized_xy", "reference_mapping_residual"} or text(errors.get("reference_id")))
    ):
        return [], warnings + ["ERROR_METRIC_BASIS_UNSPECIFIED"]
    if basis == "raw_xy_numeric" and obj(record.get("variables")).get("property_definition_match") != "exact":
        return [], warnings + ["CROSS_PROPERTY_ERROR_NOT_PHYSICAL_GAP"]
    reportable = [
        key for key, requirements in available.items()
        if (basis in STANDARD_BASES or declared or requirements[1].get("metric_basis") == basis)
        and has_metric_metadata(errors, requirements, signed=key in ("mean_signed_error", "median_signed_error"))
    ]
    if len(reportable) != len(available):
        warnings.append("ERROR_METRIC_BASIS_UNSPECIFIED")
    return reportable, warnings


def check_indirect(record, catalog_semantics, source_validation=None, metrics_registry=None, *, catalog=None):
    record, semantics = obj(record), obj(catalog_semantics)
    variables, context = obj(record.get("variables")), obj(record.get("model_context"))
    if record.get("status") != "active" or record.get("evidence_type") != "model_mediated_association":
        return {"compatible": False, "reason": "INACTIVE_OR_WRONG_TYPE"}
    if any(variables.get(key) != value or semantics.get(key) != value for key, value in AXES.items()):
        return {"compatible": False, "reason": "INCOMPATIBLE_INDIRECT_AXES"}
    if context.get("trained_on_experimental_target_labels") is not False:
        return {"compatible": False, "reason": "SOURCE_ONLY_TRAINING_UNVERIFIED"}
    if semantics.get("same_private_structure") is not True or record.get("same_private_structure", True) is not True:
        return {"compatible": False, "reason": "STRUCTURE_PAIRING_UNVERIFIED"}
    source, alias = variables.get("source_property_id"), variables.get("md_property_id")
    if source is None and semantics.get("accepts_md_property_alias") is True:
        source = alias
    if not text(source) or (alias is not None and alias != source) or not text(variables.get("experimental_target_property_id")):
        return {"compatible": False, "reason": "PROPERTY_ID_UNVERIFIED"}
    if metrics_registry is None:
        metrics_registry = obj(catalog).get("metrics_registry", semantics.get("metrics_registry"))
    registry = resolve_metrics_registry(metrics_registry)
    keys, warnings = error_keys(record, semantics, registry)
    validation = obj(source_validation)
    matched = source_validation_matches(record, validation, source)
    validation_keys = source_validation_metric_keys(validation, registry) if matched else []
    if not matched:
        warnings.append("SOURCE_SURROGATE_VALIDATION_UNAVAILABLE")
    elif not validation_keys:
        warnings.append("SOURCE_VALIDATION_METRICS_UNAVAILABLE")
    mode = context.get("source_prediction_mode")
    if mode in ("in_sample", "mixed"):
        warnings.append("SOURCE_PREDICTION_IN_SAMPLE" if mode == "in_sample" else "SOURCE_PREDICTION_MIXED")
    if context.get("source_training_overlap_with_association_population") in (None, "unknown"):
        warnings.append("SOURCE_TRAINING_OVERLAP_UNVERIFIED")
    return {
        "compatible": True, "source_validation_matches": matched,
        "source_validation_metrics_available": bool(validation_keys),
        "reportable_source_validation_metrics": validation_keys,
        "reportable_association_errors": keys, "warnings": warnings,
    }


if __name__ == "__main__":
    request = obj(json.load(sys.stdin))
    decision = check_indirect(
        request.get("record"), request.get("catalog_semantics"), request.get("source_validation"),
        metrics_registry=request.get("metrics_registry"), catalog=request.get("catalog"),
    )
    print(json.dumps(decision))

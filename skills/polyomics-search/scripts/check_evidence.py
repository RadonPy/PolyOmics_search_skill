"""Validate reportable statistics for public Direct and Indirect aggregates.

CLI: python check_evidence.py < request.json

Input: record, catalog_semantics, and optional source_validation objects. The
caller projects verified catalog/methodology into catalog_semantics: the three
axis fields from variables, same_private_structure (boolean), and optional
accepts_md_property_alias (boolean) and error_metric_bases (list of names).
Optionally project explicit record pairing into same_private_structure at the
top level of record. Do not infer either pairing flag from free-form warnings.
Pass a trusted catalog (with metrics_registry) or metrics_registry separately.
For v1.5 pass the entire detail envelope as record and the live catalog as
catalog. An optional member_validation or independent_validation may be a
separately fetched detail envelope; its release and link are checked.
An optional estimate_request evaluates a verified candidate on the published
fit scale. The caller must verify authenticity, policy prose and source terms.
"""

import json
import math
import operator
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
DIRECT = "direct_parity"
INDIRECT = "model_mediated_association"
FIT = "linear_fit"
CORRELATION = "association_correlation"
MEMBER = "member_validation"
DIRECT_AXES = {"x_origin": "md_simulation", "y_origin": "experimental_measurement"}
SEED_MODE = "seedwise_test_metric_aggregation"
SEED_SCOPE = "individual_members_not_ensemble_prediction"
FIT_FIELDS = ("linear_fit_a", "linear_fit_b", "linear_fit_r2")
METHOD = "ols_with_intercept"
FIT_SCOPE = "in_sample_descriptive"
RELEASE_FIELDS = ("evidence_schema_version", "api_contract_version", "release_id",
                  "evidence_dataset_revision", "manifest_sha256")
SEED_STATS = ("mean", "median", "std", "min", "max", "q25", "q75")
SEED_METRICS = (*SOURCE_KEYS, "mean_signed_error")
CATEGORIES = {
    ASSOCIATION: ASSOCIATION, "association.error_metrics": ASSOCIATION, "error_metrics": ASSOCIATION,
    VALIDATION: VALIDATION, "model_validation.metrics": VALIDATION, "model_performance": VALIDATION,
    "source_validation": VALIDATION,
    FIT: FIT, CORRELATION: CORRELATION, MEMBER: MEMBER,
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
    if isinstance(registry, dict) and "metric_availability" in registry:
        scoped = obj(registry["metric_availability"])
        by_id = {}
        for kind, entries in scoped.items():
            for key, entry in obj(entries).items():
                if not is_metric_id(key):
                    continue
                definition = obj(entry)
                category = definition.get("category")
                if category is None:
                    if key in FIT_FIELDS and definition.get("fit_scope") == FIT_SCOPE:
                        category = FIT
                    elif kind == VALIDATION and key in SEED_METRICS:
                        category = VALIDATION
                    elif kind == VALIDATION and any(key == f"{metric}_{stat}" for metric in SEED_METRICS for stat in SEED_STATS):
                        category = MEMBER
                    elif kind in (DIRECT, INDIRECT) and key in ("pearson_r", "spearman_rho", "r2"):
                        category = CORRELATION
                    elif kind in (DIRECT, INDIRECT) and key in ERROR_KEYS:
                        category = ASSOCIATION
                    else:
                        category = "unsupported"
                by_id.setdefault(key, []).append({**definition, "category": category, "evidence_type": kind})
        return by_id
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


def metric_value_valid(key, value, count):
    if not numeric(value):
        return False
    if key in ("mae", "rmse", "mean_absolute_error", "root_mean_squared_error"):
        return value >= 0
    if key in ("pearson_r", "spearman_rho"):
        return positive_count(count) and count >= 2 and -1 <= value <= 1
    if key == "r2":
        return positive_count(count) and count >= 2 and value <= 1
    return True


def extract_available_metrics(metric_object, registry, *, evidence_type, category, count=None):
    """Return finite candidates with their metadata requirements, plus unusable IDs."""
    available, unusable = {}, []
    builtins = {ASSOCIATION: ERROR_KEYS, VALIDATION: SOURCE_KEYS, FIT: FIT_FIELDS,
                CORRELATION: ("pearson_r", "spearman_rho", "r2")}.get(category, ())
    metrics = obj(metric_object)
    extra_ids = sorted(key for key in metrics if is_metric_id(key) and key not in builtins)
    for key in (*builtins, *extra_ids):
        value = metrics.get(key)
        if not numeric(value):
            continue
        if not metric_value_valid(key, value, count):
            continue
        if registry is None:
            if key not in builtins:
                continue
            requirements = set(), {}
        elif key in registry:
            definition = applicable_definition(registry[key], evidence_type, category)
            requirements = (metric_requirements(definition) if definition is not None
                            and definition.get("available", True) is True else None)
            if requirements is None:
                unusable.append(key)
                continue
            minimum = definition.get("min_count")
            if minimum is not None and (not positive_count(minimum) or not positive_count(count) or count < minimum):
                continue
            bounds = (definition.get("min_value"), definition.get("max_value"))
            if any(bound is not None and not numeric(bound) for bound in bounds) or (
                bounds[0] is not None and value < bounds[0] or bounds[1] is not None and value > bounds[1]
            ):
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
    available, _ = extract_available_metrics(metrics, registry, evidence_type="model_validation", category=VALIDATION,
                                             count=validation["n_test"])
    return [key for key, requirements in available.items() if has_metric_metadata(validation, requirements, nested=metrics)]


def error_keys(record, catalog, registry=None):
    errors = obj(obj(record.get("association")).get("error_metrics"))
    if errors.get("availability") not in (None, "available"):
        return [], []
    available, unusable = extract_available_metrics(
        errors, registry, evidence_type=INDIRECT, category=ASSOCIATION, count=errors.get("n_pairs"),
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


def is_public_active(row):
    return row.get("status") == "active" and row.get("is_public", True) is True and row.get("visibility", "public") == "public"


def same_release(envelope, other):
    return all(text(envelope.get(key)) and envelope[key] == other.get(key) for key in RELEASE_FIELDS)


def public_contract(envelope, catalog):
    return (envelope.get("ok") is True and catalog.get("ok") is True
            and envelope.get("publication_status") == catalog.get("publication_status") == "public_release"
            and envelope.get("evidence_schema_version") == "1.5.0" and envelope.get("api_contract_version") == "1.0"
            and same_release(envelope, catalog))


def published(row, key):
    return obj(row.get("metric_availability")).get(key, True) is True


def check_linear_fit(row, registry):
    kind = row["evidence_type"]
    interpretation = "descriptive_parity" if kind == DIRECT else "descriptive_association"
    result = {"linear_fit_available": False, "reportable_linear_fit_metrics": [],
              "linear_fit_interpretation": interpretation, "linear_fit_status": row.get("linear_fit_status")}
    if row.get("linear_fit_status") != "ok":
        return result, ["LINEAR_FIT_UNAVAILABLE"]
    fit = obj(row.get("linear_fit"))
    x_unit, y_unit, count = row.get("x_unit"), row.get("y_unit"), row.get("linear_fit_n_pairs")
    if (not text(x_unit) or not text(y_unit) or fit.get("formula") != "Y = a X + b"
            or fit.get("scope") != FIT_SCOPE or fit.get("is_validated_calibration") is not False
            or fit.get("a_unit") not in (f"({y_unit})/({x_unit})", "dimensionless" if x_unit == y_unit else None)
            or fit.get("a_unit") is None or fit.get("b_unit") != y_unit or row.get("linear_fit_method") != METHOD):
        return result, ["LINEAR_FIT_METADATA_UNVERIFIED"]
    if (not positive_count(count) or count < 2 or
            any(positive_count(row.get(key)) and count > row[key] for key in ("n_pairs", "n_unique_polymers")) or
            not all(numeric(row.get(key)) for key in FIT_FIELDS[:2])):
        return result, ["LINEAR_FIT_INVALID"]
    metrics, _ = extract_available_metrics(row, registry, evidence_type=kind, category=FIT, count=count)
    def fit_definition_ok(key, requirements):
        definition = applicable_definition((registry or {}).get(key, []), kind, FIT)
        if definition is None:
            return False
        detail = obj(obj(row.get("metric_definitions")).get(key))
        units = dict(linear_fit_a=fit["a_unit"], linear_fit_b=fit["b_unit"], linear_fit_r2="dimensionless")
        if key not in units:
            axis_unit = {"X": x_unit, "Y": y_unit, "Y/X": fit["a_unit"], "dimensionless": "dimensionless"}
            units[key] = axis_unit.get(definition.get("unit_basis")) if text(definition.get("unit_basis")) else None
            if not units[key]:
                return False
        metadata = {"metric_basis": FIT_SCOPE, "metric_unit": units[key]}
        return (published(row, key)
                and definition.get("method", METHOD) == METHOD and definition.get("fit_scope", FIT_SCOPE) == FIT_SCOPE
                and definition.get("is_validated_calibration", False) is False
                and all(name not in definition or definition[name] == value for name, value in detail.items())
                and has_metric_metadata(metadata, requirements))
    reportable = [key for key, requirements in metrics.items() if fit_definition_ok(key, requirements)]
    if not all(key in reportable for key in FIT_FIELDS[:2]):
        return result, ["LINEAR_FIT_METADATA_UNVERIFIED"]
    warnings = []
    r2 = row.get("linear_fit_r2")
    if r2 is not None and (not numeric(r2) or not -1e-12 <= r2 <= 1 + 1e-12):
        reportable = [key for key in reportable if key != "linear_fit_r2"]
        warnings.append("LINEAR_FIT_R2_INVALID")
    elif r2 is not None and "linear_fit_r2" not in reportable:
        warnings.append("LINEAR_FIT_R2_UNVERIFIED")
    result.update(linear_fit_available=True, reportable_linear_fit_metrics=reportable,
                  linear_fit_slope_unit="dimensionless" if x_unit == y_unit else fit["a_unit"],
                  linear_fit_intercept_unit=fit["b_unit"])
    return result, warnings


def validation_link(row, envelope, supplied, *, member):
    inline = row.get("source_member_validation" if member else "source_model_validation")
    identifier = obj(inline).get("evidence_id") if member else row.get("source_model_validation_evidence_id")
    if inline is None and identifier is None:
        return None, "not_provided"
    if supplied is not None:
        supplied = obj(supplied)
        if not same_release(envelope, supplied) or supplied.get("ok") is not True or supplied.get("publication_status") != "public_release":
            return None, "mismatch"
        linked = obj(supplied.get("record"))
        if any(key in linked and linked[key] != value for key, value in obj(inline).items() if key in (
            "evidence_id", "model_id", "related_source_model_id", "validated_property_id", "evaluation_mode",
        )):
            return None, "mismatch"
    else:
        linked = obj(inline)
    if not (text(identifier) and linked.get("evidence_id") == identifier and is_public_active(linked)
            and linked.get("evidence_type") == VALIDATION and linked.get("model_role") == "source_surrogate_md"
            and linked.get("validation_target_kind") == "md_simulation" and text(linked.get("model_id"))
            and linked.get("validated_property_id") == row.get("source_property_id")
            and text(linked.get("evaluation_protocol_id"))):
        return None, "mismatch"
    if member:
        correct = (linked.get("evaluation_mode") == SEED_MODE and linked.get("evaluated_model_scope") == SEED_SCOPE
                   and linked.get("source_aggregation") in ("ensemble_mean", "ensemble_median")
                   and linked.get("related_source_model_id") == row.get("source_model_id"))
    else:
        parent_aggregation = obj(row.get("source_member_validation")).get("source_aggregation")
        correct = (linked.get("evaluation_mode") in (None, "legacy_model_validation")
                   and linked.get("evaluated_model_scope") in (None, "independent_model_prediction")
                   and linked.get("model_id") == row.get("source_model_id")
                   and (not parent_aggregation or linked.get("source_aggregation") in (None, parent_aggregation))
                   and linked.get("is_out_of_sample") is True and linked.get("training_overlap") == "none")
    return (linked, "matched") if correct else (None, "mismatch")


def member_metric_keys(link, registry, source_unit):
    expected, present, eligible, used = (link.get("n_seeds_" + name) for name in ("expected", "present", "eligible", "with_any_metric"))
    coverage = link.get("seed_coverage_fraction")
    app = obj(link.get("applicability"))
    min_rows, median, max_rows = (link.get("seedwise_n_test_" + key) for key in ("min", "median", "max"))
    policy = obj(app.get("selection_policy"))
    minimum, fraction = policy.get("min_valid_seeds"), policy.get("min_valid_seed_fraction")
    if not (all(positive_count(value) for value in (expected, present, eligible, used)) and used <= eligible <= present <= expected
            and numeric(coverage) and math.isclose(coverage, used / expected)
            and app.get("expected_members") == expected and app.get("coverage_fraction") == coverage
            and app.get("scope") == SEED_SCOPE and type(app.get("replicate_test_sets_may_overlap")) is bool
            and positive_count(min_rows) and positive_count(max_rows) and numeric(median) and min_rows <= median <= max_rows
            and positive_count(minimum) and numeric(fraction) and 0 <= fraction <= 1
            and positive_count(policy.get("min_test_rows")) and min_rows >= policy["min_test_rows"]
            and text(link.get("seedwise_aggregation_policy_id")) and text(source_unit) and link.get("metric_unit") == source_unit):
        return []
    result = []
    for key, value in link.items():
        definition = applicable_definition((registry or {}).get(key, []), VALIDATION, MEMBER)
        if definition is None or not published(link, key) or not numeric(value):
            continue
        base, _, stat = key.rpartition("_")
        base = definition.get("base_metric", base)
        if not is_metric_id(base):
            continue
        count = link.get(base + "_n_seeds")
        if (stat not in SEED_STATS or not positive_count(count) or not minimum <= count <= used
                or count / expected < fraction or (stat == "std" and (count < 2 or value < 0))):
            continue
        known_unit = "dimensionless" if base in ("pearson_r", "spearman_rho", "r2") else source_unit if base in SEED_METRICS else None
        metric_unit = obj(link.get("seedwise_metric_units")).get(base)
        basis = definition.get("unit_basis")
        if (not text(metric_unit) or (known_unit and metric_unit != known_unit)
                or (basis == "dimensionless" and metric_unit != "dimensionless")
                or (basis == "Source MD property unit" and metric_unit != source_unit)
                or (basis not in (None, "dimensionless", "Source MD property unit"))
                or (not known_unit and not (basis or definition.get("unit") or definition.get("metric_unit")))
                or (stat != "std" and not metric_value_valid(base, value, min_rows))):
            continue
        available, _ = extract_available_metrics({key: value}, registry, evidence_type=VALIDATION, category=MEMBER, count=count)
        if key in available and has_metric_metadata({**link, "metric_unit": metric_unit}, available[key]):
            result.append(key)
    return sorted(result)


def check_v15(envelope, catalog, *, metrics_registry=None, member_validation=None, independent_validation=None):
    row, catalog = obj(envelope.get("record")), obj(catalog)
    kind = row.get("evidence_type")
    if not public_contract(envelope, catalog) or not is_public_active(row) or kind not in (DIRECT, INDIRECT):
        return {"compatible": False, "reason": "PUBLIC_CONTRACT_OR_STATUS_UNVERIFIED"}
    semantics = obj(obj(catalog.get("available_evidence_types")).get(kind))
    axes = AXES if kind == INDIRECT else DIRECT_AXES
    if any(row.get(key) != value or semantics.get(key) != value for key, value in axes.items()):
        return {"compatible": False, "reason": "INCOMPATIBLE_INDIRECT_AXES" if kind == INDIRECT else "INCOMPATIBLE_DIRECT_AXES"}
    source, target = (row.get(key) for key in (("source_property_id", "experimental_target_property_id") if kind == INDIRECT
                                              else ("md_property_id", "experimental_property_id")))
    if not all(map(text, (source, target, row.get("evidence_id")))):
        return {"compatible": False, "reason": "PROPERTY_ID_UNVERIFIED"}
    if kind == INDIRECT:
        if row.get("trained_on_experimental_target_labels") is not False or not text(row.get("source_model_id")):
            return {"compatible": False, "reason": "SOURCE_ONLY_TRAINING_UNVERIFIED"}
        if semantics.get("same_private_structure") is not True or row.get("same_private_structure", True) is not True:
            return {"compatible": False, "reason": "STRUCTURE_PAIRING_UNVERIFIED"}
    elif semantics.get("scope") != "matched structures":
        return {"compatible": False, "reason": "STRUCTURE_PAIRING_UNVERIFIED"}
    registry = resolve_metrics_registry(metrics_registry if metrics_registry is not None else catalog)
    fit, warnings = check_linear_fit(row, registry)
    correlations, _ = extract_available_metrics(row, registry, evidence_type=kind, category=CORRELATION, count=row.get("n_pairs"))
    result = {"compatible": True, **fit, "reportable_comparison_metrics": [
        key for key, requirements in correlations.items() if published(row, key) and has_metric_metadata(row, requirements)
    ], "warnings": warnings}
    if kind == DIRECT:
        return result
    error_ids = set(ERROR_KEYS) | {key for key, definitions in (registry or {}).items()
                                  if applicable_definition(definitions, INDIRECT, ASSOCIATION) is not None}
    errors = {key: row.get(key) for key in error_ids}
    errors.update({key: row.get("error_metric_" + key) for key in ("basis", "unit", "definition", "n_pairs", "availability")})
    errors["metric_basis"], errors["metric_unit"] = errors.pop("basis"), errors.pop("unit")
    errors.update(reference_id=row.get("error_reference_id"), signed_error_definition=row.get("signed_error_definition"))
    raw_compatible = row.get("property_definition_match") == "exact" and row.get("x_unit") == row.get("y_unit") == errors["metric_unit"]
    keys, error_warnings = error_keys({"association": {"error_metrics": errors}, "variables": {
        "property_definition_match": "exact" if raw_compatible else None,
    }}, semantics, registry)
    result["reportable_association_errors"] = [key for key in keys if published(row, key)]
    warnings.extend(error_warnings)
    for role, supplied in (("member", member_validation), ("independent", independent_validation)):
        is_member = role == "member"
        link, status = validation_link(row, envelope, supplied, member=is_member)
        keys = []
        if link and is_member:
            keys = member_metric_keys(link, registry, row.get("x_unit"))
        if link and not is_member:
            keys = source_validation_metric_keys({"model_validation": {**link, "metrics": link}}, registry)
            keys = [key for key in keys if published(link, key) and (
                key not in ("mae", "rmse", "mean_signed_error") or link.get("metric_unit") == row.get("x_unit"))]
        prefix = "source_" + role + "_validation"
        result.update({prefix + "_matches": link is not None, prefix + "_metrics_available": bool(keys),
                       prefix + "_status": ("verified" if keys else "metrics_unavailable") if link else status,
                       "reportable_" + prefix + "_metrics": keys})
        if not keys:
            warnings.append("SOURCE_" + role.upper() + "_VALIDATION_" + ("METRICS_UNAVAILABLE" if link else status.upper()))
        if is_member:
            result[prefix + "_scope"] = "member_diagnostics" if link else None
            independence = (link or {}).get("seedwise_independence_status")
            out_of_sample = (link or {}).get("is_out_of_sample")
            result[prefix + "_independence"] = (
                "in_sample_or_non_independent" if out_of_sample is False or independence == "contains_known_overlap"
                else "out_of_sample_per_member" if independence == "verified_per_seed_only"
                else "unknown" if link else None)
    result.update(source_validation_matches=result["source_independent_validation_matches"],
                  source_validation_metrics_available=result["source_independent_validation_metrics_available"],
                  reportable_source_validation_metrics=result["reportable_source_independent_validation_metrics"])
    return result


def check_direct(record, *, catalog=None, metrics_registry=None):
    envelope = obj(record)
    if obj(envelope.get("record")).get("evidence_type") != DIRECT:
        return {"compatible": False, "reason": "INACTIVE_OR_WRONG_TYPE"}
    return check_v15(envelope, catalog, metrics_registry=metrics_registry)


def check_indirect(record, catalog_semantics=None, source_validation=None, metrics_registry=None, *, catalog=None,
                   member_validation=None, independent_validation=None):
    if "record" in obj(record):
        if obj(record["record"]).get("evidence_type") != INDIRECT:
            return {"compatible": False, "reason": "INACTIVE_OR_WRONG_TYPE"}
        return check_v15(record, catalog, metrics_registry=metrics_registry,
                         member_validation=member_validation, independent_validation=independent_validation)
    record, semantics = obj(record), obj(catalog_semantics)
    variables, context = obj(record.get("variables")), obj(record.get("model_context"))
    if not is_public_active(record) or record.get("evidence_type") != INDIRECT:
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
        "linear_fit_available": False, "reportable_linear_fit_metrics": [],
    }


def fit_scale_value(value, source_unit, fit_unit):
    if not numeric(value) or not text(source_unit) or not text(fit_unit):
        return None
    source_unit = source_unit.replace("³", "^3").replace("·", "*")
    fit_unit = fit_unit.replace("³", "^3").replace("·", "*")
    try:
        value = float(value)
    except OverflowError:
        return None
    if (source_unit, fit_unit) == ("°C", "K"):
        return value + 273.15
    if (source_unit, fit_unit) == ("K", "°C"):
        return value - 273.15
    return value if source_unit == fit_unit else None


def range_status(bounds, value):
    if bounds is None:
        return "unknown"
    low, high = obj(bounds).get("min"), obj(bounds).get("max")
    if not numeric(low) or not numeric(high) or low > high:
        return "invalid"
    return "inside" if low <= value <= high else "outside"


def compare_conditions(expected, supplied):
    expected = {key: value for key, value in obj(expected).items() if key != "source_doi"}
    supplied = obj(supplied)
    common = expected.keys() & supplied.keys()
    if any(type(supplied[key]) is bool or expected[key] != supplied[key] for key in common):
        return "incompatible"
    return "matched" if expected and expected.keys() == supplied.keys() else "unknown"


def source_predictor_matches(row, fit, predictor):
    # Member and independent MD evaluation links are never fit input specifications.
    model = obj(fit.get("source_predictor"))
    observed = obj(predictor.get("source_predictor"))
    fields = ("model_revision", "aggregation", "preprocessing", "prediction_mode")
    return (observed.get("model_id") == row["source_model_id"]
            and model.get("model_id") == row["source_model_id"]
            and all(text(model.get(key)) and model[key].lower() not in {"unknown", "not_recorded"}
                    and model[key] == observed.get(key) for key in fields)
            and row.get("source_prediction_mode", model["prediction_mode"]) == model["prediction_mode"]
            and row.get("source_aggregation", model["aggregation"]) == model["aggregation"])


def reliability_action(catalog, applicability, predictor, value):
    if predictor["origin"] != DIRECT_AXES["x_origin"]:
        return None
    property_id = predictor["property_id"]
    entries = catalog.get("properties")
    properties = entries if isinstance(entries, list) else []
    relevant = [prop for prop in properties if obj(prop).get("property_id") == property_id]
    checks = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}
    caution = False
    for scope in [applicability, *relevant]:
        for rule in scope.get("md_value_reliability_cautions") or []:
            rule = obj(rule)
            if rule.get("applies_to") != "md_calculated_property" or rule.get("property_id") != property_id:
                continue
            operation = rule.get("operator")
            check = checks.get(operation) if text(operation) else None
            observed = fit_scale_value(value, predictor["unit"], rule.get("unit"))
            threshold = rule.get("threshold")
            if check is None or observed is None or not numeric(threshold):
                return "unverified"
            if check(observed, threshold):
                if rule.get("effect") == "prohibit_inference":
                    return "prohibited"
                if rule.get("effect") != "limited_reliability":
                    return "unverified"
                caution = True
    return "caution" if caution else None


def proxy_direction(pearson, spearman, target_direction):
    """Return a directional cue from reportable metrics. Judge proxy strength separately."""
    signs = {value > 0 for value in (pearson, spearman) if numeric(value) and 0 < abs(value) <= 1}
    if len(signs) != 1 or target_direction not in ("higher", "lower"):
        return None
    return "higher" if signs.pop() == (target_direction == "higher") else "lower"


def experimental_minimum_prefilter(slope, intercept, minimum):
    if not numeric(minimum):
        return None
    if slope == 0:
        return {"constant_meets_exploratory_minimum": intercept >= minimum}
    try:
        boundary = (float(minimum) - intercept) / slope
    except OverflowError:
        return None
    return {"operator": ">=" if slope > 0 else "<=", "x_bound": boundary} if math.isfinite(boundary) else None


def _estimate_from_comparison(envelope, catalog, estimate_request, comparison):
    envelope, catalog = obj(envelope), obj(catalog)
    row, request = obj(envelope.get("record")), obj(estimate_request)
    predictor = obj(request.get("predictor"))
    fit, applicability = obj(row.get("linear_fit")), obj(row.get("applicability"))
    source_revision = envelope.get("polyomics_data_revision")
    comparison_kind = row.get("evidence_type")
    decision = {
        "status": "unavailable", "level": None, "applicability": "unknown",
        "reason_codes": [], "value": None, "unit": None,
        "evidence_id": None, "release_id": None, "evidence_dataset_revision": None,
        "polyomics_data_revision": None, "predictor_origin": predictor.get("origin"),
        "validation_scope": "independent_experimental_validation_not_provided",
        "experimental_compliance_established": False,
        "evidence_warnings": [],
    }

    def stop(status, reason):
        decision.update(status=status, reason_codes=[reason])
        if status == "incompatible":
            decision["applicability"] = "incompatible"
        if status == "proxy_only":
            keys = comparison.get("reportable_comparison_metrics", [])
            decision["proxy_direction_hint"] = proxy_direction(
                row.get("pearson_r") if "pearson_r" in keys else None,
                row.get("spearman_rho") if "spearman_rho" in keys else None,
                request.get("target_direction"),
            )
        return decision

    if (not comparison.get("compatible") or not public_contract(envelope, catalog)
            or source_revision != catalog.get("polyomics_data_revision") or not is_public_active(row)):
        return stop("unavailable", "PUBLIC_CONTRACT_OR_STATUS_UNVERIFIED")
    decision.update(
        unit=row.get("y_unit"), evidence_id=row["evidence_id"], release_id=envelope["release_id"],
        evidence_dataset_revision=envelope["evidence_dataset_revision"], polyomics_data_revision=source_revision,
        evidence_warnings=[warning["code"] for warning in row.get("warnings") or []
                           if text(obj(warning).get("code"))],
    )
    if any(scope.get("quantitative_use") == "prohibited" for scope in (fit, applicability, row, catalog)):
        return stop("prohibited", "POLICY_RESTRICTED")
    source_key = "md_property_id" if comparison_kind == DIRECT else "source_property_id"
    target_key = "experimental_property_id" if comparison_kind == DIRECT else "experimental_target_property_id"
    if request.get("target_property_id") != row[target_key] or (predictor and predictor.get("property_id") != row[source_key]):
        return stop("incompatible", "PROPERTY_ID_MISMATCH")
    if not comparison.get("linear_fit_available"):
        if comparison_kind == INDIRECT and comparison.get("reportable_comparison_metrics"):
            return stop("proxy_only", "FIT_UNAVAILABLE")
        return stop("unavailable", "FIT_UNAVAILABLE")
    if not predictor:
        if comparison_kind == INDIRECT:
            return stop("proxy_only", "SOURCE_PREDICTOR_UNAVAILABLE")
        return stop("unavailable", "PREDICTOR_UNAVAILABLE")
    if predictor.get("origin") != row.get("x_origin"):
        route = "proxy_only" if comparison_kind == INDIRECT and predictor.get("origin") == "md_simulation" else "incompatible"
        return stop(route, "PREDICTOR_ORIGIN_MISMATCH")
    if not text(predictor.get("source_reference")):
        return stop("unavailable", "PREDICTOR_PROVENANCE_UNVERIFIED")
    if comparison_kind == INDIRECT and not source_predictor_matches(row, fit, predictor):
        return stop("proxy_only", "MODEL_IDENTITY_UNVERIFIED")
    if predictor.get("scale") != "linear" or any(
        fit.get(key, row.get(key, "linear")) != "linear" for key in ("x_scale", "y_scale")
    ):
        return stop("incompatible", "SCALE_MISMATCH_OR_UNSUPPORTED")
    predictor_value = predictor.get("value")
    if not numeric(predictor_value):
        return stop("incompatible", "PREDICTOR_VALUE_INVALID")
    value = fit_scale_value(predictor_value, predictor.get("unit"), row["x_unit"])
    if value is None:
        return stop("incompatible", "PREDICTOR_UNIT_MISMATCH_OR_VALUE_OVERFLOW")

    target_conditions = compare_conditions(applicability.get("experimental_conditions"), request.get("target_conditions"))
    md_conditions = compare_conditions(applicability.get("md_conditions"), predictor.get("md_conditions"))
    if "incompatible" in (target_conditions, md_conditions):
        return stop("incompatible", "CONDITIONS_MISMATCH")
    if comparison_kind == DIRECT:
        definition = row.get("definition_compatibility")
        compatible = definition == "exact" or (
            definition == "conditional_match_zero_humidity_extrapolation"
            and text(applicability.get("definition_compatibility_detail")) and target_conditions == "matched"
        )
        if not compatible:
            return stop("incompatible", "PROPERTY_DEFINITION_UNVERIFIED")
    domain = range_status(fit.get("x_range"), value)
    if domain in ("outside", "invalid"):
        return stop("incompatible", "DOMAIN_INCOMPATIBLE")
    action = reliability_action(catalog, applicability, predictor, predictor_value)
    if action == "prohibited":
        return stop("prohibited", "RELIABILITY_RULE_PROHIBITS_INFERENCE")
    if action == "unverified":
        return stop("unavailable", "RELIABILITY_RULE_UNVERIFIED")

    try:
        a, b = float(row["linear_fit_a"]), float(row["linear_fit_b"])
        estimate = a * value + b
    except OverflowError:
        return stop("incompatible", "NONFINITE_ESTIMATE")
    if not math.isfinite(estimate):
        return stop("incompatible", "NONFINITE_ESTIMATE")
    physical_range = range_status(applicability.get("y_physical_range"), estimate)
    if physical_range in ("outside", "invalid"):
        return stop("incompatible", "Y_PHYSICAL_RANGE_VIOLATION")

    limitations = []
    if domain == "unknown":
        limitations.append("DOMAIN_UNKNOWN")
    if "unknown" in (target_conditions, md_conditions):
        limitations.append("CONDITIONS_UNVERIFIED")
    if source_revision in (None, "", "not_recorded"):
        limitations.append("ORIGINAL_MD_REVISION_UNKNOWN")
    elif predictor.get("md_dataset_revision") != source_revision:
        limitations.append("ORIGINAL_MD_REVISION_NOT_MATCHED")
    if action == "caution":
        limitations.append("MD_VALUE_RELIABILITY_CAUTION")
    decision.update(
        status="conditional_exploratory" if limitations else "eligible_exploratory",
        level="B", applicability="unknown" if limitations else "matched",
        reason_codes=[*limitations, "UNQUANTIFIED_UNCERTAINTY", "INDEPENDENT_EXPERIMENTAL_VALIDATION_NOT_PROVIDED"],
        value=estimate, predictor_value_on_fit_scale=value, predictor_fit_unit=row["x_unit"],
        slope_direction="increasing" if a > 0 else "decreasing" if a < 0 else "constant",
        candidate_x_prefilter=None if action else experimental_minimum_prefilter(a, b, request.get("target_minimum")),
    )
    return decision


def check_estimate(envelope, catalog, estimate_request, *, metrics_registry=None):
    """Check trusted public evidence and evaluate a caller-verified candidate on its fit scale."""
    envelope = obj(envelope)
    comparison = check_v15(envelope, catalog, metrics_registry=metrics_registry)
    return _estimate_from_comparison(envelope, catalog, estimate_request, comparison)


if __name__ == "__main__":
    request = obj(json.load(sys.stdin))
    record = obj(request.get("record"))
    options = {"metrics_registry": request.get("metrics_registry"), "catalog": request.get("catalog")}
    if obj(record.get("record")).get("evidence_type") == DIRECT:
        decision = check_direct(record, **options)
    else:
        decision = check_indirect(record, request.get("catalog_semantics"), request.get("source_validation"),
                                  member_validation=request.get("member_validation"),
                                  independent_validation=request.get("independent_validation"), **options)
    if "estimate_request" in request:
        decision["estimate"] = _estimate_from_comparison(record, options["catalog"], request["estimate_request"], decision)
    print(json.dumps(decision))

"""Read-only deployment smoke test. Writes metadata and schema hashes, never rows."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx
import jsonschema
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from package_releases import ROOT

sys.path.insert(0, str(ROOT / "skills" / "polyomics-search" / "scripts"))
from check_evidence import DIRECT, INDIRECT, VALIDATION, RELEASE_FIELDS, check_direct, check_indirect, same_release

SEARCH = {"get_dataset_info", "list_search_fields", "search_polymers", "get_polymer", "aggregate_polymers"}
EVIDENCE = {"get_sim2real_catalog", "search_sim2real_evidence", "get_sim2real_evidence"}
CATALOG, FIND, DETAIL = "get_sim2real_catalog", "search_sim2real_evidence", "get_sim2real_evidence"
BASELINE = ROOT / "docs" / "live-mcp.json"
MAX_PAGES = 8


class CheckFailure(ValueError):
    """Controlled diagnostic safe to write into a release report."""


def require(condition, reason):
    if not condition:
        raise CheckFailure(reason)


def fingerprint(schema):
    return hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def unpack(result):
    if result.isError:
        raise CheckFailure("MCP returned a tool error")
    candidates = [result.structuredContent]
    for item in result.content:
        if item.type == "text":
            try:
                candidates.append(json.loads(item.text))
            except json.JSONDecodeError:
                continue
    envelopes = [candidate for candidate in candidates if isinstance(candidate, dict) and isinstance(candidate.get("ok"), bool)]
    require(envelopes and all(item == envelopes[0] for item in envelopes), "Missing or conflicting PolyOmics JSON envelopes")
    return envelopes[0]


async def verify(endpoint, report, include_smarts, evidence="auto"):
    transport = httpx.AsyncHTTPTransport(retries=2, trust_env=False)
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=20), transport=transport, trust_env=False) as client:
        async with streamable_http_client(endpoint, http_client=client) as (receive, send, _):
            async with ClientSession(receive, send, read_timeout_seconds=timedelta(seconds=90)) as session:
                report["stage"] = "initialize"
                initialized = await session.initialize()
                report["protocol_version"] = initialized.protocolVersion
                report["server"] = {"name": initialized.serverInfo.name, "version": initialized.serverInfo.version}
                await verify_session(session, report, include_smarts, evidence)


async def verify_session(session, report, include_smarts, evidence):
    report["stage"] = "tools/list"
    tools, cursors = {}, set()
    page = await session.list_tools()
    for _ in range(MAX_PAGES):
        for tool in page.tools:
            require(tool.name not in tools, "Duplicate MCP tool name")
            tools[tool.name] = tool
            jsonschema.Draft202012Validator.check_schema(tool.inputSchema)
            if tool.outputSchema is not None:
                jsonschema.Draft202012Validator.check_schema(tool.outputSchema)
        cursor = page.nextCursor
        if not cursor:
            break
        require(cursor not in cursors, "MCP tool discovery cursor loop")
        cursors.add(cursor)
        page = await session.list_tools(cursor=cursor)
    else:
        raise CheckFailure("MCP tool discovery page limit exceeded")
    report["tools"] = {name: fingerprint(tool.inputSchema) for name, tool in sorted(tools.items())}
    report["output_schema_hashes"] = {name: fingerprint(tool.outputSchema) for name, tool in tools.items() if tool.outputSchema is not None}
    report["tool_annotations"] = {}
    for name, tool in sorted(tools.items()):
        annotations = getattr(tool, "annotations", None)
        report["tool_annotations"][name] = {
            key: getattr(annotations, key, None) for key in ("readOnlyHint", "destructiveHint", "openWorldHint")
        }
    report["missing_evidence_tools"] = sorted(EVIDENCE - tools.keys())
    require(SEARCH <= tools.keys(), "Expected simulation tools missing")
    old = json.loads(BASELINE.read_bytes())["tools"]
    report["md_schema_changes"] = {name: {"previous": old.get(name), "current": report["tools"][name]}
                                   for name in sorted(SEARCH) if old.get(name) != report["tools"][name]}
    require(not report["md_schema_changes"], "Existing MD input schema differs from the baseline")
    checks = report.setdefault("checks", {})
    checks["L01_discovery_and_baseline"] = True

    async def call(name, args, expected_error=None):
        report["stage"] = name
        tool = tools[name]
        jsonschema.Draft202012Validator(tool.inputSchema).validate(args)
        result = await session.call_tool(name, args)
        report["tool_calls"] = report.get("tool_calls", 0) + 1
        response = unpack(result)
        if tool.outputSchema is not None:
            data = result.structuredContent if result.structuredContent is not None else response
            jsonschema.Draft202012Validator(tool.outputSchema).validate(data)
        if expected_error:
            require(not response["ok"] and response.get("error", {}).get("code") == expected_error,
                    "Expected public application error was not returned")
            return response
        require(response["ok"], "Unsuccessful PolyOmics tool response")
        if name in SEARCH and "dataset_revision" in report:
            require(response.get("dataset_revision") == report["dataset_revision"], "MD dataset revision changed")
        return response

    await verify_md(call, report, include_smarts)
    checks["L13_md_search"] = True
    found = EVIDENCE & tools.keys()
    if evidence == "off":
        report["evidence_status"] = "off"
    elif not found:
        report["evidence_status"] = "not_deployed"
        require(evidence != "require", "Evidence tools are required but not deployed")
    elif found != EVIDENCE:
        report["evidence_status"] = "partial_deployment"
        raise CheckFailure("Only some Evidence tools are deployed")
    else:
        report["evidence_status"] = "checking"
        await verify_evidence(call, report, evidence)


async def verify_md(call, report, include_smarts):
    dataset = await call("get_dataset_info", {})
    report["dataset_revision"] = dataset["dataset_revision"]
    report["record_count"] = dataset["record_count"]
    info = await call("list_search_fields", {"category": "all"})
    properties = {field["name"]: field.get("unit") for field in info["fields"]}
    require({"UUID", "search_smiles", "density", "thermal_conductivity", "class_PIMD"} <= properties.keys(), "Required MD fields are missing")
    report["units"] = {name: properties[name] for name in ("density", "thermal_conductivity")}
    filters = {"polymer_classes": ["PIMD"], "property_filters": [{"field": "density", "min": 1.3}]}
    fields = ["UUID", "search_smiles", "density", "thermal_conductivity"]
    found = await call("search_polymers", {"request": {
        **filters, "fields": fields, "sort": {"field": "thermal_conductivity", "direction": "desc"},
        "limit": 3, "include_total_count": True,
    }})
    rows = found["results"]
    ordered = [row["thermal_conductivity"] for row in rows]
    require(rows and all(row["density"] >= 1.3 for row in rows) and None not in ordered and ordered == sorted(ordered, reverse=True),
            "Constrained MD search did not satisfy bounds and sort")
    detail = await call("get_polymer", {"uuid": rows[0]["UUID"], "fields": fields})
    require(detail["record"] == rows[0], "MD search and exact detail disagree")
    stats = await call("aggregate_polymers", {"request": {
        **filters, "properties": ["density"], "statistics": ["mean", "min", "max"],
    }})
    require(stats["matching_record_count"] == found["total_matches"], "MD search and aggregate cohort sizes disagree")
    report["constrained_search"] = {"match_count": found["total_matches"], "detail_and_aggregate_verified": True}
    await call("search_polymers", {"request": {
        "property_filters": [{"field": "density", "min": 2.0, "max": 1.0}],
    }}, expected_error="INVALID_ARGUMENT")
    report["invalid_bounds_rejected"] = True
    if include_smarts:
        structure = await call("search_polymers", {"request": {
            **filters, "fields": ["UUID", "search_smiles"], "limit": 2,
            "structure": {"format": "smarts", "query": "c1ccccc1"}, "include_total_count": True,
        }})
        require(structure["results"], "No SMARTS match for constrained MD search")
        report["smarts_match_count"] = structure["total_matches"]


async def verify_evidence(call, report, mode):
    checks = report.setdefault("checks", {})
    catalog = await call(CATALOG, {"include_properties": True, "include_metric_definitions": True})
    require(catalog.get("evidence_schema_version") == "1.5.0" and catalog.get("api_contract_version") == "1.0"
            and catalog.get("publication_status") == "public_release" and same_release(catalog, catalog),
            "Missing supported public Evidence contract or release metadata")
    counts = catalog["record_counts"]
    registry = catalog["metrics_registry"]["metric_availability"]
    types = catalog["available_evidence_types"]
    require(isinstance(counts, dict) and all(type(counts.get(key)) is int and counts[key] >= 0 for key in (DIRECT, INDIRECT, VALIDATION, "transfer_scaling"))
            and catalog.get("data_access_policy") and all(key in types and key in registry for key in counts),
            "Catalog counts, types, public policy, or metric definitions are missing")
    revision = catalog["evidence_dataset_revision"]
    report["evidence_release"] = {key: catalog[key] for key in (*RELEASE_FIELDS, "polyomics_data_revision")}
    report["evidence_counts"] = counts
    checks["L02_catalog"] = True

    async def checked(name, args):
        out = await call(name, args)
        require(same_release(catalog, out) and out.get("polyomics_data_revision") == catalog["polyomics_data_revision"],
                "Evidence release changed during verification")
        return out

    async def search(kind, **kwargs):
        return await checked(FIND, {"evidence_type": kind, "limit": 2, **kwargs})

    async def detail(identifier):
        out = await checked(DETAIL, {"evidence_id": identifier, "evidence_revision": revision})
        require(out["record"]["evidence_id"] == identifier, "Evidence detail identity differs from the requested ID")
        return out

    if not any(counts.values()):
        sample = await search("all")
        require(not sample["items"] and sample["total_matches"] == 0, "Empty Catalog and search disagree")
        report["evidence_status"] = "empty_catalog"
        require(mode != "require", "Evidence release has no public records")
        return
    require(all(counts[key] > 0 for key in (DIRECT, INDIRECT, VALIDATION)), "Missing required Direct, Indirect or validation example")

    def compare(summary, row, keys):
        require(all(key in summary and key in row and summary[key] == row[key] for key in keys),
                "Evidence summary and detail fields disagree")

    fit_fields = ("evidence_id", "evidence_type", "linear_fit_a", "linear_fit_b", "linear_fit_r2", "linear_fit_method",
                  "linear_fit_status", "linear_fit_n_pairs", "x_origin", "y_origin", "x_unit", "y_unit")
    coverage = catalog["coverage"]
    props = {prop["property_id"]: prop for prop in catalog["properties"]}
    direct_md = coverage[DIRECT]["md_property_id"]
    aliased = next((key for key in direct_md if props[key].get("aliases")), None)
    require(aliased is not None, "Catalog lacks a Direct example with a registered alias")
    alias = props[aliased]["aliases"][0]
    canonical = await search(DIRECT, md_property_id=aliased)
    alias_result = await search(DIRECT, md_property_id=alias)
    require(canonical["items"] == alias_result["items"] and canonical["total_matches"] == alias_result["total_matches"]
            and alias_result["property_resolutions"]["md_property_id"]["resolved_property_id"] == aliased,
            "Catalog alias and canonical search disagree")
    checks["L10_alias"] = True
    direct = next((item for item in canonical["items"] if item["linear_fit_status"] == "ok"), None)
    require(direct and direct["evidence_type"] == DIRECT and direct["md_property_id"] == aliased, "Direct search did not return a fitted record for the filter")
    checks["L03_direct_search"] = True
    direct_detail = await detail(direct["evidence_id"])
    compare(direct, direct_detail["record"], fit_fields + ("md_property_id", "experimental_property_id"))
    direct_check = check_direct(direct_detail, catalog=catalog)
    require(direct_check.get("linear_fit_available") and direct_check["linear_fit_interpretation"] == "descriptive_parity",
            "Local validator rejected the published Direct fit")
    checks["L04_direct_fit"] = direct_check["reportable_linear_fit_metrics"]

    md_ids = coverage[INDIRECT]["source_property_id"]
    targets = coverage[INDIRECT]["experimental_target_property_id"]
    source = next(key for key in md_ids if md_ids[key] > 2)
    filters = {"md_property_id": source, "sort_by": "evidence_id"}
    initial = await search(INDIRECT, **filters)
    cursor = initial["next_cursor"]
    require(cursor and initial["offset"] == 0 and len(initial["items"]) == 2, "Missing initial Evidence page or cursor")
    follow = await search(INDIRECT, **filters, cursor=cursor)
    ids = [row["evidence_id"] for row in initial["items"] + follow["items"]]
    require(follow["offset"] == len(initial["items"]) and follow["items"] and len(ids) == len(set(ids))
            and ids == sorted(ids) and follow["total_matches"] == initial["total_matches"]
            and follow["next_cursor"] != cursor and bool(follow["next_cursor"]) == (len(ids) < follow["total_matches"])
            and all(row["source_property_id"] == source for row in initial["items"] + follow["items"]),
            "Evidence pages overlap, differ in total, or have a cursor or ordering mismatch")
    end = await search(INDIRECT, **filters, filters={"offset": initial["total_matches"] - 1})
    require(len(end["items"]) == 1 and end["next_cursor"] is None and end["total_matches"] == initial["total_matches"]
            and end["offset"] == initial["total_matches"] - 1, "Evidence paging did not terminate at the last record")
    checks["L09_paging"] = True

    association = next((row for row in initial["items"] + follow["items"]
                        if row["linear_fit_status"] == "ok" and row["x_unit"] != row["y_unit"]), None)
    require(association is not None and association["experimental_target_property_id"] in targets, "No fitted cross-property Indirect example")
    target = association["experimental_target_property_id"]
    selected = await search(INDIRECT, md_property_id=source, experimental_property_id=target)
    require(association["evidence_id"] in {item["evidence_id"] for item in selected["items"]}
            and all(row["source_property_id"] == source and row["experimental_target_property_id"] == target
                    for row in selected["items"]), "Indirect property filters do not match the record")
    checks["L05_indirect_search"] = True
    indirect_detail = await detail(association["evidence_id"])
    row = indirect_detail["record"]
    compare(association, row, fit_fields + ("source_property_id", "experimental_target_property_id", "pearson_r", "spearman_rho"))
    member = await detail(row["source_member_validation"]["evidence_id"])
    member_record = member["record"]
    compare(row["source_member_validation"], member_record, ("evidence_id", "model_id", "related_source_model_id",
                                                           "validated_property_id", "evaluation_mode", "n_seeds_expected"))
    independent_id = row["source_model_validation_evidence_id"]
    independent = await detail(independent_id) if independent_id else None
    outcome = check_indirect(indirect_detail, catalog=catalog, member_validation=member, independent_validation=independent)
    require(outcome.get("linear_fit_available") and outcome["reportable_comparison_metrics"]
            and outcome["linear_fit_interpretation"] == "descriptive_association", "Local validator rejected the Indirect fit or correlation")
    if row["error_metric_availability"] == "not_provided":
        require(not outcome["reportable_association_errors"], "Unreported Indirect error was unexpectedly reportable")
    else:
        require(outcome["reportable_association_errors"], "Published Indirect error lacks usable metadata")
    checks["L06_indirect_fit"] = outcome["reportable_linear_fit_metrics"]
    require(outcome["source_member_validation_metrics_available"], "Member diagnostic link or metrics could not be verified")
    checks["L07_member_validation"] = {"metrics": outcome["reportable_source_member_validation_metrics"],
                                       "members": member_record["n_seeds_expected"],
                                       "independence": outcome["source_member_validation_independence"]}
    independent_status = outcome["source_independent_validation_status"]
    require(independent_status == "not_provided" if independent is None else independent_status == "verified",
            "Independent Source-model evaluation does not match the declared link")
    checks["L08_independent_validation"] = independent_status
    report["selected_evidence_ids"] = [direct["evidence_id"], row["evidence_id"], member_record["evidence_id"]]

    scaling = await search("transfer_scaling")
    if counts["transfer_scaling"] == 0:
        require(not scaling["items"] and scaling["total_matches"] == 0 and scaling["status"] == "no_records",
                "Empty scaling Catalog and search disagree")
    else:
        require(scaling["items"] and scaling["total_matches"] > 0, "Published scaling records cannot be read")
    await call(DETAIL, {"evidence_id": "synthetic:missing-evidence-for-smoke-test"}, "NOT_FOUND")
    await call(FIND, {"experimental_property_id": "synthetic:unknown-property"}, "UNKNOWN_PROPERTY")
    checks["L11_public_errors_and_search_status"] = True
    for entry in (direct_detail["record"], row, member_record):
        require(entry["study"]["citation"] and isinstance(entry["population"], dict)
                and isinstance(entry["applicability"], dict) and isinstance(entry["warnings"], list) and "notes" in entry,
                "Citation, notes or applicability metadata is missing")
    checks["L12_provenance_and_cautions"] = {
        "original_md_revision": catalog["polyomics_data_revision"],
        "warning_codes": sorted({warn["code"] for entry in (catalog, direct_detail["record"], row, member_record) for warn in entry["warnings"]}),
    }
    report["evidence_status"] = "validated"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--smarts", action="store_true")
    parser.add_argument("--evidence", choices=("auto", "require", "off"), default="auto")
    options = parser.parse_args()
    endpoint = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]["polyomics"]["url"]
    report = {"endpoint": endpoint, "checked_at_utc": datetime.now(timezone.utc).isoformat(), "authentication": "none",
              "evidence_mode": options.evidence}
    try:
        asyncio.run(verify(endpoint, report, options.smarts, options.evidence))
    except Exception as error:
        while isinstance(error, BaseExceptionGroup) and error.exceptions:
            error = error.exceptions[0]
        report["error_type"] = type(error).__name__
        report["error"] = str(error) if isinstance(error, CheckFailure) else "See stage and error type; response and exception payloads are omitted."
        if report.get("evidence_status") in (None, "checking"):
            report["evidence_status"] = "unreachable" if isinstance(error, (TimeoutError, httpx.TransportError)) else "failed"
        report["ok"] = False
    else:
        report["ok"] = True
        report.pop("stage", None)
    result = json.dumps(report, indent=2, sort_keys=True)
    if options.output:
        options.output.write_text(result + "\n", encoding="utf-8")
    print(result)
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

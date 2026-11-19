"""Read-only deployment smoke test. Writes metadata and schema hashes, never rows."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import httpx
import jsonschema
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from package_releases import ROOT


SEARCH = {"get_dataset_info", "list_search_fields", "search_polymers", "get_polymer", "aggregate_polymers"}
EVIDENCE = {"get_sim2real_catalog", "search_sim2real_evidence", "get_sim2real_evidence"}


def unpack(result):
    if result.isError:
        raise RuntimeError("MCP returned a tool error")
    candidates = [result.structuredContent]
    for item in result.content:
        if item.type == "text":
            try:
                candidates.append(json.loads(item.text))
            except json.JSONDecodeError:
                continue
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get("ok"), bool):
            return candidate
    raise ValueError("No PolyOmics JSON response envelope")


async def verify(endpoint, report, include_smarts):
    transport = httpx.AsyncHTTPTransport(retries=2, trust_env=False)
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=20), transport=transport, trust_env=False) as client:
        async with streamable_http_client(endpoint, http_client=client) as (receive, send, _):
            async with ClientSession(receive, send, read_timeout_seconds=timedelta(seconds=90)) as session:
                report["stage"] = "initialize"
                initialized = await session.initialize()
                report["protocol_version"] = initialized.protocolVersion
                report["stage"] = "tools/list"
                page = await session.list_tools()
                tools = {tool.name: tool.inputSchema for tool in page.tools}
                while page.nextCursor:
                    page = await session.list_tools(cursor=page.nextCursor)
                    tools.update({tool.name: tool.inputSchema for tool in page.tools})
                for schema in tools.values():
                    jsonschema.Draft202012Validator.check_schema(schema)
                report["tools"] = {
                    name: hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                    for name, schema in sorted(tools.items())
                }
                report["evidence_status"] = "not_deployed" if not EVIDENCE & tools.keys() else "discovered_not_validated"
                report["missing_evidence_tools"] = sorted(EVIDENCE - tools.keys())
                if not SEARCH <= tools.keys():
                    raise ValueError("Expected simulation tools missing")

                async def call(name, args, expected_error=None):
                    report["stage"] = name
                    jsonschema.validate(args, tools[name])
                    response = unpack(await session.call_tool(name, args))
                    if expected_error and not response["ok"] and response.get("error", {}).get("code") == expected_error:
                        return response
                    if expected_error or not response["ok"]:
                        raise ValueError(f"Unexpected {name} outcome: {response.get('error', {}).get('code')}")
                    if "dataset_revision" in report and response.get("dataset_revision") != report["dataset_revision"]:
                        raise ValueError(f"Snapshot changed during {name}")
                    return response

                dataset = await call("get_dataset_info", {})
                report["dataset_revision"] = dataset["dataset_revision"]
                report["record_count"] = dataset["record_count"]
                info = await call("list_search_fields", {"category": "all"})
                properties = {field["name"]: field.get("unit") for field in info["fields"]}
                for field in ("UUID", "search_smiles", "density", "thermal_conductivity", "class_PIMD"):
                    if field not in properties:
                        raise ValueError(f"Missing expected field: {field}")
                report["units"] = {name: properties[name] for name in ("density", "thermal_conductivity")}
                filters = {"polymer_classes": ["PIMD"], "property_filters": [{"field": "density", "min": 1.3}]}
                fields = ["UUID", "search_smiles", "density", "thermal_conductivity"]
                found = await call("search_polymers", {"request": {
                    **filters, "fields": fields, "sort": {"field": "thermal_conductivity", "direction": "desc"},
                    "limit": 3, "include_total_count": True,
                }})
                rows = found["results"]
                ordered = [row["thermal_conductivity"] for row in rows]
                if not rows or not all(row["density"] >= 1.3 for row in rows) or None in ordered or ordered != sorted(ordered, reverse=True):
                    raise ValueError("Constrained search did not satisfy bounds and sort")
                detail = await call("get_polymer", {"uuid": rows[0]["UUID"], "fields": fields})
                if detail["record"] != rows[0]:
                    raise ValueError("Search and exact detail disagree")
                stats = await call("aggregate_polymers", {"request": {
                    **filters, "properties": ["density"], "statistics": ["mean", "min", "max"],
                }})
                if stats["matching_record_count"] != found["total_matches"]:
                    raise ValueError("Search and aggregate cohort sizes disagree")
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
                    if not structure["results"]:
                        raise ValueError("Expected a SMARTS match for the constrained test")
                    report["smarts_match_count"] = structure["total_matches"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--smarts", action="store_true")
    options = parser.parse_args()
    endpoint = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]["polyomics"]["url"]
    report = {"endpoint": endpoint, "checked_at_utc": datetime.now(timezone.utc).isoformat(), "authentication": "none"}
    try:
        asyncio.run(verify(endpoint, report, options.smarts))
    except Exception as error:
        while isinstance(error, BaseExceptionGroup) and error.exceptions:
            error = error.exceptions[0]
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
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

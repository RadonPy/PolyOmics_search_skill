import asyncio
import json
from types import SimpleNamespace

import httpx
import jsonschema
import pytest

import check_live_mcp as live
from check_evidence import DIRECT, INDIRECT, VALIDATION
from fixtures.synthetic_evidence_v15 import SOURCE, TARGET, STAMP, catalog, comparison, member


class FakeSession:
    def __init__(self, available=live.EVIDENCE, *, fault=None):
        self.names = sorted(live.SEARCH | set(available))
        self.calls = []
        self.fault = fault

    async def list_tools(self, cursor=None):
        names = self.names[4:] if cursor else self.names[:4]
        tools = [SimpleNamespace(name=name, inputSchema={"type": "object"}, outputSchema=None) for name in names]
        if self.fault == "output_schema":
            for tool in tools:
                tool.outputSchema = {"type": "object", "required": ["intentionally_missing"]}
        return SimpleNamespace(tools=tools, nextCursor="page2" if cursor is None else None)

    async def call_tool(self, name, arguments):
        self.calls.append(name)
        if self.fault == "network":
            raise httpx.ConnectError("private payload must never enter the report")
        if name == live.CATALOG:
            out = catalog()
            if self.fault == "empty":
                out["record_counts"] = dict.fromkeys(out["record_counts"], 0)
        elif name == live.DETAIL:
            identifier = arguments["evidence_id"]
            known = {value["record"]["evidence_id"]: value for value in (comparison(DIRECT), comparison(INDIRECT), member())}
            out = known.get(identifier, {"ok": False, "error": {"code": "NOT_FOUND"}})
            if self.fault == "fit" and identifier == "synthetic:" + INDIRECT:
                out["record"]["linear_fit"]["scope"] = "unknown_scale"
            if self.fault == "wrong_error" and not out["ok"]:
                out["error"]["code"] = "OTHER"
        else:
            kind = arguments.get("evidence_type")
            out = {**STAMP, "items": [], "total_matches": 0, "status": "no_records", "next_cursor": None, "offset": 0}
            if "experimental_property_id" in arguments and arguments["experimental_property_id"] != TARGET:
                out = {"ok": False, "error": {"code": "UNKNOWN_PROPERTY"}}
            elif kind == DIRECT:
                out.update(items=[comparison(DIRECT)["record"]], total_matches=1, property_resolutions={
                    "md_property_id": {"resolved_property_id": SOURCE},
                })
            elif kind == INDIRECT:
                rows = [comparison(INDIRECT)["record"] for _ in range(3)]
                rows[1]["evidence_id"] += ":2"
                rows[2]["evidence_id"] += ":3"
                if "cursor" in arguments or "filters" in arguments:
                    out.update(items=rows[2:], total_matches=3, offset=2)
                    if self.fault == "cursor_loop":
                        out["next_cursor"] = "next"
                else:
                    out.update(items=rows[:2], total_matches=3, next_cursor="next")
                if self.fault == "revision":
                    out["evidence_dataset_revision"] = "a" * 40
        if name == live.CATALOG:
            return SimpleNamespace(isError=False, structuredContent=None,
                                   content=[SimpleNamespace(type="text", text=json.dumps(out))])
        return SimpleNamespace(isError=False, structuredContent=out, content=[])


@pytest.fixture
def fake_live(monkeypatch, tmp_path):
    base = tmp_path / "baseline.json"
    base.write_text(json.dumps({"tools": dict.fromkeys(live.SEARCH, live.fingerprint({"type": "object"}))}))
    monkeypatch.setattr(live, "BASELINE", base)
    async def md(call, report, include_smarts):
        report["dataset_revision"] = "different-MD-revision"
    monkeypatch.setattr(live, "verify_md", md)
    return live


def test_fake_session_uses_all_evidence_tools_and_local_guard(fake_live):
    session, report = FakeSession(), {}
    asyncio.run(live.verify_session(session, report, False, "require"))
    assert report["evidence_status"] == "validated"
    assert set(session.calls) == live.EVIDENCE
    assert report["checks"]["L08_independent_validation"] == "not_provided"
    assert report["checks"]["L07_member_validation"]["members"] == 471
    with pytest.raises(live.CheckFailure, match="validator rejected"):
        asyncio.run(live.verify_session(FakeSession(fault="fit"), {}, False, "require"))


@pytest.mark.parametrize("available,mode,status,failed", [
    ([], "auto", "not_deployed", False),
    ([], "require", "not_deployed", True),
    ([live.CATALOG], "auto", "partial_deployment", True),
    ([live.CATALOG, live.DETAIL], "require", "partial_deployment", True),
    (live.EVIDENCE, "off", "off", False),
])
def test_discovery_modes(fake_live, available, mode, status, failed):
    report, session = {}, FakeSession(available)
    if failed:
        with pytest.raises(live.CheckFailure):
            asyncio.run(live.verify_session(session, report, False, mode))
    else:
        asyncio.run(live.verify_session(session, report, False, mode))
    assert report["evidence_status"] == status and not session.calls


def test_empty_catalog_checks_search_but_fails_release_gate(fake_live):
    session, report = FakeSession(fault="empty"), {}
    asyncio.run(live.verify_session(session, report, False, "auto"))
    assert report["evidence_status"] == "empty_catalog" and session.calls == [live.CATALOG, live.FIND]
    with pytest.raises(live.CheckFailure, match="no public records"):
        asyncio.run(live.verify_session(session, {}, False, "require"))


@pytest.mark.parametrize("fault,failure", [
    ("revision", live.CheckFailure), ("cursor_loop", live.CheckFailure),
    ("output_schema", jsonschema.ValidationError), ("wrong_error", live.CheckFailure),
])
def test_contract_errors_fail_release_gate(fake_live, fault, failure):
    with pytest.raises(failure):
        asyncio.run(live.verify_session(FakeSession(fault=fault), {}, False, "require"))


def test_cli_network_failure_is_redacted_and_nonzero(monkeypatch, tmp_path):
    destination = tmp_path / "receipt.json"
    async def offline(*args):
        raise httpx.ConnectError("private payload must never enter the report")
    monkeypatch.setattr(live, "verify", offline)
    monkeypatch.setattr(live.sys, "argv", ["check_live_mcp.py", "--evidence", "require", "--output", str(destination)])
    with pytest.raises(SystemExit) as exit_error:
        live.main()
    receipt = json.loads(destination.read_bytes())
    assert exit_error.value.code == 1 and receipt["evidence_status"] == "unreachable" and receipt["ok"] is False
    assert "private payload" not in destination.read_text()

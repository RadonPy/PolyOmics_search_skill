from io import BytesIO
import json
from zipfile import ZipFile, ZipInfo

import pytest
import yaml

from check_english_text import inspect_archive
from package_releases import AGENT_METADATA, PORTABLE_ZIP, ROOT, WORKSPACE_ZIP, build, workspace_manifest
from validate_package import ENDPOINT, validate_archives


# Synthetic identifier for temporary test archives only.
SYNTHETIC_APP_ID = "asdk_app_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


@pytest.fixture
def workspace_archive(tmp_path):
    build(tmp_path, profile="workspace", workspace_app_id=SYNTHETIC_APP_ID)
    return tmp_path / WORKSPACE_ZIP


def test_workspace_archive_is_reproducible_and_shares_the_portable_skill(workspace_archive):
    root = workspace_archive.parent
    second = root / "second"
    build(second, profile="workspace", workspace_app_id=SYNTHETIC_APP_ID)
    assert workspace_archive.read_bytes() == (second / WORKSPACE_ZIP).read_bytes()

    schema_dir = ROOT / ".cache" / "schemas"
    validate_archives(root, profile="workspace", workspace_app_id=SYNTHETIC_APP_ID,
                      schema_dir=schema_dir if schema_dir.is_dir() else None)
    assert not inspect_archive(workspace_archive.read_bytes(), workspace_archive.name)
    build(root)
    with ZipFile(workspace_archive) as web, ZipFile(root / PORTABLE_ZIP) as portable:
        assert set(web.namelist()) == (set(portable.namelist()) - {"mcp.json"}) | {".app.json"}
        assert json.loads(web.read(".app.json")) == {
            "apps": {"polyomics": {"id": SYNTHETIC_APP_ID, "required": True}},
        }
        assert json.loads(portable.read("mcp.json"))["mcpServers"] == {
            "polyomics": {"type": "streamable-http", "url": ENDPOINT},
        }
        web_manifest = json.loads(web.read("plugin.json"))
        assert web_manifest["extensions"]["com.openai"].pop("apps") == "./.app.json"
        assert web_manifest == json.loads(portable.read("plugin.json"))
        portable_agent = yaml.safe_load(portable.read(AGENT_METADATA))
        assert portable_agent["dependencies"]["tools"][0]["url"] == ENDPOINT
        assert yaml.safe_load(web.read(AGENT_METADATA)) == {"interface": portable_agent["interface"]}
        for name in set(web.namelist()) - {".app.json", "plugin.json", AGENT_METADATA}:
            assert web.read(name) == portable.read(name)


@pytest.mark.parametrize("invalid_id", [
    None, "", "polyomics-search", "plugin_asdk_app_abcd", "asdk_app_bad/id", "asdk_app_with a space",
    "asdk_app_EXAMPLE_REPLACE_AT_BUILD_TIME", "connector_placeholder", "asdk_app_00000000000",
])
def test_invalid_app_id_never_creates_an_archive(tmp_path, invalid_id):
    output = tmp_path / "workspace"
    with pytest.raises(ValueError, match="registered app ID"):
        build(output, profile="workspace", workspace_app_id=invalid_id)
    assert not output.exists()


def test_workspace_archive_cannot_be_written_to_public_dist():
    with pytest.raises(ValueError, match="workspace-specific output"):
        build(ROOT / "dist", profile="workspace", workspace_app_id=SYNTHETIC_APP_ID)


@pytest.mark.parametrize("extra", [
    "mcp.json", ".mcp.json", ".codex-plugin/plugin.json", "hooks/hooks.json",
    ".env", "private.csv", "../escape.md",
])
def test_workspace_rejects_extra_members(workspace_archive, extra):
    with ZipFile(workspace_archive, "a") as archive:
        archive.writestr(extra, "Synthetic unexpected content")
    with pytest.raises(ValueError, match="Unexpected or duplicate files"):
        validate_archives(workspace_archive.parent, profile="workspace", workspace_app_id=SYNTHETIC_APP_ID)


@pytest.mark.parametrize(("change", "message"), [
    ("missing", "Unexpected or duplicate files"),
    ("symlink", "Unsafe archive member"),
    ("wrong_icon", "Archive/source mismatch"),
])
def test_workspace_rejects_broken_manifest_references(workspace_archive, change, message):
    data = BytesIO(workspace_archive.read_bytes())
    with ZipFile(data) as source, ZipFile(workspace_archive, "w") as archive:
        for item in source.infolist():
            member = source.read(item)
            if item.filename == "assets/polyomics-square.png":
                if change == "missing":
                    continue
                if change == "symlink":
                    item = ZipInfo(item.filename)
                    item.create_system = 3
                    item.external_attr = 0o120777 << 16
            if item.filename == "plugin.json" and change == "wrong_icon":
                member = member.replace(b"./assets/polyomics-square.png", b"./missing.png")
            archive.writestr(item, member)
    with pytest.raises(ValueError, match=message):
        validate_archives(workspace_archive.parent, profile="workspace", workspace_app_id=SYNTHETIC_APP_ID)


def test_workspace_rejects_a_source_manifest_with_hooks():
    manifest = json.loads((ROOT / "plugin.json").read_bytes())
    manifest["extensions"]["com.openai"]["hooks"] = "./hooks/hooks.json"
    with pytest.raises(ValueError, match="binding or hook"):
        workspace_manifest(manifest)

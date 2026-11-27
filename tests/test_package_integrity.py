from hashlib import sha256
import json
from zipfile import ZipFile

import pytest
import yaml

import package_releases
from package_releases import ORIGINAL_ICON, PLUGIN_ICON, ROOT, archive_bytes, build, entries
from validate_package import DATABASE_DESCRIPTION, SKILL_DESCRIPTION, SUBTITLE, validate_archives, validate_icons, validate_metadata, validate_source


def test_source_and_linked_metadata():
    validate_source()


def test_reproducible_archives(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    for directory in (first, second):
        build(directory)
        validate_archives(directory)
    for name in entries():
        assert (first / name).read_bytes() == (second / name).read_bytes()
        with ZipFile(first / name) as archive:
            assert not any("fixture" in member or ".app.json" in member for member in archive.namelist())


def test_plugin_archive_retains_supplied_png_and_links_the_padded_icon(tmp_path):
    build(tmp_path)
    with ZipFile(tmp_path / "polyomics-search-plugin.zip") as archive:
        interface = json.loads(archive.read("plugin.json"))["extensions"]["com.openai"]["interface"]
        assert interface["logo"] == interface["composerIcon"] == f"./{PLUGIN_ICON}"
        original = archive.read(ORIGINAL_ICON)
        assert sha256(original).hexdigest() == "6ab5b071d69bb646adfe1c6e833b09acff967fcef52dc2162759b3e471c5efe2"
        validate_icons(original, archive.read(PLUGIN_ICON))
    with ZipFile(tmp_path / "skill.zip") as archive:
        assert not any(name.endswith(".png") for name in archive.namelist())


def test_standalone_and_portable_archives_expose_database_identity(tmp_path):
    build(tmp_path)
    with ZipFile(tmp_path / "skill.zip") as skill, ZipFile(tmp_path / "polyomics-search-plugin.zip") as plugin:
        manifest = json.loads(plugin.read("plugin.json"))
        interface = manifest["extensions"]["com.openai"]["interface"]
        assert interface["shortDescription"] == SUBTITLE and len(SUBTITLE) == 30
        assert manifest["description"].startswith(DATABASE_DESCRIPTION)
        assert interface["longDescription"].startswith(DATABASE_DESCRIPTION)
        prompts = interface["defaultPrompt"]
        assert len(prompts) == len(set(prompts)) == 3 and all(0 < len(prompt) <= 128 for prompt in prompts)
        agent_path = "polyomics-search/agents/openai.yaml"
        skill_path = "polyomics-search/SKILL.md"
        for path in (agent_path, skill_path):
            assert skill.read(path) == plugin.read(f"skills/{path}")
        agent = yaml.safe_load(skill.read(agent_path))
        assert agent["interface"]["short_description"] == SUBTITLE
        assert yaml.safe_load(skill.read(skill_path).decode().split("---", 2)[1])["description"].startswith(SKILL_DESCRIPTION)


@pytest.mark.parametrize(("issue", "message"), [
    ("historical", "Plugin subtitle must identify"),
    ("overlong", "Plugin subtitle must be 1 to 30"),
    ("agent", "Agent/plugin subtitles disagree"),
    ("root", "Plugin description lacks"),
    ("long", "Plugin description lacks"),
    ("skill", "Skill description lacks"),
])
def test_metadata_validator_rejects_stale_or_missing_copy(issue, message):
    skill = ROOT / "skills" / "polyomics-search"
    content = (skill / "SKILL.md").read_bytes()
    agent = yaml.safe_load((skill / "agents" / "openai.yaml").read_bytes())
    manifest = json.loads((ROOT / "plugin.json").read_bytes())
    interface = manifest["extensions"]["com.openai"]["interface"]
    if issue == "historical":
        interface["shortDescription"] = "Search polymer simulations"
    elif issue == "overlong":
        interface["shortDescription"] = SUBTITLE + "."
    elif issue == "agent":
        agent["interface"]["short_description"] = "Simulated polymer properties"
    elif issue == "root":
        manifest["description"] = "Search polymers."
    elif issue == "long":
        interface["longDescription"] = "Search polymers."
    else:
        content = b"---\nname: polyomics-search\ndescription: Search polymers.\n---\n"
    with pytest.raises(ValueError, match=message):
        validate_metadata(content, agent, manifest)


def test_packaged_license_uses_canonical_line_endings(tmp_path, monkeypatch):
    monkeypatch.setattr(package_releases, "ROOT", tmp_path)
    license_file = tmp_path / "LICENSE"
    for newline in (b"\n", b"\r\n"):
        license_file.write_bytes(newline.join((b"line 1", b"line 2", b"")))
        assert archive_bytes(license_file) == b"line 1\nline 2\n"


def test_extra_archive_member_is_rejected(tmp_path):
    build(tmp_path)
    with ZipFile(tmp_path / "polyomics-search-plugin.zip", "a") as archive:
        archive.writestr(".env", "test-only invalid member")
    with pytest.raises(ValueError, match="Unexpected or duplicate files"):
        validate_archives(tmp_path)

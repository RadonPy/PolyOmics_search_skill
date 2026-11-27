"""Validate source metadata and every archived member against the allowlist."""

import argparse
from io import BytesIO
import json
import re
import stat
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from zipfile import ZipFile

import jsonschema
from PIL import Image, ImageOps
import yaml

from package_releases import (
    AGENT_METADATA, ORIGINAL_ICON, PLUGIN_FIELDS, PLUGIN_ICON, PORTABLE_ZIP, ROOT, SKILL, WORKSPACE_ZIP,
    add_profile_args, entries, expected_bytes, package_payloads, profile_options, workspace_binding,
)


SCHEMA_BASE = "https://agent-plugins.org/schemas/1.0.0/"
ENDPOINT = "https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/"
SUBTITLE = "Polymer property database (MD)"
DATABASE_DESCRIPTION = "Search PolyOmics, a large-scale computational polymer property database"
SKILL_DESCRIPTION = "Search and reason with PolyOmics, a large-scale public database of polymer properties"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def yaml_object(value):
    parsed = yaml.safe_load(value)
    require(isinstance(parsed, dict), "Expected a YAML object")
    return parsed


def validate_icons(original, packaged):
    require(len(packaged) <= 5 * 1024 * 1024, "Plugin icon exceeds 5 MiB")
    with Image.open(BytesIO(original)) as source, Image.open(BytesIO(packaged)) as icon:
        require(source.format == icon.format == "PNG", "Expected PNG icons")
        require(icon.width == icon.height and 48 <= icon.width <= 4096, "Expected a square plugin icon")
        require(icon.mode == "RGBA", "Plugin icon must retain transparency")
        source = source.convert("RGBA")
        horizontal, vertical = icon.width - source.width, icon.height - source.height
        require(min(horizontal, vertical) == 0, "Plugin icon must fit the original without rescaling")
        padded = ImageOps.expand(
            source, (horizontal // 2, vertical // 2, (horizontal + 1) // 2, (vertical + 1) // 2),
            fill=(0, 0, 0, 0),
        )
        require(icon.tobytes() == padded.tobytes(), "Plugin icon differs beyond transparent padding")


def validate_metadata(skill_bytes, agent, manifest=None):
    content = skill_bytes.decode("utf-8").replace("\r\n", "\n")
    require(content.startswith("---\n") and "\n---\n" in content[4:], "Missing Skill frontmatter")
    header, _ = content[4:].split("\n---\n", 1)
    frontmatter = yaml_object(header)
    description = frontmatter.get("description")
    require(frontmatter.get("name") == SKILL and isinstance(description, str)
            and 0 < len(description.strip()) <= 1024, "Invalid Skill name/description")
    require(description.startswith(SKILL_DESCRIPTION), "Skill description lacks the PolyOmics database definition")
    agent_interface = agent["interface"]
    if manifest is not None:
        interface = manifest["extensions"]["com.openai"]["interface"]
        subtitle = interface.get("shortDescription")
        require(isinstance(subtitle, str) and 0 < len(subtitle) <= 30, "Plugin subtitle must be 1 to 30 characters")
        require(subtitle == SUBTITLE, "Plugin subtitle must identify the PolyOmics database")
        require(agent_interface.get("short_description") == subtitle, "Agent/plugin subtitles disagree")
        require(agent_interface.get("display_name") == interface.get("displayName"), "Agent/plugin display names disagree")
        for description in (manifest.get("description"), interface.get("longDescription")):
            require(isinstance(description, str) and description.startswith(DATABASE_DESCRIPTION),
                    "Plugin description lacks the PolyOmics database definition")
    require(agent_interface.get("short_description") == SUBTITLE, "Agent subtitle must identify the PolyOmics database")


def validate_source(schema_dir=None):
    skill = ROOT / "skills" / SKILL
    manifest = json.loads(expected_bytes(ROOT / "plugin.json"))
    mcp = json.loads(expected_bytes(ROOT / "mcp.json"))
    for name, data in (("plugin", manifest), ("mcp", mcp)):
        require(data["$schema"] == f"{SCHEMA_BASE}{name}.schema.json", f"Wrong {name} schema URI")
        if schema_dir is not None:
            jsonschema.validate(data, json.loads((schema_dir / f"{name}.schema.json").read_text(encoding="utf-8")))
    require(manifest["name"] == SKILL and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", manifest["version"]), "Wrong plugin identity")
    require(manifest.keys() <= PLUGIN_FIELDS and set(manifest["extensions"]) == {"com.openai"},
            "Unexpected plugin fields or extensions")
    openai = manifest["extensions"]["com.openai"]
    require(set(openai) == {"interface"}, "Unexpected OpenAI plugin binding")
    interface = openai["interface"]
    require(interface["category"] == "Scientific Research", "Invalid category for this package")
    require(interface.get("capabilities") == ["Read"], "Expected read-only listing capability")
    for key in ("logo", "composerIcon"):
        require(interface[key] == f"./{PLUGIN_ICON}" and PLUGIN_ICON in entries()[PORTABLE_ZIP],
                f"Invalid packaged {key}")
    validate_icons(expected_bytes(ROOT / ORIGINAL_ICON), expected_bytes(ROOT / PLUGIN_ICON))
    require(set(mcp) == {"$schema", "mcpServers"} and set(mcp["mcpServers"]) == {"polyomics"},
            "Expected one PolyOmics connection")
    server = mcp["mcpServers"]["polyomics"]
    endpoint = urlsplit(server["url"])
    require(endpoint.scheme == "https" and endpoint.hostname and not any((endpoint.username, endpoint.password, endpoint.query, endpoint.fragment)), "Expected clean HTTPS endpoint")
    require(server["url"] == ENDPOINT, "Expected the production PolyOmics endpoint")
    require(server["type"] == "streamable-http" and set(server) == {"type", "url"}, "Expected anonymous portable MCP transport")
    agent = yaml_object(expected_bytes(skill / "agents" / "openai.yaml"))
    validate_metadata(expected_bytes(skill / "SKILL.md"), agent, manifest)
    dependency, = agent["dependencies"]["tools"]
    require(dependency["type"] == "mcp" and dependency["value"] == "polyomics" and dependency["transport"] == "streamable_http" and dependency["url"] == server["url"], "Agent connection and manifest disagree")
    skill_files = set(entries()["skill.zip"].values())
    for source in skill_files:
        if source.suffix != ".md":
            continue
        for relative in re.findall(r"\]\(([^ )]+)\)", expected_bytes(source).decode("utf-8")):
            target = (source.parent / relative.split("#", 1)[0]).resolve()
            require(target in skill_files, f"Missing or unbundled Skill reference: {relative}")


def validate_archives(directory=ROOT / "dist", *, profile="portable", workspace_app_id=None, schema_dir=None):
    for archive_name, sources in package_payloads(profile, workspace_app_id).items():
        with ZipFile(directory / archive_name) as archive:
            names = archive.namelist()
            require(names == sorted(sources), f"Unexpected or duplicate files in {archive_name}")
            require(archive.testzip() is None, f"Corrupt member in {archive_name}")
            for info in archive.infolist():
                name = info.filename
                parts = PurePosixPath(name).parts
                require(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16)
                        and not name.startswith("/") and ".." not in parts and "\\" not in name, f"Unsafe archive member: {name}")
                require(archive.read(name) == sources[name], f"Archive/source mismatch: {name}")
            is_plugin = archive_name in (PORTABLE_ZIP, WORKSPACE_ZIP)
            manifest = json.loads(archive.read("plugin.json")) if is_plugin else None
            skill_root = f"skills/{SKILL}" if is_plugin else SKILL
            agent_path = AGENT_METADATA if is_plugin else AGENT_METADATA.removeprefix("skills/")
            agent = yaml_object(archive.read(agent_path))
            validate_metadata(archive.read(f"{skill_root}/SKILL.md"), agent, manifest)
            if archive_name == WORKSPACE_ZIP:
                if schema_dir is not None:
                    schema = json.loads((schema_dir / "plugin.schema.json").read_bytes())
                    jsonschema.validate(manifest, schema)
                extension = manifest["extensions"]["com.openai"]
                require(set(extension) == {"interface", "apps"} and extension["apps"] == "./.app.json", "Invalid registered app path")
                require(json.loads(archive.read(".app.json")) == workspace_binding(workspace_app_id), "Invalid required app binding")
                require(set(agent) == {"interface"}, "Workspace skill has a runtime dependency")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--schema-dir", type=Path, help="Directory with the official Agent Plugins 1.0 schemas")
    add_profile_args(cli)
    args = cli.parse_args()
    directory, app_id = profile_options(args)
    try:
        validate_source(args.schema_dir)
        validate_archives(directory, profile=args.profile, workspace_app_id=app_id, schema_dir=args.schema_dir)
    except ValueError as error:
        cli.error(str(error))
    print(f"Source and {args.profile} ZIP artifacts are valid.")

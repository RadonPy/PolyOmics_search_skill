"""Validate source metadata and every archived member against the allowlist."""

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from zipfile import ZipFile

import jsonschema
import yaml

from package_releases import ROOT, SKILL, entries, expected_bytes


SCHEMA_BASE = "https://agent-plugins.org/schemas/1.0.0/"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def yaml_object(value):
    parsed = yaml.safe_load(value)
    require(isinstance(parsed, dict), "Expected a YAML object")
    return parsed


def validate_source(schema_dir=None):
    skill = ROOT / "skills" / SKILL
    manifest = json.loads(expected_bytes(ROOT / "plugin.json"))
    mcp = json.loads(expected_bytes(ROOT / "mcp.json"))
    for name, data in (("plugin", manifest), ("mcp", mcp)):
        require(data["$schema"] == f"{SCHEMA_BASE}{name}.schema.json", f"Wrong {name} schema URI")
        if schema_dir is not None:
            jsonschema.validate(data, json.loads((schema_dir / f"{name}.schema.json").read_text(encoding="utf-8")))
    require(manifest["name"] == SKILL and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", manifest["version"]), "Wrong plugin identity")
    require(not {"interface", "skills", "mcpServers", "apps"} & manifest.keys(), "Legacy root fields")
    openai = manifest["extensions"]["com.openai"]
    require(set(openai) == {"interface"}, "Unexpected OpenAI plugin binding")
    interface = openai["interface"]
    require(0 < len(interface["shortDescription"]) <= 30, "Plugin subtitle is too long")
    require(interface["category"] == "Scientific Research", "Invalid category for this package")
    for key in ("logo", "composerIcon"):
        icon = interface[key].removeprefix("./")
        require(icon in entries()["polyomics-search-plugin.zip"], f"Missing archived {key}")
    require(set(mcp["mcpServers"]) == {"polyomics"}, "Expected one PolyOmics connection")
    server = mcp["mcpServers"]["polyomics"]
    endpoint = urlsplit(server["url"])
    require(endpoint.scheme == "https" and endpoint.hostname and not any((endpoint.username, endpoint.password, endpoint.query, endpoint.fragment)), "Expected clean HTTPS endpoint")
    require(server["type"] == "streamable-http" and set(server) == {"type", "url"}, "Expected anonymous portable MCP transport")
    content = expected_bytes(skill / "SKILL.md").decode("utf-8")
    require(content.startswith("---\n") and "\n---\n" in content[4:], "Missing Skill frontmatter")
    header, _ = content[4:].split("\n---\n", 1)
    frontmatter = yaml_object(header)
    require(frontmatter["name"] == SKILL and 0 < len(frontmatter["description"].strip()) <= 1024, "Invalid Skill name/description")
    agent = yaml_object(expected_bytes(skill / "agents" / "openai.yaml"))
    require(agent["interface"]["display_name"] == interface["displayName"], "Agent/plugin display names disagree")
    dependency, = agent["dependencies"]["tools"]
    require(dependency["type"] == "mcp" and dependency["value"] == "polyomics" and dependency["transport"] == "streamable_http" and dependency["url"] == server["url"], "Agent connection and manifest disagree")
    skill_files = set(entries()["skill.zip"].values())
    for source in skill_files:
        if source.suffix != ".md":
            continue
        for relative in re.findall(r"\]\(([^ )]+)\)", expected_bytes(source).decode("utf-8")):
            target = (source.parent / relative.split("#", 1)[0]).resolve()
            require(target in skill_files, f"Missing or unbundled Skill reference: {relative}")


def validate_archives(directory=ROOT / "dist"):
    for archive_name, sources in entries().items():
        with ZipFile(directory / archive_name) as archive:
            names = archive.namelist()
            require(names == sorted(sources), f"Unexpected or duplicate files in {archive_name}")
            require(archive.testzip() is None, f"Corrupt member in {archive_name}")
            for info in archive.infolist():
                name = info.filename
                parts = PurePosixPath(name).parts
                require(not info.is_dir() and not name.startswith("/") and ".." not in parts and "\\" not in name, f"Unsafe archive member: {name}")
                require(archive.read(name) == expected_bytes(sources[name]), f"Archive/source mismatch: {name}")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--schema-dir", type=Path, help="Directory with the official Agent Plugins 1.0 schemas")
    args = cli.parse_args()
    validate_source(args.schema_dir)
    validate_archives()
    print("Source and both ZIP archives are valid.")

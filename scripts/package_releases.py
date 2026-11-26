"""Build reproducible portable or registered-app workspace ZIPs."""

import argparse
import json
import os
from pathlib import Path
import re
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = "polyomics-search"
SKILL_FILES = {
    "SKILL.md", "agents/openai.yaml", "references/mcp-workflows.md",
    "references/evidence-interpretation.md", "references/output-rules.md",
    "references/example-prompts.md", "scripts/check_evidence.py",
}
ORIGINAL_ICON = "assets/polyomics.png"
PLUGIN_ICON = "assets/polyomics-square.png"
PLUGIN_FILES = {"plugin.json", "mcp.json", ORIGINAL_ICON, PLUGIN_ICON, "LICENSE"}
PLUGIN_FIELDS = {"$schema", "name", "version", "description", "repository", "homepage", "license", "keywords", "extensions"}
PORTABLE_ZIP = "polyomics-search-plugin.zip"
WORKSPACE_ZIP = "polyomics-search-web-plugin.zip"
WORKSPACE_DIR = ROOT / ".local" / "dist"
AGENT_METADATA = f"skills/{SKILL}/agents/openai.yaml"


def entries():
    skill = {f"{SKILL}/{path}": ROOT / "skills" / SKILL / path for path in SKILL_FILES}
    plugin = {f"skills/{name}": source for name, source in skill.items()}
    plugin.update({name: ROOT / name for name in PLUGIN_FILES})
    skill[f"{SKILL}/LICENSE"] = ROOT / "LICENSE"
    return {"skill.zip": skill, PORTABLE_ZIP: plugin}


def expected_bytes(path):
    relative = path.relative_to(ROOT)
    lineage = (ROOT / Path(*relative.parts[:length]) for length in range(1, len(relative.parts) + 1))
    if not path.is_file() or not path.resolve().is_relative_to(ROOT) or any(
        item.is_symlink() or item.is_junction() for item in lineage
    ):
        raise ValueError(f"Release file is missing or outside the source tree: {path.name}")
    return path.read_bytes()


def archive_bytes(path):
    data = expected_bytes(path)
    if path.name == "LICENSE" or path.suffix in {".json", ".md", ".py", ".yaml"}:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def checked_app_id(value):
    match = re.fullmatch(r"(?:asdk_app|connector|templated_apps)_([A-Za-z0-9][A-Za-z0-9_-]*)", value or "")
    if not match or len(value) > 200:
        raise ValueError("Supply a registered app ID with --workspace-app-id or POLYOMICS_WORKSPACE_APP_ID.")
    suffix = match[1].lower()
    if any(word in suffix for word in ("example", "placeholder", "replace", "your_app", "test_only")) or set(suffix) == {"0"}:
        raise ValueError("Use the actual registered app ID, not a placeholder.")
    return value


def workspace_binding(app_id):
    return {"apps": {"polyomics": {"id": checked_app_id(app_id), "required": True}}}


def workspace_manifest(manifest):
    extension = manifest["extensions"]["com.openai"]
    if manifest.keys() - PLUGIN_FIELDS or set(manifest["extensions"]) != {"com.openai"} or set(extension) != {"interface"}:
        raise ValueError("Unexpected source plugin binding or hook.")
    extension["apps"] = "./.app.json"
    return manifest


def workspace_agent(metadata):
    return {"interface": metadata["interface"]}


def package_payloads(profile="portable", workspace_app_id=None):
    sources = entries()
    if profile == "portable" and workspace_app_id is None:
        return {name: {member: archive_bytes(path) for member, path in files.items()} for name, files in sources.items()}
    if profile != "workspace":
        raise ValueError("Only the workspace profile accepts a registered app ID.")
    binding = workspace_binding(workspace_app_id)
    files = {member: archive_bytes(path) for member, path in sources[PORTABLE_ZIP].items() if member != "mcp.json"}
    manifest = workspace_manifest(json.loads(files["plugin.json"]))
    files["plugin.json"] = json_bytes(manifest)
    files[".app.json"] = json_bytes(binding)
    metadata = workspace_agent(yaml.safe_load(files[AGENT_METADATA]))
    files[AGENT_METADATA] = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).encode("utf-8")
    return {WORKSPACE_ZIP: files}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build(directory=None, *, profile="portable", workspace_app_id=None):
    directory = directory or (WORKSPACE_DIR if profile == "workspace" else ROOT / "dist")
    if profile == "workspace":
        target = directory.resolve()
        if target.is_relative_to(ROOT) and not target.is_relative_to(ROOT / ".local"):
            raise ValueError("Keep workspace-specific output under .local/ or outside the repository.")
    payloads = package_payloads(profile, workspace_app_id)
    directory.mkdir(parents=True, exist_ok=True)
    for archive_name, sources in payloads.items():
        destination = directory / archive_name
        if destination.is_symlink():
            raise ValueError("Archive output must not be a symlink.")
        with ZipFile(destination, "w") as archive:
            for name, data in sorted(sources.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = ZIP_STORED
                archive.writestr(info, data)


def add_profile_args(cli):
    cli.add_argument("--profile", choices=("portable", "workspace"), default="portable")
    cli.add_argument("--workspace-app-id", help="Registered app ID; defaults to POLYOMICS_WORKSPACE_APP_ID for workspace builds.")
    cli.add_argument("--output-dir", type=Path)


def profile_options(args):
    app_id = args.workspace_app_id
    if args.profile == "workspace" and app_id is None:
        app_id = os.environ.get("POLYOMICS_WORKSPACE_APP_ID")
    directory = args.output_dir or (WORKSPACE_DIR if args.profile == "workspace" else ROOT / "dist")
    return directory, app_id


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    add_profile_args(cli)
    args = cli.parse_args()
    directory, app_id = profile_options(args)
    try:
        build(directory, profile=args.profile, workspace_app_id=app_id)
    except ValueError as error:
        cli.error(str(error))

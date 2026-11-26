"""Build reproducible, allowlisted release ZIPs from the source tree."""

from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


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


def entries():
    skill = {f"{SKILL}/{path}": ROOT / "skills" / SKILL / path for path in SKILL_FILES}
    plugin = {f"skills/{name}": source for name, source in skill.items()}
    plugin.update({name: ROOT / name for name in PLUGIN_FILES})
    skill[f"{SKILL}/LICENSE"] = ROOT / "LICENSE"
    return {"skill.zip": skill, "polyomics-search-plugin.zip": plugin}


def expected_bytes(path):
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise ValueError(f"Release file is missing or outside the source tree: {path.name}")
    return path.read_bytes()


def archive_bytes(path):
    data = expected_bytes(path)
    if path.name == "LICENSE" or path.suffix in {".json", ".md", ".py", ".yaml"}:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def build(directory=ROOT / "dist"):
    directory.mkdir(parents=True, exist_ok=True)
    for archive_name, sources in entries().items():
        with ZipFile(directory / archive_name, "w") as archive:
            for name, path in sorted(sources.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = ZIP_STORED
                archive.writestr(info, archive_bytes(path))


if __name__ == "__main__":
    build()

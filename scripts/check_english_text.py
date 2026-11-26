"""Check authored text, structured strings, archive text, and local Markdown links."""

import argparse
from io import BytesIO
import json
from pathlib import Path
from posixpath import dirname, join, normpath
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

import yaml

from package_releases import ROOT

TEXT_SUFFIXES = {
    ".cfg", ".css", ".csv", ".html", ".ini", ".js", ".json", ".jsonl", ".md", ".py",
    ".ps1", ".rst", ".sh", ".svg", ".toml", ".ts", ".txt", ".xml", ".yaml", ".yml",
}
LINKS = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^)\s]+)(?:\s+\"[^\"\n]*\")?\)")


def japanese_script(value):
    return any(unicodedata.name(char, "").startswith((
        "HIRAGANA", "KATAKANA", "HALFWIDTH KATAKANA", "CJK UNIFIED IDEOGRAPH",
        "CJK COMPATIBILITY IDEOGRAPH", "CJK RADICAL", "KANGXI RADICAL",
    )) or char in "\u3005\u3006\u3007\u30fc\uff70" for char in value)


def structured_strings(value, field="$", active=None):
    if isinstance(value, str):
        yield field, value
    elif isinstance(value, (dict, list)):
        active = set() if active is None else active
        if id(value) in active:
            raise ValueError("Recursive structured value")
        active.add(id(value))
        if isinstance(value, dict):
            for number, (key, child) in enumerate(value.items(), 1):
                if isinstance(key, str):
                    yield f"{field} key {number}", key
                label = key if isinstance(key, str) and re.fullmatch(r"[\w.-]{1,100}", key) and not japanese_script(key) else number
                yield from structured_strings(child, f"{field}.{label}", active)
        else:
            for index, child in enumerate(value):
                yield from structured_strings(child, f"{field}[{index}]", active)
        active.remove(id(value))


def inspect_text(data, name):
    suffix = Path(name).suffix.lower()
    leaf = Path(name).name
    if suffix not in TEXT_SUFFIXES and suffix and leaf not in {".gitignore", ".gitattributes", ".editorconfig"}:
        return []
    if not suffix and b"\0" in data:
        return []
    try:
        source = data.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return [f"{name}: expected UTF-8 text"] if suffix in TEXT_SUFFIXES else []
    hits = [f"{name}:{line}: Japanese-script text" for line, value in enumerate(source.splitlines(), 1) if japanese_script(value)]
    try:
        if suffix in {".json", ".jsonl"}:
            objects = [json.loads(source)] if suffix == ".json" else [json.loads(line) for line in source.splitlines() if line.strip()]
        elif suffix in {".yaml", ".yml"}:
            objects = list(yaml.safe_load_all(source))
        elif suffix == ".md" and source.startswith("---\n"):
            objects = [yaml.safe_load(source.split("\n---\n", 1)[0][4:])]
        else:
            objects = []
        hits.extend(f"{name}:{field}: Japanese-script value" for value in objects
                    for field, string in structured_strings(value) if japanese_script(string))
    except (ValueError, RecursionError, yaml.YAMLError):
        hits.append(f"{name}: could not inspect structured text")
    return hits


def markdown_links(data):
    source = data.decode("utf-8-sig")
    fenced = None
    for number, line in enumerate(source.splitlines(), 1):
        marker = re.match(r"^\s*([\x60~]{3,})", line)
        if marker:
            edge = marker[1]
            if fenced is None:
                fenced = edge
            elif edge[0] == fenced[0] and len(edge) >= len(fenced):
                fenced = None
            continue
        if fenced is not None:
            continue
        for match in LINKS.finditer(line):
            parsed = urlsplit(match[1].strip("<>"))
            if not parsed.scheme and not parsed.netloc and parsed.path:
                yield number, unquote(parsed.path)


def inspect_archive(data, name):
    findings = []
    with ZipFile(BytesIO(data)) as archive:
        names = set(archive.namelist())
        for item in archive.infolist():
            if item.is_dir():
                continue
            path = item.filename
            address = f"{name}!/{path}"
            member = archive.read(item)
            findings.extend(inspect_text(member, address))
            if path.endswith(".md"):
                for number, target in markdown_links(member):
                    if normpath(join(dirname(path), target)) not in names:
                        findings.append(f"{address}:{number}: missing local link target {target}")
    return findings


def repository_files():
    output = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    return sorted(set(output.decode("utf-8").split("\0")) - {""})


def inspect_repository():
    findings = []
    for name in repository_files():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            findings.append(f"{name}: expected a repository file")
            continue
        data = path.read_bytes()
        if path.suffix == ".zip":
            findings.extend(inspect_archive(data, name))
            continue
        findings.extend(inspect_text(data, name))
        if path.suffix == ".md":
            for number, target in markdown_links(data):
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(ROOT) or not resolved.exists():
                    findings.append(f"{name}:{number}: missing or external local link target {target}")
    return findings


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--archive", type=Path, action="append", default=[], help="Also check a locally built workspace ZIP.")
    args = cli.parse_args()
    findings = inspect_repository()
    for archive in args.archive:
        findings.extend(inspect_archive(archive.read_bytes(), archive.name))
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("English text, archive text, and relative Markdown links passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

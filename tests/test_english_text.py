from io import BytesIO
from zipfile import ZipFile

import pytest

from check_english_text import inspect_archive, inspect_text, markdown_links


@pytest.mark.parametrize("character", [0x3042, 0x30AB, 0xFF76, 0x5B9F, 0x20000])
def test_detects_japanese_script_in_extensionless_text(character):
    assert inspect_text(chr(character).encode(), "README") == ["README:1: Japanese-script text"]


@pytest.mark.parametrize(("name", "data"), [
    ("listing.json", b'{"listing": ["\\u30ab"]}'),
    ("agent.yaml", b'listing: ["\\u30ab"]\n'),
    ("SKILL.md", b'---\r\nlisting: ["\\u30ab"]\r\n---\r\n\r\nBody\r\n'),
])
def test_decodes_structured_text_escapes(name, data):
    assert inspect_text(data, name) == [f"{name}:$.listing[0]: Japanese-script value"]


def test_scientific_unicode_and_binary_assets_pass():
    assert not inspect_text("R², µm, °C, ρ and ±".encode(), "report.md")
    assert not inspect_text(b"\x89PNG\0binary", "icon.png")


def test_scans_archive_text_and_local_links():
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("skill/SKILL.md", "[Reference](references/example.md)\n[Missing](missing.md)\n")
        archive.writestr("skill/references/example.md", chr(0x3042))
    assert inspect_archive(data.getvalue(), "release.zip") == [
        "release.zip!/skill/SKILL.md:2: missing local link target missing.md",
        "release.zip!/skill/references/example.md:1: Japanese-script text",
    ]


def test_ignores_fenced_examples_and_extracts_urlencoded_paths():
    data = b"~~~sh\n[Example](missing.md)\n~~~\n[File](file%20name.md#section)\n[External](https://example.com)\n"
    assert list(markdown_links(data)) == [(4, "file name.md")]

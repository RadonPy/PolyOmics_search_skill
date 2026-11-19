from zipfile import ZipFile

import pytest

from package_releases import build, entries
from validate_package import validate_archives, validate_source


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


def test_extra_archive_member_is_rejected(tmp_path):
    build(tmp_path)
    with ZipFile(tmp_path / "polyomics-search-plugin.zip", "a") as archive:
        archive.writestr(".env", "test-only invalid member")
    with pytest.raises(ValueError, match="Unexpected or duplicate files"):
        validate_archives(tmp_path)

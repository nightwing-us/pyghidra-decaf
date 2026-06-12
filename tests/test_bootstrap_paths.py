"""Unit tests for bootstrap path resolution (no JVM required)."""

# Standard Libraries
from pathlib import Path
from unittest.mock import patch

# Our Libraries
from pyghidra_decaf.bootstrap import (
    _parse_reported_paths,
    _resolve_extensions_dir,
)


class TestParseReportedPaths:
    def test_extracts_ext_path_and_version(self) -> None:
        stdout = (
            'noise\n'
            '__DECAF_EXT_PATH__=/opt/test/.config/ghidra/x/Extensions\n'
            '__DECAF_VERSION__=12.0.4\n'
            'more noise\n'
        )
        result = _parse_reported_paths(stdout)
        assert result['ext_path'] == '/opt/test/.config/ghidra/x/Extensions'
        assert result['version'] == '12.0.4'

    def test_last_occurrence_wins(self) -> None:
        stdout = '__DECAF_EXT_PATH__=/a\n__DECAF_EXT_PATH__=/b\n'
        assert _parse_reported_paths(stdout)['ext_path'] == '/b'

    def test_absent_sentinels_yield_empty(self) -> None:
        assert _parse_reported_paths('nothing here\n') == {}


class TestResolveExtensionsDir:
    def test_prefers_reported_path(self) -> None:
        reported = {'ext_path': '/reported/Extensions'}
        with patch(
            'pyghidra_decaf.bootstrap.find_ghidra_extensions_dir',
            return_value=Path('/heuristic/Extensions'),
        ):
            assert _resolve_extensions_dir(reported) == Path('/reported/Extensions')

    def test_falls_back_to_heuristic_when_no_sentinel(self) -> None:
        with patch(
            'pyghidra_decaf.bootstrap.find_ghidra_extensions_dir',
            return_value=Path('/heuristic/Extensions'),
        ):
            assert _resolve_extensions_dir({}) == Path('/heuristic/Extensions')

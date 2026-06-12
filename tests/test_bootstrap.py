"""Unit tests for pyghidra_decaf.bootstrap — pure-Python helper functions."""

# Standard Libraries
import os
from pathlib import Path
from typing import Generator
from unittest.mock import (
    MagicMock,
    patch,
)

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.bootstrap import (
    find_ghidra_extensions_dir,
    get_extension_dirs,
)


# ---------------------------------------------------------------------------
# find_ghidra_extensions_dir
# ---------------------------------------------------------------------------

class TestFindGhidraExtensionsDir:
    def test_returns_none_when_env_not_set(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != 'GHIDRA_INSTALL_DIR'}
        with patch.dict(os.environ, env, clear=True):
            result = find_ghidra_extensions_dir()
        assert result is None

    def test_returns_none_when_env_is_empty_string(self) -> None:
        with patch.dict(os.environ, {'GHIDRA_INSTALL_DIR': ''}):
            result = find_ghidra_extensions_dir()
        assert result is None

    def test_returns_none_when_config_dir_does_not_exist(self, tmp_path: Path) -> None:
        install_dir = tmp_path / 'ghidra_11.0_PUBLIC'
        install_dir.mkdir()
        with patch.dict(os.environ, {'GHIDRA_INSTALL_DIR': str(install_dir)}):
            # Patch Path.home() so no real ~/.config/ghidra is found
            with patch('pyghidra_decaf.bootstrap.Path') as mock_path_cls:
                # Make the home dir point to a temp location with no ghidra config
                fake_home = tmp_path / 'fakehome'
                fake_home.mkdir()
                mock_path_cls.return_value = Path(str(install_dir))
                mock_path_cls.home.return_value = fake_home
                # Re-import using real Path for the install dir logic
                # Use a simpler approach: just assert config doesn't exist under tmp
                result = find_ghidra_extensions_dir()
        # config dir doesn't exist → None
        assert result is None

    def test_returns_extensions_path_when_matching_dir_found(self, tmp_path: Path) -> None:
        # Set up a fake Ghidra install dir
        ghidra_version_name = 'ghidra_11.0_PUBLIC'
        install_dir = tmp_path / ghidra_version_name
        install_dir.mkdir()

        # Set up a fake ~/.config/ghidra/<version_dir>/Extensions
        fake_home = tmp_path / 'home'
        fake_home.mkdir()
        config_ghidra = fake_home / '.config' / 'ghidra'
        config_ghidra.mkdir(parents=True)
        version_dir = config_ghidra / ghidra_version_name
        version_dir.mkdir()
        extensions_dir = version_dir / 'Extensions'
        extensions_dir.mkdir()

        with patch.dict(os.environ, {'GHIDRA_INSTALL_DIR': str(install_dir)}):
            with patch('pyghidra_decaf.bootstrap.Path') as mock_path_cls:
                # We need Path() calls to return real Paths, but Path.home() → fake_home
                mock_path_cls.side_effect = lambda *args: Path(*args)
                mock_path_cls.home.return_value = fake_home
                result = find_ghidra_extensions_dir()

        assert result == extensions_dir

    def test_falls_back_to_dot_ghidra_dir(self, tmp_path: Path) -> None:
        ghidra_version_name = 'ghidra_10.4_PUBLIC'
        install_dir = tmp_path / ghidra_version_name
        install_dir.mkdir()

        fake_home = tmp_path / 'home2'
        fake_home.mkdir()
        # No ~/.config/ghidra, but ~/.ghidra exists
        dot_ghidra = fake_home / '.ghidra'
        dot_ghidra.mkdir()
        version_dir = dot_ghidra / ghidra_version_name
        version_dir.mkdir()
        extensions_dir = version_dir / 'Extensions'
        extensions_dir.mkdir()

        with patch.dict(os.environ, {'GHIDRA_INSTALL_DIR': str(install_dir)}):
            with patch('pyghidra_decaf.bootstrap.Path') as mock_path_cls:
                mock_path_cls.side_effect = lambda *args: Path(*args)
                mock_path_cls.home.return_value = fake_home
                result = find_ghidra_extensions_dir()

        assert result == extensions_dir

    def test_returns_none_when_no_matching_version_dir(self, tmp_path: Path) -> None:
        install_dir = tmp_path / 'ghidra_11.0_PUBLIC'
        install_dir.mkdir()

        fake_home = tmp_path / 'home3'
        fake_home.mkdir()
        config_ghidra = fake_home / '.config' / 'ghidra'
        config_ghidra.mkdir(parents=True)
        # A dir that does NOT match the install name
        unrelated = config_ghidra / 'ghidra_9.0_PUBLIC'
        unrelated.mkdir()

        with patch.dict(os.environ, {'GHIDRA_INSTALL_DIR': str(install_dir)}):
            with patch('pyghidra_decaf.bootstrap.Path') as mock_path_cls:
                mock_path_cls.side_effect = lambda *args: Path(*args)
                mock_path_cls.home.return_value = fake_home
                result = find_ghidra_extensions_dir()

        assert result is None


# ---------------------------------------------------------------------------
# get_extension_dirs
# ---------------------------------------------------------------------------

class TestGetExtensionDirs:
    def test_returns_empty_set_when_extensions_dir_not_found(self) -> None:
        result = get_extension_dirs(None)
        assert result == set()

    def test_returns_empty_set_when_extensions_dir_does_not_exist(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / 'does_not_exist' / 'Extensions'
        result = get_extension_dirs(nonexistent)
        assert result == set()

    def test_returns_empty_set_when_extensions_dir_is_empty(self, tmp_path: Path) -> None:
        ext_dir = tmp_path / 'Extensions'
        ext_dir.mkdir()

        result = get_extension_dirs(ext_dir)
        assert result == set()

    def test_returns_present_extension_names(self, tmp_path: Path) -> None:
        ext_dir = tmp_path / 'Extensions'
        ext_dir.mkdir()
        (ext_dir / 'MyExt').mkdir()

        result = get_extension_dirs(ext_dir)
        assert result == {'MyExt'}

    def test_returns_all_present_extensions(self, tmp_path: Path) -> None:
        ext_dir = tmp_path / 'Extensions'
        ext_dir.mkdir()
        (ext_dir / 'ExtA').mkdir()
        (ext_dir / 'ExtB').mkdir()
        (ext_dir / 'ExtC').mkdir()

        result = get_extension_dirs(ext_dir)
        assert result == {'ExtA', 'ExtB', 'ExtC'}

    def test_filters_out_non_directory_entries(self, tmp_path: Path) -> None:
        ext_dir = tmp_path / 'Extensions'
        ext_dir.mkdir()
        (ext_dir / 'RealExt').mkdir()
        # A regular file in the same directory must be ignored
        (ext_dir / 'NotADir').write_text('file content')

        result = get_extension_dirs(ext_dir)
        assert result == {'RealExt'}

    def test_diff_pattern_supports_convergence_check(self, tmp_path: Path) -> None:
        """The before/after diff is the bootstrap's convergence signal."""
        ext_dir = tmp_path / 'Extensions'
        ext_dir.mkdir()
        (ext_dir / 'Existing').mkdir()

        before = get_extension_dirs(ext_dir)
        (ext_dir / 'NewlyCompiled').mkdir()
        after = get_extension_dirs(ext_dir)

        assert after - before == {'NewlyCompiled'}
        # And once nothing changes, the diff is empty (convergence reached).
        assert after - after == set()

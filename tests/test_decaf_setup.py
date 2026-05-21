"""Unit tests for pyghidra_decaf.decaf_setup — Java template and entry point loading."""

# Standard Libraries
import logging
from pathlib import Path
from unittest.mock import (
    MagicMock,
    patch,
)

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.decaf_setup import (
    _load_entry_points,
    plugin_java_template,
)
from pyghidra_decaf.launch import (
    PluginStatus,
    PluginType,
)


# ---------------------------------------------------------------------------
# _load_entry_points
# ---------------------------------------------------------------------------

class TestLoadEntryPoints:
    def test_returns_empty_list_when_no_group_matches(self) -> None:
        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = []
            result = _load_entry_points('nonexistent.group.xyz')
        assert result == []

    def test_returns_loaded_callbacks(self) -> None:
        fake_callback = MagicMock(return_value='setup_result')
        fake_entry = MagicMock()
        fake_entry.name = 'my_plugin'
        fake_entry.load.return_value = fake_callback

        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = [fake_entry]
            result = _load_entry_points('decaf.init')

        assert len(result) == 1
        assert result[0] is fake_callback

    def test_loads_multiple_entry_points(self) -> None:
        cb_a = MagicMock()
        cb_b = MagicMock()

        entry_a = MagicMock()
        entry_a.name = 'plugin_a'
        entry_a.load.return_value = cb_a

        entry_b = MagicMock()
        entry_b.name = 'plugin_b'
        entry_b.load.return_value = cb_b

        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = [entry_a, entry_b]
            result = _load_entry_points('decaf.init')

        assert result == [cb_a, cb_b]

    def test_failed_load_is_caught_and_logged_not_raised(self, caplog) -> None:
        bad_entry = MagicMock()
        bad_entry.name = 'broken_plugin'
        bad_entry.load.side_effect = ImportError('no module named broken')

        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = [bad_entry]
            with caplog.at_level(logging.ERROR, logger='pyghidra_decaf.decaf_setup'):
                result = _load_entry_points('decaf.init')

        # The bad entry is skipped — result is empty
        assert result == []

    def test_failed_load_logs_error_message(self, caplog) -> None:
        bad_entry = MagicMock()
        bad_entry.name = 'broken_plugin'
        bad_entry.load.side_effect = RuntimeError('something went wrong')

        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = [bad_entry]
            with caplog.at_level(logging.ERROR, logger='pyghidra_decaf.decaf_setup'):
                _load_entry_points('decaf.init')

        assert any('broken_plugin' in record.message for record in caplog.records)

    def test_partial_failure_returns_successful_entries(self, caplog) -> None:
        good_cb = MagicMock()
        good_entry = MagicMock()
        good_entry.name = 'good_plugin'
        good_entry.load.return_value = good_cb

        bad_entry = MagicMock()
        bad_entry.name = 'bad_plugin'
        bad_entry.load.side_effect = ValueError('oops')

        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = [good_entry, bad_entry]
            with caplog.at_level(logging.ERROR, logger='pyghidra_decaf.decaf_setup'):
                result = _load_entry_points('decaf.init')

        assert result == [good_cb]

    def test_none_entries_returns_empty(self) -> None:
        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = None
            result = _load_entry_points('some.group')
        assert result == []


# ---------------------------------------------------------------------------
# plugin_java_template formatting
# ---------------------------------------------------------------------------

def _format_template(
    *,
    package_name: str = 'com.example.plugins',
    plugin_status: str = 'PluginStatus.STABLE',
    plugin_package: str = 'ExampleModule',
    plugin_category: str = 'Analysis',
    short_description: str = 'A short desc',
    description: str = 'A longer description.',
    class_name: str = 'MyPlugin',
    parent_type: str = 'Plugin',
    additional_imports: str = '',
    services_provided: str = '',
    services_required: str = '',
    events_consumed: str = '',
    events_provided: str = '',
    is_slow_installation: str = 'false',
) -> str:
    return plugin_java_template.format(
        package_name=package_name,
        plugin_status=plugin_status,
        plugin_package=plugin_package,
        plugin_category=plugin_category,
        short_description=short_description,
        description=description,
        class_name=class_name,
        parent_type=parent_type,
        additional_imports=additional_imports,
        services_provided=services_provided,
        services_required=services_required,
        events_consumed=events_consumed,
        events_provided=events_provided,
        is_slow_installation=is_slow_installation,
    )


class TestPluginJavaTemplateAnnotation:
    def test_contains_plugin_info_annotation(self) -> None:
        src = _format_template()
        assert '@PluginInfo(' in src

    def test_annotation_has_status(self) -> None:
        src = _format_template(plugin_status='PluginStatus.STABLE')
        assert 'status = PluginStatus.STABLE' in src

    def test_annotation_has_package_name(self) -> None:
        src = _format_template(plugin_package='MyPackage')
        assert 'packageName = "MyPackage"' in src

    def test_annotation_has_category(self) -> None:
        src = _format_template(plugin_category='Misc')
        assert 'category = "Misc"' in src

    def test_annotation_has_short_description(self) -> None:
        src = _format_template(short_description='Does stuff')
        assert 'shortDescription = "Does stuff"' in src

    def test_annotation_has_description(self) -> None:
        src = _format_template(description='More detail here.')
        assert 'description = "More detail here."' in src

    def test_annotation_has_services_provided_braces(self) -> None:
        src = _format_template()
        assert 'servicesProvided = {' in src

    def test_annotation_has_services_required_braces(self) -> None:
        src = _format_template()
        assert 'servicesRequired = {' in src

    def test_annotation_has_events_consumed_braces(self) -> None:
        src = _format_template()
        assert 'eventsConsumed = {' in src

    def test_annotation_has_events_produced_braces(self) -> None:
        src = _format_template()
        assert 'eventsProduced = {' in src

    def test_annotation_has_slow_installation(self) -> None:
        src = _format_template(is_slow_installation='false')
        assert 'isSlowInstallation = false' in src


class TestPluginJavaTemplateClassDeclaration:
    def test_class_name_in_source(self) -> None:
        src = _format_template(class_name='CoolPlugin')
        assert 'CoolPlugin' in src

    def test_extends_decaf_plugin(self) -> None:
        src = _format_template(parent_type='Plugin')
        assert 'extends DecafPlugin' in src

    def test_extends_decaf_program_plugin(self) -> None:
        src = _format_template(parent_type='ProgramPlugin')
        assert 'extends DecafProgramPlugin' in src

    def test_class_is_public_final(self) -> None:
        src = _format_template(class_name='MyPlugin')
        assert 'public final class MyPlugin' in src

    def test_package_declaration(self) -> None:
        src = _format_template(package_name='org.example.plugins')
        assert 'package org.example.plugins;' in src

    def test_constructor_has_plugin_tool_param(self) -> None:
        src = _format_template(class_name='MyPlugin')
        assert 'public MyPlugin(PluginTool tool)' in src

    def test_set_initializer_method_present(self) -> None:
        src = _format_template(class_name='MyPlugin')
        assert 'public static void setInitializer' in src

    def test_initializer_field_declaration(self) -> None:
        src = _format_template(class_name='MyPlugin')
        assert 'private static Consumer<MyPlugin> initializer = null;' in src


class TestPluginJavaTemplateInitMethod:
    def test_init_method_override_annotation(self) -> None:
        src = _format_template()
        assert '@Override' in src

    def test_init_method_signature(self) -> None:
        src = _format_template()
        assert 'protected void init()' in src

    def test_null_check_guard_present(self) -> None:
        src = _format_template()
        assert 'if (initializer == null)' in src

    def test_null_check_has_early_return(self) -> None:
        src = _format_template()
        # Guard must include a return to skip init when python not ready
        lines = src.splitlines()
        null_check_idx = next(
            i for i, line in enumerate(lines) if 'if (initializer == null)' in line
        )
        # The return should appear within a few lines after the null check
        nearby = '\n'.join(lines[null_check_idx:null_check_idx + 5])
        assert 'return;' in nearby

    def test_initializer_accept_call(self) -> None:
        src = _format_template(class_name='MyPlugin')
        assert 'initializer.accept(this);' in src


class TestPluginJavaTemplateServicesAndEvents:
    def test_single_service_provided(self) -> None:
        src = _format_template(services_provided='MyService.class')
        assert 'MyService.class' in src

    def test_multiple_services_provided(self) -> None:
        src = _format_template(services_provided='ServiceA.class, ServiceB.class')
        assert 'ServiceA.class' in src
        assert 'ServiceB.class' in src

    def test_single_event_consumed(self) -> None:
        src = _format_template(events_consumed='ProgramActivatedPluginEvent.class')
        assert 'ProgramActivatedPluginEvent.class' in src

    def test_multiple_events_produced(self) -> None:
        src = _format_template(events_provided='EventA.class, EventB.class')
        assert 'EventA.class' in src
        assert 'EventB.class' in src

    def test_additional_imports_included(self) -> None:
        src = _format_template(additional_imports='import com.example.MyService;')
        assert 'import com.example.MyService;' in src

    def test_slow_installation_true(self) -> None:
        src = _format_template(is_slow_installation='true')
        assert 'isSlowInstallation = true' in src


# ---------------------------------------------------------------------------
# Stub Rebuild Detection (NEW)
# ---------------------------------------------------------------------------


class TestStubNeedsRebuild:
    """Tests for _stub_needs_rebuild() helper function (RED: function doesn't exist yet)."""

    def test_rebuild_needed_when_stub_file_missing(self, tmp_path: Path) -> None:
        """If stub file doesn't exist, rebuild is needed."""
        from pyghidra_decaf.decaf_setup import _stub_needs_rebuild

        stub_file = tmp_path / 'TestPlugin.java'

        # Stub file doesn't exist
        assert not stub_file.exists()

        result = _stub_needs_rebuild(stub_file, 'public class TestPlugin {}')
        assert result is True, 'Should rebuild when stub file missing'

    def test_rebuild_needed_when_stub_content_differs(self, tmp_path: Path) -> None:
        """If stub content differs (metadata changed), rebuild is needed."""
        from pyghidra_decaf.decaf_setup import _stub_needs_rebuild

        stub_file = tmp_path / 'TestPlugin.java'

        # Write old stub
        old_content = 'public class TestPlugin { /* ServiceA */ }'
        stub_file.write_text(old_content)

        # New content (metadata changed)
        new_content = 'public class TestPlugin { /* ServiceB */ }'

        result = _stub_needs_rebuild(stub_file, new_content)
        assert result is True, 'Should rebuild when stub content differs'

    def test_no_rebuild_when_stub_unchanged(self, tmp_path: Path) -> None:
        """If stub content matches on-disk file, no rebuild needed."""
        from pyghidra_decaf.decaf_setup import _stub_needs_rebuild

        stub_file = tmp_path / 'TestPlugin.java'

        content = 'public class TestPlugin {}'
        stub_file.write_text(content)

        result = _stub_needs_rebuild(stub_file, content)
        assert result is False, 'Should not rebuild when stub content is identical'

    def test_no_rebuild_with_template_generated_stub(self, tmp_path: Path) -> None:
        """
        Real-world scenario: stub generated with _format_template,
        written to disk, then re-rendered identically — no rebuild needed.
        """
        from pyghidra_decaf.decaf_setup import _stub_needs_rebuild

        stub_file = tmp_path / 'TestPlugin.java'

        params = dict(
            package_name='test.pkg',
            class_name='TestPlugin',
            services_provided='ServiceA.class',
        )
        rendered_v1 = _format_template(**params)

        # Write to disk
        stub_file.write_text(rendered_v1)

        # Re-render with identical params
        rendered_v2 = _format_template(**params)

        assert rendered_v1 == rendered_v2, 'Template should be deterministic'

        result = _stub_needs_rebuild(stub_file, rendered_v2)
        assert result is False, 'Should not rebuild when template-rendered stubs are identical'

    def test_rebuild_when_template_stub_metadata_changes(self, tmp_path: Path) -> None:
        """
        Real-world scenario: stub generated with one set of metadata, then
        re-rendered with different metadata — rebuild needed.
        """
        from pyghidra_decaf.decaf_setup import _stub_needs_rebuild

        stub_file = tmp_path / 'TestPlugin.java'

        old_rendered = _format_template(
            class_name='TestPlugin',
            services_provided='',
        )
        stub_file.write_text(old_rendered)

        new_rendered = _format_template(
            class_name='TestPlugin',
            services_provided='MyNewService.class',
        )

        assert old_rendered != new_rendered, 'Rendered stubs should differ when metadata changes'

        result = _stub_needs_rebuild(stub_file, new_rendered)
        assert result is True, 'Should rebuild when metadata changes cause stub content to differ'

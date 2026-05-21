"""Unit tests for pyghidra_decaf.launch — enums and data classes."""

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.launch import (
    DecafExtensionInfo,
    DecafPluginInfo,
    PluginStatus,
    PluginType,
)


# ---------------------------------------------------------------------------
# PluginStatus enum
# ---------------------------------------------------------------------------

class TestPluginStatus:
    def test_has_deprecated(self) -> None:
        assert hasattr(PluginStatus, 'DEPRECATED')

    def test_has_hidden(self) -> None:
        assert hasattr(PluginStatus, 'HIDDEN')

    def test_has_released(self) -> None:
        assert hasattr(PluginStatus, 'RELEASED')

    def test_has_stable(self) -> None:
        assert hasattr(PluginStatus, 'STABLE')

    def test_has_unstable(self) -> None:
        assert hasattr(PluginStatus, 'UNSTABLE')

    def test_members_are_distinct(self) -> None:
        values = [m.value for m in PluginStatus]
        assert len(values) == len(set(values))

    def test_members_count(self) -> None:
        assert len(PluginStatus) == 5

    def test_access_by_name(self) -> None:
        assert PluginStatus['STABLE'] is PluginStatus.STABLE

    def test_equality(self) -> None:
        assert PluginStatus.STABLE == PluginStatus.STABLE
        assert PluginStatus.STABLE != PluginStatus.UNSTABLE


# ---------------------------------------------------------------------------
# PluginType enum
# ---------------------------------------------------------------------------

class TestPluginType:
    def test_has_plugin(self) -> None:
        assert hasattr(PluginType, 'Plugin')

    def test_has_program_plugin(self) -> None:
        assert hasattr(PluginType, 'ProgramPlugin')

    def test_members_count(self) -> None:
        assert len(PluginType) == 2

    def test_members_are_distinct(self) -> None:
        values = [m.value for m in PluginType]
        assert len(values) == len(set(values))

    def test_plugin_name(self) -> None:
        assert PluginType.Plugin.name == 'Plugin'

    def test_program_plugin_name(self) -> None:
        assert PluginType.ProgramPlugin.name == 'ProgramPlugin'


# ---------------------------------------------------------------------------
# DecafPluginInfo construction
# ---------------------------------------------------------------------------

def _make_plugin_info(**overrides) -> DecafPluginInfo:
    defaults = dict(
        type=PluginType.Plugin,
        qualname='mypackage.myplugin.MyPlugin',
        class_name='MyPlugin',
        status=PluginStatus.STABLE,
        module_name='MyModule',
        category='TestCategory',
        shortDescription='A short description',
        description='A longer description of the plugin.',
    )
    defaults.update(overrides)
    return DecafPluginInfo(**defaults)


class TestDecafPluginInfoConstruction:
    def test_required_fields_set(self) -> None:
        info = _make_plugin_info()
        assert info.type is PluginType.Plugin
        assert info.qualname == 'mypackage.myplugin.MyPlugin'
        assert info.class_name == 'MyPlugin'
        assert info.status is PluginStatus.STABLE
        assert info.module_name == 'MyModule'
        assert info.category == 'TestCategory'
        assert info.shortDescription == 'A short description'
        assert info.description == 'A longer description of the plugin.'

    def test_optional_defaults(self) -> None:
        info = _make_plugin_info()
        assert info.plugin_imports == ()
        assert info.servicesProvided == []
        assert info.servicesRequired == []
        assert info.eventsConsumed == []
        assert info.eventsProduced == []
        assert info.isSlowInstallation is False

    def test_optional_fields_can_be_set(self) -> None:
        info = _make_plugin_info(
            plugin_imports=('some.Import',),
            servicesProvided=['ServiceA'],
            servicesRequired=['ServiceB'],
            eventsConsumed=['EventX'],
            eventsProduced=['EventY'],
            isSlowInstallation=True,
        )
        assert info.plugin_imports == ('some.Import',)
        assert info.servicesProvided == ['ServiceA']
        assert info.servicesRequired == ['ServiceB']
        assert info.eventsConsumed == ['EventX']
        assert info.eventsProduced == ['EventY']
        assert info.isSlowInstallation is True

    def test_with_program_plugin_type(self) -> None:
        info = _make_plugin_info(type=PluginType.ProgramPlugin)
        assert info.type is PluginType.ProgramPlugin

    def test_is_namedtuple(self) -> None:
        info = _make_plugin_info()
        # NamedTuples support tuple unpacking and indexing
        assert info[0] is PluginType.Plugin  # type field is index 0

    def test_immutable(self) -> None:
        info = _make_plugin_info()
        with pytest.raises(AttributeError):
            info.class_name = 'OtherClass'  # type: ignore[misc]


class TestDecafPluginInfoPythonFqName:
    def test_fq_name_concatenates_module_and_qualname(self) -> None:
        info = _make_plugin_info(
            module_name='com.example.module',
            qualname='subpkg.MyPlugin',
        )
        assert info.python_fq_name == 'com.example.module.subpkg.MyPlugin'

    def test_fq_name_simple(self) -> None:
        info = _make_plugin_info(
            module_name='MyModule',
            qualname='MyPlugin',
        )
        assert info.python_fq_name == 'MyModule.MyPlugin'

    def test_fq_name_deeply_qualified(self) -> None:
        info = _make_plugin_info(
            module_name='org.example',
            qualname='plugins.analysis.AnalysisPlugin',
        )
        assert info.python_fq_name == 'org.example.plugins.analysis.AnalysisPlugin'

    def test_fq_name_format(self) -> None:
        info = _make_plugin_info(
            module_name='ModA',
            qualname='a.b.C',
        )
        # Must be "{module_name}.{qualname}"
        assert info.python_fq_name == f'{info.module_name}.{info.qualname}'


# ---------------------------------------------------------------------------
# DecafExtensionInfo construction
# ---------------------------------------------------------------------------

class TestDecafExtensionInfoConstruction:
    def test_required_fields(self) -> None:
        plugin = _make_plugin_info()
        ext = DecafExtensionInfo(
            name='MyExtension',
            description='An extension.',
            author='Alice',
            version='10.3',
            plugins=[plugin],
        )
        assert ext.name == 'MyExtension'
        assert ext.description == 'An extension.'
        assert ext.author == 'Alice'
        assert ext.version == '10.3'
        assert ext.plugins == [plugin]

    def test_optional_java_package_default(self) -> None:
        ext = DecafExtensionInfo(
            name='Ext',
            description='',
            author='',
            version='1.0',
            plugins=[],
        )
        assert ext.java_package == ''

    def test_optional_java_source_default(self) -> None:
        ext = DecafExtensionInfo(
            name='Ext',
            description='',
            author='',
            version='1.0',
            plugins=[],
        )
        assert ext.java_source == []

    def test_with_java_package(self) -> None:
        ext = DecafExtensionInfo(
            name='Ext',
            description='',
            author='',
            version='1.0',
            plugins=[],
            java_package='com.example',
        )
        assert ext.java_package == 'com.example'

    def test_multiple_plugins(self) -> None:
        p1 = _make_plugin_info(class_name='PluginOne', qualname='pkg.PluginOne')
        p2 = _make_plugin_info(class_name='PluginTwo', qualname='pkg.PluginTwo',
                               type=PluginType.ProgramPlugin)
        ext = DecafExtensionInfo(
            name='MultiExt',
            description='Two plugins.',
            author='Bob',
            version='11.0',
            plugins=[p1, p2],
        )
        assert len(ext.plugins) == 2
        assert ext.plugins[0].class_name == 'PluginOne'
        assert ext.plugins[1].class_name == 'PluginTwo'

    def test_empty_plugins_list(self) -> None:
        ext = DecafExtensionInfo(
            name='Empty',
            description='',
            author='',
            version='1.0',
            plugins=[],
        )
        assert ext.plugins == []

    def test_is_namedtuple(self) -> None:
        ext = DecafExtensionInfo(
            name='X',
            description='',
            author='',
            version='1.0',
            plugins=[],
        )
        assert ext[0] == 'X'  # name is index 0

    def test_immutable(self) -> None:
        ext = DecafExtensionInfo(
            name='X',
            description='',
            author='',
            version='1.0',
            plugins=[],
        )
        with pytest.raises(AttributeError):
            ext.name = 'Y'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Mutable-default isolation
# ---------------------------------------------------------------------------

class TestDecafPluginInfoMutableDefaultIsolation:
    """Guard against the classic mutable-default-argument trap.

    Two ``DecafPluginInfo`` instances created without an explicit
    ``plugin_imports`` argument must **not** share the same underlying mutable
    object.  The default must be immutable (a tuple) so that accidental
    mutation of one instance cannot bleed into another.
    """

    def test_plugin_imports_default_is_not_shared_between_instances(self) -> None:
        first = _make_plugin_info()
        second = _make_plugin_info()

        # Tuples are immutable, so we cannot append in-place.
        # Instead, verify that both instances carry the same *value* (empty)
        # and that building a local list from one does not affect the other —
        # this mirrors exactly what decaf_setup.py does with
        #   addl_imports = list(plugin.plugin_imports)
        local_copy = list(first.plugin_imports)
        local_copy.append('some.Import')

        assert second.plugin_imports == (), (
            "Building a local list from first.plugin_imports and appending to it "
            "must not affect second.plugin_imports."
        )
        assert first.plugin_imports == (), (
            "first.plugin_imports itself must remain unmodified — "
            "it is an immutable tuple default."
        )

    def test_plugin_imports_default_is_immutable_tuple(self) -> None:
        info = _make_plugin_info()

        assert isinstance(info.plugin_imports, tuple), (
            "plugin_imports default must be a tuple, not a mutable list."
        )
        with pytest.raises(AttributeError):
            info.plugin_imports.append('x')  # type: ignore[attr-defined]

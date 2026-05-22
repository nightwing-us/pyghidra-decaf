# Standard Libraries
from typing import (
    Any,
)

# Third Party Libraries
from jpype import JClass  # type: ignore[import-untyped]


def _set_field(cls: 'JClass', fname: str, value: Any, obj: object = None) -> None:
    cls = cls.class_
    field = cls.getDeclaredField(fname)
    field.setAccessible(True)
    field.set(obj, value)


def _get_private_class(class_name: str) -> 'JClass':
    # Third Party Libraries
    from java.lang import ClassLoader  # type: ignore[import-not-found]

    gcl = ClassLoader.getSystemClassLoader()
    return JClass(class_name, loader=gcl)

# Standard Libraries
from itertools import islice
import threading
from typing import (
    Iterable,
    Iterator,
    TypeVar,
)


class AtomicCounter:
    """
    A thread-safe integer counter that supports atomic increment, decrement,
    comparison with integers or other AtomicCounter instances, and += / -= operations.
    """

    def __init__(self, initial: int = 0) -> None:
        self._value: int = initial
        self._lock: threading.RLock = threading.RLock()

    def increment(self) -> int:
        """
        Atomically increments the counter by 1.
        Returns the new value.
        """
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self) -> int:
        """
        Atomically decrements the counter by 1.
        Returns the new value.
        """
        with self._lock:
            self._value -= 1
            return self._value

    def value(self) -> int:
        """
        Returns the current value of the counter.
        """
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0

    # In-place addition: counter += int
    def __iadd__(self, other: int) -> 'AtomicCounter':
        with self._lock:
            self._value += other
        return self

    # In-place subtraction: counter -= int
    def __isub__(self, other: int) -> 'AtomicCounter':
        with self._lock:
            self._value -= other
        return self

    # Equality comparison: counter == int or counter == AtomicCounter
    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtomicCounter):
            return self.value() == other.value()
        elif isinstance(other, int):
            return self.value() == other
        return NotImplemented

    # Inequality comparison: counter != other
    def __ne__(self, other: object) -> bool:
        return not self == other

    def __lt__(self, other: object) -> bool:
        if isinstance(other, (AtomicCounter, int)):
            return self.value() < (
                other.value() if isinstance(other, AtomicCounter) else other
            )
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, (AtomicCounter, int)):
            return self.value() <= (
                other.value() if isinstance(other, AtomicCounter) else other
            )
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, (AtomicCounter, int)):
            return self.value() > (
                other.value() if isinstance(other, AtomicCounter) else other
            )
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, (AtomicCounter, int)):
            return self.value() >= (
                other.value() if isinstance(other, AtomicCounter) else other
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'AtomicCounter({self.value()})'


T = TypeVar('T')


def paginate(
    iterable: Iterable[T], offset: int = 0, limit: int | None = None
) -> Iterator[T]:
    """
    Lazily paginates any iterable or iterator.

    :param iterable: Any iterable or iterator to paginate.
    :param offset: Number of items to skip from the start (default: 0).
    :param limit: Maximum number of items to yield after the offset (default: None for no limit).
    :returns: An iterator over the paginated items.
    """
    # Convert to iterator (if it isn't already)
    # Skip 'offset' items
    return islice(iter(iterable), offset, offset + limit if limit is not None else None)

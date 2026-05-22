"""Unit tests for pyghidra_decaf.util — AtomicCounter and paginate."""

# Standard Libraries
import threading
from typing import List

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.util import (
    AtomicCounter,
    paginate,
)


# ---------------------------------------------------------------------------
# AtomicCounter
# ---------------------------------------------------------------------------

class TestAtomicCounterInit:
    def test_default_value_is_zero(self) -> None:
        c = AtomicCounter()
        assert c.value() == 0

    def test_custom_initial_value(self) -> None:
        c = AtomicCounter(42)
        assert c.value() == 42

    def test_negative_initial_value(self) -> None:
        c = AtomicCounter(-5)
        assert c.value() == -5


class TestAtomicCounterMutations:
    def test_increment_returns_new_value(self) -> None:
        c = AtomicCounter(0)
        result = c.increment()
        assert result == 1
        assert c.value() == 1

    def test_increment_multiple_times(self) -> None:
        c = AtomicCounter(0)
        c.increment()
        c.increment()
        c.increment()
        assert c.value() == 3

    def test_decrement_returns_new_value(self) -> None:
        c = AtomicCounter(5)
        result = c.decrement()
        assert result == 4
        assert c.value() == 4

    def test_decrement_below_zero(self) -> None:
        c = AtomicCounter(0)
        result = c.decrement()
        assert result == -1

    def test_iadd_updates_value(self) -> None:
        c = AtomicCounter(10)
        c += 5
        assert c.value() == 15

    def test_iadd_returns_same_object(self) -> None:
        c = AtomicCounter(0)
        original_id = id(c)
        c += 3
        assert id(c) == original_id

    def test_isub_updates_value(self) -> None:
        c = AtomicCounter(10)
        c -= 4
        assert c.value() == 6

    def test_isub_returns_same_object(self) -> None:
        c = AtomicCounter(0)
        original_id = id(c)
        c -= 1
        assert id(c) == original_id

    def test_reset_sets_to_zero(self) -> None:
        c = AtomicCounter(99)
        c.reset()
        assert c.value() == 0

    def test_reset_from_negative(self) -> None:
        c = AtomicCounter(-10)
        c.reset()
        assert c.value() == 0


class TestAtomicCounterComparisons:
    def test_eq_int(self) -> None:
        c = AtomicCounter(7)
        assert c == 7

    def test_eq_other_counter_same_value(self) -> None:
        a = AtomicCounter(3)
        b = AtomicCounter(3)
        assert a == b

    def test_eq_other_counter_different_value(self) -> None:
        a = AtomicCounter(3)
        b = AtomicCounter(4)
        assert not (a == b)

    def test_ne_int(self) -> None:
        c = AtomicCounter(5)
        assert c != 6

    def test_ne_counter(self) -> None:
        a = AtomicCounter(1)
        b = AtomicCounter(2)
        assert a != b

    def test_lt_int(self) -> None:
        c = AtomicCounter(3)
        assert c < 4
        assert not (c < 3)

    def test_le_int(self) -> None:
        c = AtomicCounter(3)
        assert c <= 3
        assert c <= 4
        assert not (c <= 2)

    def test_gt_int(self) -> None:
        c = AtomicCounter(5)
        assert c > 4
        assert not (c > 5)

    def test_ge_int(self) -> None:
        c = AtomicCounter(5)
        assert c >= 5
        assert c >= 4
        assert not (c >= 6)

    def test_lt_counter(self) -> None:
        a = AtomicCounter(1)
        b = AtomicCounter(2)
        assert a < b
        assert not (b < a)

    def test_gt_counter(self) -> None:
        a = AtomicCounter(10)
        b = AtomicCounter(1)
        assert a > b

    def test_eq_unsupported_type_returns_not_implemented(self) -> None:
        c = AtomicCounter(1)
        assert c.__eq__("not an int") is NotImplemented

    def test_lt_unsupported_type_returns_not_implemented(self) -> None:
        c = AtomicCounter(1)
        assert c.__lt__("bad") is NotImplemented

    def test_gt_unsupported_type_returns_not_implemented(self) -> None:
        c = AtomicCounter(1)
        assert c.__gt__("bad") is NotImplemented


class TestAtomicCounterRepr:
    def test_repr_contains_value(self) -> None:
        c = AtomicCounter(42)
        assert "42" in repr(c)
        assert "AtomicCounter" in repr(c)


class TestAtomicCounterThreadSafety:
    """Stress test: concurrent increments and decrements should cancel out."""

    def test_concurrent_increments(self) -> None:
        counter = AtomicCounter(0)
        threads_count = 50
        increments_per_thread = 100

        def worker() -> None:
            for _ in range(increments_per_thread):
                counter.increment()

        threads = [threading.Thread(target=worker) for _ in range(threads_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter.value() == threads_count * increments_per_thread

    def test_concurrent_increments_and_decrements_cancel(self) -> None:
        counter = AtomicCounter(0)
        n = 50

        def inc_worker() -> None:
            for _ in range(100):
                counter.increment()

        def dec_worker() -> None:
            for _ in range(100):
                counter.decrement()

        threads: List[threading.Thread] = []
        threads.extend(threading.Thread(target=inc_worker) for _ in range(n))
        threads.extend(threading.Thread(target=dec_worker) for _ in range(n))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter.value() == 0


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------

class TestPaginate:
    def test_basic_offset_and_limit(self) -> None:
        data = list(range(10))
        result = list(paginate(data, offset=2, limit=4))
        assert result == [2, 3, 4, 5]

    def test_offset_zero_is_default(self) -> None:
        data = [10, 20, 30]
        result = list(paginate(data, limit=2))
        assert result == [10, 20]

    def test_no_limit_returns_all_from_offset(self) -> None:
        data = list(range(5))
        result = list(paginate(data, offset=2))
        assert result == [2, 3, 4]

    def test_no_offset_no_limit_returns_all(self) -> None:
        data = [1, 2, 3]
        result = list(paginate(data))
        assert result == [1, 2, 3]

    def test_limit_zero_returns_empty(self) -> None:
        data = [1, 2, 3]
        result = list(paginate(data, limit=0))
        assert result == []

    def test_limit_larger_than_remaining_returns_rest(self) -> None:
        data = list(range(5))
        result = list(paginate(data, offset=3, limit=100))
        assert result == [3, 4]

    def test_offset_beyond_end_returns_empty(self) -> None:
        data = [1, 2, 3]
        result = list(paginate(data, offset=10))
        assert result == []

    def test_empty_iterable(self) -> None:
        result = list(paginate([], offset=0, limit=5))
        assert result == []

    def test_works_with_generator(self) -> None:
        def gen():
            yield from range(10)
        result = list(paginate(gen(), offset=5, limit=3))
        assert result == [5, 6, 7]

    def test_works_with_string_iterable(self) -> None:
        result = list(paginate("abcdef", offset=1, limit=3))
        assert result == ["b", "c", "d"]

    def test_returns_iterator_not_list(self) -> None:
        data = [1, 2, 3]
        result = paginate(data, limit=2)
        # Should be an iterator, not a list
        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')

    def test_offset_exactly_at_end(self) -> None:
        data = [1, 2, 3]
        result = list(paginate(data, offset=3, limit=1))
        assert result == []

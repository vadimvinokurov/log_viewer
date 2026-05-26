"""Benchmark script for search/filter engine performance.

Measures all key operations on a real log file (d:/log.txt, ~6.4M lines).
Reports median time over N runs for each operation.
"""
from __future__ import annotations

import sys
import time
import statistics

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, Highlight, SearchMode, SearchDirection

FILE = "d:/log.txt"
WARMUP = 1
RUNS = 5


def median_ms(samples: list[float]) -> float:
    return statistics.median(samples) * 1000


def bench_load() -> LogStore:
    """1. File loading — baseline, run once."""
    store = LogStore()
    with open(FILE, "rb") as f:
        buf = bytearray(f.read())
    print(f"  File size: {len(buf) / 1024 / 1024:.1f} MB, lines: detecting...")

    samples = []
    for _ in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        store.load_bytes(buf.copy(), file_path=FILE)
        samples.append(time.perf_counter() - t0)

    print(f"  Lines: {store.n:,}")
    print(f"  Load: {median_ms(samples):.0f} ms")
    return store


def bench_add_filter(store: LogStore) -> None:
    """2. Adding a single plain-CI filter (hot path)."""
    samples = []
    for _ in range(WARMUP + RUNS):
        store.clear_filters()
        t0 = time.perf_counter()
        store.add_filter(Filter(pattern="error", mode=SearchMode.PLAIN))
        samples.append(time.perf_counter() - t0)
    print(f"  Plain-CI filter 'error': {median_ms(samples):.1f} ms  ({sum(store._filter_masks[0]):,} matches)")

    # Second filter add (with existing filter)
    samples = []
    for _ in range(WARMUP + RUNS):
        store.remove_filter("error")
        store.add_filter(Filter(pattern="error", mode=SearchMode.PLAIN))
        t0 = time.perf_counter()
        store.add_filter(Filter(pattern="timeout", mode=SearchMode.PLAIN))
        samples.append(time.perf_counter() - t0)
    store.remove_filter("timeout")
    print(f"  Second filter 'timeout' (first exists): {median_ms(samples):.1f} ms")

    # Regex filter
    samples = []
    for _ in range(WARMUP + RUNS):
        store.remove_filter("error")
        t0 = time.perf_counter()
        store.add_filter(Filter(pattern=r"err(or)?", mode=SearchMode.REGEX))
        samples.append(time.perf_counter() - t0)
    store.clear_filters()
    print(f"  Regex filter 'err(or)?': {median_ms(samples):.1f} ms")

    # Simple query filter
    samples = []
    for _ in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        store.add_filter(Filter(pattern='"error" AND "config"', mode=SearchMode.SIMPLE))
        samples.append(time.perf_counter() - t0)
    store.clear_filters()
    print(f"  Simple query '\"error\" AND \"config\"': {median_ms(samples):.1f} ms")


def bench_filter_toggle(store: LogStore) -> None:
    """3. Toggling filter enabled/disabled (should be near-instant with cached masks)."""
    store.add_filter(Filter(pattern="error", mode=SearchMode.PLAIN))
    store.add_filter(Filter(pattern="warning", mode=SearchMode.PLAIN))

    samples = []
    for i in range(WARMUP + RUNS):
        store.filter_enabled = [True, True]
        t0 = time.perf_counter()
        store.filter_enabled = [True, False]  # disable second
        store._apply_filters()
        samples.append(time.perf_counter() - t0)
    print(f"  Toggle filter off: {median_ms(samples):.2f} ms")

    samples = []
    for i in range(WARMUP + RUNS):
        store.filter_enabled = [True, False]
        t0 = time.perf_counter()
        store.filter_enabled = [True, True]  # re-enable
        store._apply_filters()
        samples.append(time.perf_counter() - t0)
    print(f"  Toggle filter on: {median_ms(samples):.2f} ms")

    store.clear_filters()


def bench_level_toggle(store: LogStore) -> None:
    """4. Level toggle."""
    from log_viewer.core.models import _LEVEL_LIST, LogLevel

    samples = []
    for _ in range(WARMUP + RUNS):
        store.disabled_levels = set()
        t0 = time.perf_counter()
        store.toggle_level(LogLevel.WARNING)
        samples.append(time.perf_counter() - t0)
    store.disabled_levels = set()
    print(f"  Toggle level WARNING off: {median_ms(samples):.2f} ms")

    samples = []
    for _ in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        store.toggle_level(LogLevel.WARNING)  # toggle back on
        samples.append(time.perf_counter() - t0)
    store.disabled_levels = set()
    print(f"  Toggle level WARNING on: {median_ms(samples):.2f} ms")


def bench_category_toggle(store: LogStore) -> None:
    """5. Category toggle."""
    # Pick a category with some lines
    cats = list(store.category_counts.items())
    if not cats:
        print("  No categories found, skipping")
        return
    # Pick a mid-size category
    cats_sorted = sorted(cats, key=lambda x: x[1], reverse=True)
    target_cat = cats_sorted[min(5, len(cats_sorted) - 1)]
    print(f"  Target category: '{target_cat[0]}' ({target_cat[1]:,} lines)")

    samples = []
    for _ in range(WARMUP + RUNS):
        store.enable_all_categories()
        t0 = time.perf_counter()
        store.disable_category(target_cat[0])
        samples.append(time.perf_counter() - t0)
    store.enable_all_categories()
    print(f"  Disable category: {median_ms(samples):.2f} ms")

    samples = []
    for _ in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        store.enable_category(target_cat[0])
        samples.append(time.perf_counter() - t0)
    store.enable_all_categories()
    print(f"  Enable category: {median_ms(samples):.2f} ms")


def bench_search(store: LogStore) -> None:
    """6. Search operations."""
    # Plain CI search
    samples = []
    for _ in range(WARMUP + RUNS):
        store.clear_search()
        t0 = time.perf_counter()
        state = store.search("error", SearchMode.PLAIN, direction=SearchDirection.FORWARD)
        samples.append(time.perf_counter() - t0)
    print(f"  Plain search 'error': {median_ms(samples):.1f} ms  ({len(state.matches):,} matches)")

    # Regex search
    samples = []
    for _ in range(WARMUP + RUNS):
        store.clear_search()
        t0 = time.perf_counter()
        state = store.search(r"err(or)?", SearchMode.REGEX, direction=SearchDirection.FORWARD)
        samples.append(time.perf_counter() - t0)
    store.clear_search()
    print(f"  Regex search 'err(or)?': {median_ms(samples):.1f} ms  ({len(state.matches):,} matches)")

    # Simple query search
    samples = []
    for _ in range(WARMUP + RUNS):
        store.clear_search()
        t0 = time.perf_counter()
        state = store.search('"error" AND "config"', SearchMode.SIMPLE, direction=SearchDirection.FORWARD)
        samples.append(time.perf_counter() - t0)
    store.clear_search()
    print(f"  Simple query search '\"error\" AND \"config\"': {median_ms(samples):.1f} ms  ({len(state.matches):,} matches)")


def bench_pins(store: LogStore) -> None:
    """7. Pin operations."""
    samples = []
    for _ in range(WARMUP + RUNS):
        store.unpin_all()
        t0 = time.perf_counter()
        store.add_pin(Filter(pattern="error", mode=SearchMode.PLAIN))
        samples.append(time.perf_counter() - t0)
    store.unpin_all()
    print(f"  Add pin 'error': {median_ms(samples):.1f} ms")

    # Toggle pin
    store.add_pin(Filter(pattern="error", mode=SearchMode.PLAIN))
    samples = []
    for _ in range(WARMUP + RUNS):
        store.pinned_enabled = [True]
        t0 = time.perf_counter()
        store.pinned_enabled = [False]
        store._apply_filters()
        samples.append(time.perf_counter() - t0)
    store.unpin_all()
    print(f"  Toggle pin off: {median_ms(samples):.2f} ms")


def bench_reload(store: LogStore) -> None:
    """8. Reload file (re-parse + re-apply filters)."""
    store.add_filter(Filter(pattern="error", mode=SearchMode.PLAIN))
    with open(FILE, "rb") as f:
        buf = bytearray(f.read())

    samples = []
    for _ in range(WARMUP + RUNS):
        t0 = time.perf_counter()
        store.load_bytes(buf.copy(), file_path=FILE)
        samples.append(time.perf_counter() - t0)

    store.clear_filters()
    print(f"  Reload (with 1 filter): {median_ms(samples):.0f} ms")


def bench_combined(store: LogStore) -> None:
    """9. Combined scenario: filter + category disabled + pin."""
    with open(FILE, "rb") as f:
        buf = bytearray(f.read())

    samples = []
    for _ in range(WARMUP + RUNS):
        store.load_bytes(buf.copy(), file_path=FILE)
        t0 = time.perf_counter()
        store.add_filter(Filter(pattern="error", mode=SearchMode.PLAIN))
        store.toggle_level(LogLevel.WARNING)
        store.add_pin(Filter(pattern="timeout", mode=SearchMode.PLAIN))
        samples.append(time.perf_counter() - t0)

    store.clear_filters()
    store.disabled_levels = set()
    store.unpin_all()
    print(f"  Load + filter + level toggle + pin: {median_ms(samples):.0f} ms")


if __name__ == "__main__":
    from log_viewer.core.models import _LEVEL_LIST, LogLevel

    print("=" * 60)
    print("LOG VIEWER ENGINE BENCHMARK")
    print("=" * 60)

    print("\n--- 1. File Load ---")
    store = bench_load()

    print("\n--- 2. Add Filter ---")
    bench_add_filter(store)

    print("\n--- 3. Filter Toggle ---")
    bench_filter_toggle(store)

    print("\n--- 4. Level Toggle ---")
    bench_level_toggle(store)

    print("\n--- 5. Category Toggle ---")
    bench_category_toggle(store)

    print("\n--- 6. Search ---")
    bench_search(store)

    print("\n--- 7. Pins ---")
    bench_pins(store)

    print("\n--- 8. Reload ---")
    bench_reload(store)

    print("\n--- 9. Combined ---")
    bench_combined(store)

    print("\n" + "=" * 60)
    print("DONE")

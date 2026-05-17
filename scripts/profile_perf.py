"""Headless profiling script for log_viewer core operations.

Generates a synthetic KSIVA-format log file if the target doesn't exist,
then benchmarks parse, load, filter, category toggle, search, and batch_match.
3 runs per operation, reports median via statistics.median.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from pathlib import Path

# Make log_viewer importable from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from log_viewer.core.filter_engine import batch_match
from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, SearchDirection, SearchMode
from log_viewer.core.parser import parse_line

CATEGORIES = [
    "app/main",
    "net/http",
    "db/query",
    "ui/render",
    "sys/init",
]
LEVELS = [
    "LOG_INFO",
    "LOG_DEBUG",
    "LOG_WARNING",
    "LOG_ERROR",
    "LOG_TRACE",
]


def generate_synthetic(path: str, n: int) -> list[str]:
    """Generate n KSIVA-format lines and write them to *path*. Returns raw lines."""
    rng = random.Random(42)
    lines: list[str] = []
    for i in range(n):
        minute = i % 60
        second = (i * 7) % 60
        ts = f"2024-01-15T10:{minute:02d}:{second:02d}.000"
        cat = CATEGORIES[i % len(CATEGORIES)]
        level = LEVELS[i % len(LEVELS)]
        msg = f"Message line {i} with some padding text"
        lines.append(f"{ts} {cat} [{level}] {msg}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")

    return lines


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

def _bench(fn, *args, runs: int = 3) -> float:
    """Run *fn* *runs* times, return median elapsed seconds."""
    timings: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(*args)
        timings.append(time.perf_counter() - t0)
    return statistics.median(timings)


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------

def bench_parse(raw_lines: list[str]) -> float:
    """Benchmark parse_line on all raw lines."""
    def _run() -> None:
        for i, raw in enumerate(raw_lines):
            parse_line(raw, i)
    return _bench(_run)


def bench_load(raw_lines: list[str]) -> float:
    """Benchmark LogStore.load_lines end-to-end (fresh store each run)."""
    def _run() -> None:
        store = LogStore()
        store.load_lines(raw_lines)
    return _bench(_run)


def bench_apply_filters(store: LogStore, n_filters: int) -> float:
    """Benchmark _apply_filters with *n_filters* active plain filters.

    Saves and restores store.filters / store.filter_enabled.
    """
    saved_filters = store.filters[:]
    saved_enabled = store.filter_enabled[:]

    try:
        store.filters = [
            Filter(pattern=f"pad{i}", mode=SearchMode.PLAIN)
            for i in range(n_filters)
        ]
        store.filter_enabled = [True] * n_filters
        med = _bench(store._apply_filters)
    finally:
        store.filters = saved_filters
        store.filter_enabled = saved_enabled
        store._apply_filters()

    return med


def bench_category_toggle(store: LogStore) -> float:
    """Benchmark disable + re-enable first category."""
    cats = list(store.category_counts.keys())
    if not cats:
        return 0.0
    first_cat = cats[0]

    def _run() -> None:
        store.disable_category(first_cat)
        store.enable_category(first_cat)

    return _bench(_run)


def bench_search_plain(store: LogStore) -> float:
    """Benchmark search with plain text."""
    def _run() -> None:
        store.search("Message", SearchMode.PLAIN)
    return _bench(_run)


def bench_search_regex(store: LogStore) -> float:
    """Benchmark search with regex."""
    def _run() -> None:
        store.search(r"Message\s+line\s+\d+", SearchMode.REGEX)
    return _bench(_run)


def bench_search_simple(store: LogStore) -> float:
    """Benchmark search with simple query."""
    def _run() -> None:
        store.search('"Message" AND "1000"', SearchMode.SIMPLE)
    return _bench(_run)


def bench_batch_match(store: LogStore) -> float:
    """Benchmark batch_match on first 100K filtered lines with 1 plain filter."""
    n = min(100_000, len(store.filtered_indices))
    indices = store.filtered_indices[:n]
    texts = [store.lines[i].message for i in indices]
    filters = [Filter(pattern="padding", mode=SearchMode.PLAIN)]

    def _run() -> None:
        batch_match(texts, filters)

    return _bench(_run)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_baseline(path: str) -> dict[str, float]:
    """Load baseline timings from a text file (handles pipe-delimited tables)."""
    results = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("-") or line.startswith("Operation") or line.startswith("+"):
                continue
            # Strip outer pipe characters
            line = line.strip("|").strip()
            if not line:
                continue
            # Split on pipe separator if present (pipe-delimited table format)
            if "|" in line:
                segs = line.rsplit("|", 1)
                if len(segs) == 2:
                    name = segs[0].strip()
                    try:
                        results[name] = float(segs[1].strip())
                    except ValueError:
                        pass
            else:
                parts = line.rsplit(None, 1)
                if len(parts) == 2:
                    try:
                        results[parts[0].strip()] = float(parts[1])
                    except ValueError:
                        pass
    return results


def print_comparison(results: list[tuple[str, float]], baseline: dict[str, float]) -> None:
    """Print comparison table with before/after and speedup."""
    print("\n" + "=" * 85)
    print(f"{'Operation':<35} {'Before (s)':>10} {'After (s)':>10} {'Speedup':>10}")
    print("-" * 85)
    for name, secs in results:
        before = baseline.get(name)
        if before is not None and secs > 0:
            speedup = before / secs
            print(f"{name:<35} {before:>10.4f} {secs:>10.4f} {speedup:>9.2f}x")
        else:
            print(f"{name:<35} {'N/A':>10} {secs:>10.4f} {'N/A':>10}")
    print("=" * 85)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile log_viewer core ops")
    parser.add_argument("--file", default="d:/log.txt", help="Log file path (default: d:/log.txt)")
    parser.add_argument("--lines", type=int, default=6_000_000, help="Number of synthetic lines to generate (default: 6M)")
    parser.add_argument("--compare", default=None, help="Path to baseline timings file for comparison")
    args = parser.parse_args()

    file_path = args.file
    n_lines = args.lines

    # Load or generate
    if Path(file_path).exists():
        print(f"Reading existing file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            raw_lines = f.read().splitlines()
        print(f"  Loaded {len(raw_lines):,} lines")
    else:
        print(f"Generating {n_lines:,} synthetic lines -> {file_path}")
        raw_lines = generate_synthetic(file_path, n_lines)

    # Load store once for reuse in most benchmarks
    print("Loading LogStore for benchmark base...")
    store = LogStore()
    store.load_lines(raw_lines)
    print(f"  {len(store.lines):,} parsed lines, {len(store.filtered_indices):,} visible")

    results: list[tuple[str, float]] = []

    print("\nRunning benchmarks (3 runs each, reporting median)...\n")

    results.append(("parse_line (all lines)", bench_parse(raw_lines)))
    results.append(("LogStore.load_lines", bench_load(raw_lines)))
    results.append(("_apply_filters (0 filters)", bench_apply_filters(store, 0)))
    results.append(("_apply_filters (1 filter)", bench_apply_filters(store, 1)))
    results.append(("_apply_filters (3 filters)", bench_apply_filters(store, 3)))
    results.append(("_apply_filters (5 filters)", bench_apply_filters(store, 5)))
    results.append(("category toggle (disable+enable)", bench_category_toggle(store)))
    results.append(("search plain", bench_search_plain(store)))
    results.append(("search regex", bench_search_regex(store)))
    results.append(("search simple query", bench_search_simple(store)))
    results.append(("batch_match (100K lines, 1 filter)", bench_batch_match(store)))

    # Print table
    col_op = max(len(op) for op, _ in results)
    col_time = len("Median (s)")
    sep = f"+-{'-' * col_op}-+-{'-' * col_time}-+"
    header = f"| {'Operation':<{col_op}} | {'Median (s)':>{col_time}} |"

    print(sep)
    print(header)
    print(sep)
    for op, med in results:
        print(f"| {op:<{col_op}} | {med:>{col_time}.4f} |")
    print(sep)

    # Comparison with baseline
    if args.compare:
        baseline = load_baseline(args.compare)
        if baseline:
            print_comparison(results, baseline)
        else:
            print(f"\nWarning: no valid timings found in {args.compare}")


if __name__ == "__main__":
    main()

"""Headless memory profiling script for log_viewer.

Usage: uv run python profile_memory.py <path-to-log-file>

Reports memory usage at each stage of loading.
"""

from __future__ import annotations

import os
import sys
import tracemalloc
from pathlib import Path

import psutil

_PROC = psutil.Process(os.getpid())


def format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def snapshot_top(snapshot: tracemalloc.Snapshot, label: str, limit: int = 15) -> None:
    print(f"\n{'='*60}")
    print(f"  Top allocations — {label}")
    print(f"{'='*60}")
    stats = snapshot.statistics("lineno")
    total = sum(s.size for s in stats)
    print(f"  Total: {format_bytes(total)}\n")
    for stat in stats[:limit]:
        print(f"  {format_bytes(stat.size):>10}  {stat.traceback}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python profile_memory.py <path-to-log-file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    file_size = Path(file_path).stat().st_size
    print(f"File: {file_path}")
    print(f"Size on disk: {format_bytes(file_size)}")
    print(f"Process RSS before loading: {format_bytes(_PROC.memory_info().rss)}")

    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    # Stage 1: Read file into string + split
    print("\n--- Stage 1: read_text + split ---")
    raw_text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    print(f"  raw_text: {format_bytes(sys.getsizeof(raw_text))}")
    lines = raw_text.split("\n")
    del raw_text  # free the big string
    print(f"  lines count: {len(lines):,}")
    lines_list_size = sum(sys.getsizeof(line) for line in lines[:1000]) * (len(lines) / 1000) if lines else 0
    print(f"  lines estimated size: {format_bytes(lines_list_size)}")
    print(f"  RSS after split: {format_bytes(_PROC.memory_info().rss)}")
    snap_after_read = tracemalloc.take_snapshot()
    snapshot_top(snap_after_read, "After read_text + split")

    # Stage 2: Parse into LogLine objects
    print("\n--- Stage 2: Parse lines ---")
    from log_viewer.core.parser import detect_format, parse_line, parse_plain_line
    from log_viewer.core.models import LogFormat

    fmt = detect_format(lines)
    parser = parse_plain_line if fmt == LogFormat.PLAIN else parse_line
    print(f"  Format: {fmt.value}")

    # Compute offsets (same as LogStore.load_lines)
    offsets: list[tuple[int, int]] = []
    offset = 0
    for raw in lines:
        line_bytes = raw.encode("utf-8")
        offsets.append((offset, len(line_bytes)))
        offset += len(line_bytes) + 1

    parsed: list = []
    for i, raw in enumerate(lines):
        parsed.append(parser(raw, i + 1, offsets[i][0], offsets[i][1]))

    print(f"  Parsed lines: {len(parsed):,}")
    print(f"  RSS after parsing: {format_bytes(_PROC.memory_info().rss)}")

    # Sample LogLine memory
    sample = parsed[:1]
    for ll in sample:
        ll_size = sys.getsizeof(ll)
        msg_size = sys.getsizeof(ll.message)
        ts_size = sys.getsizeof(ll.timestamp)
        cat_size = sys.getsizeof(ll.category)
        print(f"  Sample LogLine overhead: {format_bytes(ll_size)}")
        print(f"    .message: {format_bytes(msg_size)} ({len(ll.message)} chars)")
        print(f"    .timestamp: {format_bytes(ts_size)}")
        print(f"    .category: {format_bytes(cat_size)}")

    snap_after_parse = tracemalloc.take_snapshot()
    snapshot_top(snap_after_parse, "After parsing into LogLine objects")

    # Stage 3: LogStore (with indices, category tree, etc.)
    print("\n--- Stage 3: LogStore.load_lines ---")
    from log_viewer.core.log_store import LogStore

    del parsed, offsets  # free the manually-parsed data
    store = LogStore()
    store.load_lines(lines, file_path=file_path)

    print(f"  Total lines: {len(store.lines):,}")
    print(f"  Filtered indices: {len(store.filtered_indices):,}")
    print(f"  Categories: {len(store.category_counts)}")
    print(f"  RSS after LogStore: {format_bytes(_PROC.memory_info().rss)}")

    snap_after_store = tracemalloc.take_snapshot()
    snapshot_top(snap_after_store, "After LogStore.load_lines")

    # Stage 4: Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  File on disk:        {format_bytes(file_size)}")
    print(f"  Final RSS:           {format_bytes(_PROC.memory_info().rss)}")
    print(f"  Multiplier:          {_PROC.memory_info().rss / file_size:.1f}x")
    print()

    # Diff: read vs baseline
    print("  Memory delta by stage:")
    for label, snap in [
        ("After read+split", snap_after_read),
        ("After parse", snap_after_parse),
        ("After LogStore", snap_after_store),
    ]:
        total = sum(s.size for s in snap.statistics("lineno"))
        baseline = sum(s.size for s in snap_before.statistics("lineno"))
        print(f"    {label:25s}  +{format_bytes(total - baseline)}")

    # Per-field breakdown across all LogLines (full scan)
    print("\n  Per-field estimate (full scan):")
    msg_total = sum(sys.getsizeof(ll.message) for ll in store.lines)
    ts_total = sum(sys.getsizeof(ll.timestamp) for ll in store.lines)
    cat_total = sum(sys.getsizeof(ll.category) for ll in store.lines)
    obj_total = sum(sys.getsizeof(ll) for ll in store.lines)
    print(f"    .message:        {format_bytes(msg_total)}")
    print(f"    .timestamp:      {format_bytes(ts_total)}")
    print(f"    .category:       {format_bytes(cat_total)}")
    print(f"    dataclass shell: {format_bytes(obj_total)}")
    print(f"    TOTAL LogLines:  {format_bytes(obj_total + msg_total + ts_total + cat_total)}")

    tracemalloc.stop()


if __name__ == "__main__":
    main()

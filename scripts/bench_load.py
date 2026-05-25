"""Benchmark log file loading pipeline.

Profiles each stage: file read, line scanning, format detection,
batch parsing, category tree building, and filter application.
Runs WITHOUT tracemalloc during timed sections to avoid overhead.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add src to path so we can import log_viewer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np


def bench_load(path: str) -> None:
    file_path = Path(path)
    print(f"=== Benchmark: {file_path.name} ===")
    print(f"File size: {file_path.stat().st_size / 1024 / 1024:.1f} MB")
    print()

    # --- Stage 1: File read ---
    t0 = time.perf_counter()
    raw_bytes = file_path.read_bytes()
    buf = bytearray(raw_bytes)
    del raw_bytes
    t1 = time.perf_counter()
    print(f"[1] File read + bytearray:  {t1 - t0:.3f}s")

    # --- Stage 2: Scan line starts ---
    from log_viewer.core.parser import scan_line_starts_fast
    t2 = time.perf_counter()
    line_starts = scan_line_starts_fast(buf)
    t3 = time.perf_counter()
    n_lines = len(line_starts) - 1
    print(f"[2] Scan line starts:       {t3 - t2:.3f}s  ({n_lines:,} lines)")

    # --- Stage 3: Format detection ---
    from log_viewer.core.parser import detect_format_bytes
    t4 = time.perf_counter()
    fmt = detect_format_bytes(bytes(buf[:4096]))
    t5 = time.perf_counter()
    print(f"[3] Format detection:       {t5 - t4:.6f}s  (format: {fmt})")

    # --- Stage 4: Batch parse (no tracemalloc) ---
    from log_viewer.core.parser import parse_batch_fast
    t6 = time.perf_counter()
    ts_spans, cat_names, cat_name_to_id, cat_ids, levels, msg_spans = parse_batch_fast(
        buf, line_starts, fmt
    )
    t7 = time.perf_counter()
    print(f"[4] Batch parse:            {t7 - t6:.3f}s")

    # --- Stage 5: Category tree build ---
    from log_viewer.core.log_store import LogStore
    store = LogStore()
    store._buf = buf
    store.line_starts = line_starts
    store.n = n_lines
    store.timestamp_spans = ts_spans
    store.category_ids = cat_ids
    store.levels = levels
    store.message_spans = msg_spans
    store._category_names = cat_names
    store._category_name_to_id = cat_name_to_id

    t8 = time.perf_counter()
    store._build_category_tree()
    t9 = time.perf_counter()
    print(f"[5] Build category tree:    {t9 - t8:.3f}s  ({len(cat_names)} categories)")

    # --- Stage 6: Count levels ---
    t10 = time.perf_counter()
    store._count_levels()
    t11 = time.perf_counter()
    print(f"[6] Count levels:           {t11 - t10:.3f}s")

    # --- Stage 7: Apply filters (no filters) ---
    t12 = time.perf_counter()
    store._apply_filters()
    t13 = time.perf_counter()
    print(f"[7] Apply filters (none):   {t13 - t12:.3f}s  ({len(store.filtered_indices):,} visible)")

    # --- Summary ---
    total = t13 - t0
    print()
    print(f"Total pipeline:            {total:.3f}s")
    print()

    # --- Memory breakdown (measured after the fact, no tracemalloc) ---
    buf_size = len(store._buf)
    arrays_size = (
        store.line_starts.nbytes + store.category_ids.nbytes +
        store.levels.nbytes + store.message_spans.nbytes +
        store.timestamp_spans.nbytes + store.filtered_indices.nbytes
    )
    print(f"Buffer:                    {buf_size / 1024 / 1024:.1f} MB")
    print(f"Numpy arrays:              {arrays_size / 1024 / 1024:.1f} MB")
    print(f"  line_starts:             {store.line_starts.nbytes / 1024 / 1024:.1f} MB")
    print(f"  category_ids:            {store.category_ids.nbytes / 1024 / 1024:.1f} MB")
    print(f"  levels:                  {store.levels.nbytes / 1024 / 1024:.1f} MB")
    print(f"  message_spans:           {store.message_spans.nbytes / 1024 / 1024:.1f} MB")
    print(f"  timestamp_spans:         {store.timestamp_spans.nbytes / 1024 / 1024:.1f} MB")
    print(f"  filtered_indices:        {store.filtered_indices.nbytes / 1024 / 1024:.1f} MB")
    print(f"Total data:                {(buf_size + arrays_size) / 1024 / 1024:.1f} MB")
    print(f"Overhead ratio:            {(buf_size + arrays_size) / file_path.stat().st_size:.2f}x file size")

    # --- RSS via OS ---
    import psutil
    proc = psutil.Process(os.getpid())
    print(f"Process RSS:               {proc.memory_info().rss / 1024 / 1024:.1f} MB")

    # --- Level distribution ---
    print()
    print("Level distribution:")
    for level, count in sorted(store.level_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / n_lines * 100
        print(f"  {level.name:10s}: {count:>10,} ({pct:5.1f}%)")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"d:\log.txt"
    bench_load(target)

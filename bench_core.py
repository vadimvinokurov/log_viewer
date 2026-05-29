"""Benchmark core user actions on ~/log.txt (~6.4M lines)."""

from __future__ import annotations

import time
from pathlib import Path

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, Highlight, SearchMode


def bench(label: str, fn, warmup: int = 0, repeats: int = 3) -> list[float]:
    """Run fn multiple times, return [best] ms."""
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    best = min(times)
    avg = sum(times) / len(times)
    print(f"  {label:50s}  best={best:8.1f} ms  avg={avg:8.1f} ms")
    return times


def main() -> None:
    log_path = Path.home() / "log.txt"
    buf = bytearray(log_path.read_bytes())
    print(f"File: {log_path}  size={len(buf)/1024/1024:.1f} MB\n")

    # --- 1. File loading (full pipeline) ---
    print("=== 1. File loading ===")
    store = LogStore()

    def load_file():
        store.load_bytes(bytearray(buf), str(log_path))

    bench("load_bytes (parse + build indices)", load_file, repeats=3)
    print(f"  lines: {store.n:,}  categories: {len(store._category_names)}")
    print()

    # Pick a category that exists for testing
    cat_names = list(store.category_counts.keys())
    top_cats = sorted(cat_names, key=lambda c: store.category_counts[c], reverse=True)
    big_cat = top_cats[0]          # largest category
    small_cat = top_cats[len(top_cats)//2]  # mid-size
    print(f"  big_cat:  {big_cat!r}  ({store.category_counts[big_cat]:,} lines)")
    print(f"  small_cat: {small_cat!r}  ({store.category_counts[small_cat]:,} lines)")
    print()

    # --- 2. Category enable/disable ---
    print("=== 2. Category toggle ===")

    bench(
        f"disable_category({big_cat!r})",
        lambda: store.disable_category(big_cat),
    )
    bench(
        f"enable_category({big_cat!r})",
        lambda: store.enable_category(big_cat),
    )
    bench(
        f"disable_category({small_cat!r})",
        lambda: store.disable_category(small_cat),
    )
    bench(
        f"enable_category({small_cat!r})",
        lambda: store.enable_category(small_cat),
    )
    bench(
        "disable_all_categories",
        lambda: store.disable_all_categories(),
    )
    bench(
        "enable_all_categories",
        lambda: store.enable_all_categories(),
    )
    print()

    # --- 3. Filter: apply / toggle ---
    print("=== 3. Filter apply + toggle ===")
    store.enable_all_categories()

    # Pick a pattern that actually exists in the file
    sample_msg = store.get_raw(0)
    sample_word = sample_msg.split()[3] if len(sample_msg.split()) > 3 else "cfg"

    filt_common = Filter(pattern=sample_word, mode=SearchMode.PLAIN)
    filt_rare = Filter(pattern="ZZZ_NONEXISTENT_PATTERN_12345", mode=SearchMode.PLAIN)

    bench(
        f"add_filter(PLAIN, {sample_word!r})",
        lambda: store.add_filter(filt_common),
    )
    print(f"  visible after filter: {len(store.filtered_indices):,}")

    # Toggle filter off/on
    bench(
        "filter_enabled=[False] + apply",
        lambda: setattr(store.pipeline, "filter_enabled", [False]) or store._apply_filters(),
    )
    bench(
        "filter_enabled=[True] + apply",
        lambda: setattr(store.pipeline, "filter_enabled", [True]) or store._apply_filters(),
    )

    # Remove filter
    bench(
        f"remove_filter({sample_word!r})",
        lambda: store.remove_filter(sample_word),
    )
    print()

    # --- 4. Pin: apply / toggle ---
    print("=== 4. Pin apply + toggle ===")
    pin_filt = Filter(pattern=sample_word, mode=SearchMode.PLAIN)

    bench(
        f"add_pin(PLAIN, {sample_word!r})",
        lambda: store.add_pin(pin_filt),
    )
    print(f"  visible after pin: {len(store.filtered_indices):,}")

    bench(
        "pinned_enabled=[False] + apply",
        lambda: setattr(store.pipeline, "pinned_enabled", [False]) or store._apply_filters(),
    )
    bench(
        "pinned_enabled=[True] + apply",
        lambda: setattr(store.pipeline, "pinned_enabled", [True]) or store._apply_filters(),
    )
    def remove_pin_0():
        store.remove_pin(0)
        store.add_pin(Filter(pattern=sample_word, mode=SearchMode.PLAIN))
        store.pipeline.pinned_enabled[0] = True

    bench("remove_pin(0) + re-add", remove_pin_0)
    store.pipeline.pinned_rules.clear()
    store.pipeline.pinned_enabled.clear()
    store.pipeline._pin_masks.clear()
    print()

    # --- 5. Highlight toggle ---
    print("=== 5. Highlight apply + toggle ===")

    hl_state = {"hl": Highlight(pattern=sample_word, mode=SearchMode.PLAIN)}

    bench(
        f"add_highlight(PLAIN, {sample_word!r})",
        lambda: store.add_highlight(hl_state["hl"]),
    )

    def remove_hl():
        h = hl_state["hl"]
        store.remove_highlight(sample_word, h.color)
        hl_state["hl"] = Highlight(pattern=sample_word, mode=SearchMode.PLAIN)
        store.add_highlight(hl_state["hl"])

    bench("remove_highlight + re-add", remove_hl)
    print()

    # --- 6. Category toggle WITH active filter ---
    print("=== 6. Category toggle with active filter ===")
    store.add_filter(Filter(pattern=sample_word, mode=SearchMode.PLAIN))
    print(f"  active filter: {sample_word!r}  visible: {len(store.filtered_indices):,}")

    bench(
        f"disable_category({big_cat!r}) [filter active]",
        lambda: store.disable_category(big_cat),
    )
    bench(
        f"enable_category({big_cat!r}) [filter active]",
        lambda: store.enable_category(big_cat),
    )
    bench(
        "disable_all_categories [filter active]",
        lambda: store.disable_all_categories(),
    )
    bench(
        "enable_all_categories [filter active]",
        lambda: store.enable_all_categories(),
    )
    print()

    # --- 7. First _buf_lower creation (lazy init cost) ---
    print("=== 7. Lazy buffer init (_buf_lower) ===")
    store2 = LogStore()
    store2.load_bytes(bytearray(buf), str(log_path))

    bench(
        "first filter (triggers _buf_lower creation)",
        lambda: store2.add_filter(Filter(pattern="cfg", mode=SearchMode.PLAIN)),
    )
    buf_lower_mb = len(store2._buf_lower) / 1024 / 1024 if store2._buf_lower else 0
    print(f"  _buf_lower size: {buf_lower_mb:.1f} MB")
    bench(
        "second filter (_buf_lower cached)",
        lambda: store2.add_filter(Filter(pattern="wrn", mode=SearchMode.PLAIN)),
    )


if __name__ == "__main__":
    main()

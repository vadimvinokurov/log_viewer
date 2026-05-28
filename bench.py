"""Benchmark core operations on a real log file."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure project src is importable
sys.path.insert(0, str(Path(__file__).parent / "src"))

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import Filter, SearchMode

LOG_FILE = Path("~/log.txt").expanduser()
ITERATIONS = 5  # repeat each bench this many times, take median


def bench(label: str, fn, iterations: int = ITERATIONS) -> float:
    """Run fn() multiple times, return median seconds."""
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    times.sort()
    median = times[len(times) // 2]
    return median


def fmt(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f} µs"
    if seconds < 1:
        return f"{seconds * 1_000:.1f} ms"
    return f"{seconds:.2f} s"


def main() -> None:
    results: list[tuple[str, str]] = []

    # --- 1. File loading ---
    print("1/8  File loading ...", flush=True)
    store = LogStore()

    def load():
        buf = bytearray(LOG_FILE.read_bytes())
        store.load_bytes(buf, file_path=str(LOG_FILE))

    t = bench("File loading", load, iterations=3)
    results.append(("File loading", fmt(t)))
    print(f"     {fmt(t)}  ({store.n:,} lines, {len(store._category_names)} categories)")

    # Grab some real data for use in later benches
    all_cats = list(store.category_counts.keys())
    mid_cat = all_cats[len(all_cats) // 2] if all_cats else "cfg"
    popular_cat = max(store.category_counts, key=store.category_counts.get)

    # Find a filter that actually matches something
    sample_msg = store.get_message(0)
    sample_word = sample_msg.split()[0] if sample_msg else "error"
    # Use a common word from messages
    from collections import Counter
    words = Counter()
    for i in range(min(1000, store.n)):
        msg = store.get_message(i)
        for w in msg.split():
            if len(w) > 4:
                words[w] += 1
    common_word = words.most_common(1)[0][0] if words else "error"

    # --- 2. Category disable ---
    print("2/8  Category disable ...", flush=True)

    def cat_disable():
        store.disable_category(mid_cat)

    t = bench("Category disable", cat_disable)
    results.append(("Category disable (1)", fmt(t)))

    # --- 3. Category enable ---
    print("3/8  Category enable ...", flush=True)

    def cat_enable():
        store.enable_category(mid_cat)

    t = bench("Category enable", cat_enable)
    results.append(("Category enable (1)", fmt(t)))

    # --- 4. Disable all categories ---
    print("4/8  Disable all categories ...", flush=True)

    def cat_disable_all():
        store.disable_all_categories()
    t = bench("Disable all categories", cat_disable_all)
    results.append(("Disable all categories", fmt(t)))

    # Restore
    store.enable_all_categories()

    # --- 5. Add filter ---
    print("5/8  Add filter ...", flush=True)

    def add_filter():
        store.add_filter(Filter(pattern=common_word, mode=SearchMode.PLAIN))

    t = bench("Add filter (plain)", add_filter)
    results.append(("Add filter (plain)", fmt(t)))
    matched = len(store.filtered_indices)
    print(f"     matched {matched:,} / {store.n:,} lines")

    # --- 6. Toggle filter off ---
    print("6/8  Toggle filter off ...", flush=True)

    def toggle_filter_off():
        store.filter_enabled[0] = False
        store._apply_filters()

    t = bench("Toggle filter off", toggle_filter_off)
    results.append(("Toggle filter off", fmt(t)))

    # --- 7. Toggle filter on ---
    print("7/8  Toggle filter on ...", flush=True)

    def toggle_filter_on():
        store.filter_enabled[0] = True
        store._apply_filters()

    t = bench("Toggle filter on", toggle_filter_on)
    results.append(("Toggle filter on", fmt(t)))

    # --- 8. Category toggle WITH active filter ---
    print("8/8  Category toggle (filter active) ...", flush=True)

    def cat_toggle_with_filter():
        store.disable_category(popular_cat)
        store.enable_category(popular_cat)

    t = bench("Cat toggle (filter active)", cat_toggle_with_filter)
    results.append(("Cat toggle with active filter", fmt(t)))

    # --- Bonus: Pin operations ---
    print("\n--- Bonus: Pin operations ---", flush=True)

    # Add a pin
    def add_pin():
        store.add_pin(Filter(pattern=common_word, mode=SearchMode.PLAIN))

    t = bench("Add pin (plain)", add_pin)
    results.append(("Add pin (plain)", fmt(t)))

    # Toggle pin off
    def toggle_pin_off():
        store.pinned_enabled[0] = False
        store._apply_filters()

    t = bench("Toggle pin off", toggle_pin_off)
    results.append(("Toggle pin off", fmt(t)))

    # Toggle pin on
    def toggle_pin_on():
        store.pinned_enabled[0] = True
        store._apply_filters()

    t = bench("Toggle pin on", toggle_pin_on)
    results.append(("Toggle pin on", fmt(t)))

    # --- Bonus: Search ---
    print("\n--- Bonus: Search ---", flush=True)

    def do_search():
        store.search(common_word, SearchMode.PLAIN, start_line=0)

    t = bench("Search (plain)", do_search)
    results.append(("Search (plain)", fmt(t)))
    ss = store.search_state
    print(f"     {len(ss.matches):,} matches")

    def search_next():
        store.next_match()

    t = bench("Search next match", search_next, iterations=100)
    results.append(("Search next match", fmt(t)))

    # --- Bonus: Regex filter ---
    print("\n--- Bonus: Regex filter ---", flush=True)

    store.clear_filters()

    def add_regex_filter():
        store.add_filter(Filter(pattern=r"error|warning|fail", mode=SearchMode.REGEX))

    t = bench("Add filter (regex)", add_regex_filter)
    results.append(("Add filter (regex)", fmt(t)))

    # --- Bonus: Simple query ---
    store.clear_filters()

    def add_simple_filter():
        store.add_filter(Filter(pattern=f'"{common_word}" AND NOT "test"', mode=SearchMode.SIMPLE))

    t = bench("Add filter (simple)", add_simple_filter)
    results.append(("Add filter (simple)", fmt(t)))

    # --- Print table ---
    store.clear_filters()
    store.enable_all_categories()

    print("\n")
    print("=" * 70)
    print(f"  BENCHMARK RESULTS  ({store.n:,} lines, {LOG_FILE.stat().st_size / 1e6:.0f} MB)")
    print("=" * 70)
    print(f"  {'Operation':<35} {'Median time':>15}")
    print("-" * 70)
    for label, val in results:
        print(f"  {label:<35} {val:>15}")
    print("=" * 70)


if __name__ == "__main__":
    main()

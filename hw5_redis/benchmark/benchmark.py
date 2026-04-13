"""
Benchmark: compare response times with and without Redis cache.

Usage:
    python benchmark.py [--host http://localhost:8000] [--runs 10]
"""
import argparse
import time
import statistics
import requests

ENDPOINTS = [
    ("Campaign Performance",    "/campaign/166/performance"),
    ("Advertiser Spending",     "/advertiser/3/spending"),
    ("User Engagements",        "/user/583398/engagements"),
]


def flush_cache(host: str):
    """Call each endpoint once and then ask Redis to flush — done via
    a direct redis-cli call is cleaner, but we simulate MISS by measuring
    the first hit and HIT by measuring subsequent hits."""
    pass


def measure(url: str, runs: int) -> tuple[list[float], list[float]]:
    miss_times = []
    hit_times  = []

    for i in range(runs):
        start = time.perf_counter()
        r = requests.get(url, timeout=200)
        elapsed = (time.perf_counter() - start) * 1000   # ms
        r.raise_for_status()
        body = r.json()

        if body.get("cache") == "MISS":
            miss_times.append(elapsed)
        else:
            hit_times.append(elapsed)

    return miss_times, hit_times


def fmt(times: list[float]) -> str:
    if not times:
        return "  n/a"
    return (f"  avg={statistics.mean(times):.1f}ms  "
            f"min={min(times):.1f}ms  "
            f"max={max(times):.1f}ms  "
            f"n={len(times)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--runs", type=int, default=15)
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  AdTech API Benchmark  |  {args.runs} requests per endpoint")
    print(f"  Host: {args.host}")
    print(f"{'='*65}\n")

    summary_rows = []

    for name, path in ENDPOINTS:
        url = args.host + path
        print(f"► {name}  ({url})")

        miss_times, hit_times = measure(url, args.runs)

        print(f"  MISS (cold / DB){fmt(miss_times)}")
        print(f"  HIT  (cached)   {fmt(hit_times)}\n")

        avg_miss = statistics.mean(miss_times) if miss_times else None
        avg_hit  = statistics.mean(hit_times)  if hit_times  else None
        speedup  = f"{avg_miss/avg_hit:.1f}x" if (avg_miss and avg_hit) else "n/a"
        summary_rows.append((name, avg_miss, avg_hit, speedup))

    # ── summary table ─────────────────────────────────────────────────────────
    print(f"{'='*65}")
    print(f"  SUMMARY TABLE")
    print(f"{'='*65}")
    header = f"{'Endpoint':<30} {'MISS (ms)':>12} {'HIT (ms)':>12} {'Speedup':>10}"
    print(header)
    print("-" * 65)
    for name, miss, hit, su in summary_rows:
        m = f"{miss:.1f}" if miss else "n/a"
        h = f"{hit:.1f}"  if hit  else "n/a"
        print(f"{name:<30} {m:>12} {h:>12} {su:>10}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()

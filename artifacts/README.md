# Reference Artifacts

This folder contains checked-in reference artifacts for quick repository review.

- `reference_benchmark_results.csv` mirrors the CSV schema written by `scripts/benchmark.py`
- `reference_benchmark_summary.md` mirrors the Markdown summary shape written by `scripts/benchmark.py`

These are illustrative mock-mode reference files, not guaranteed to match a fresh run byte-for-byte.

To generate current artifacts locally:

```bash
make benchmark
make benchmark-local
```

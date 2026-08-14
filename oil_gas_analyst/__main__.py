from __future__ import annotations

import os
from pathlib import Path

from oil_gas_analyst.deps import ROOT, build_deps, download_full_reports
from oil_gas_analyst.retrieve import ingest_samples_and_reports


def main() -> None:
    download_full_reports()
    deps = build_deps(ingest_if_empty=False)
    reset = getattr(deps.retriever, "reset", None)
    if callable(reset):
        reset()
    samples = Path(os.environ.get("SAMPLES_PATH", str(ROOT / "data" / "samples")))
    reports = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports")))
    n = ingest_samples_and_reports(deps.retriever, samples_dir=samples, reports_dir=reports)
    print(f"indexed {n} Chunks")


if __name__ == "__main__":
    main()

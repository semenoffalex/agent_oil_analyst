from __future__ import annotations

from oil_gas_analyst.deps import build_deps, download_full_reports
from oil_gas_analyst.retrieve import ingest_samples_and_reports
from oil_gas_analyst.deps import ROOT
from pathlib import Path
import os


def main() -> None:
    download_full_reports()
    deps = build_deps(ingest_if_empty=True)
    samples = Path(os.environ.get("SAMPLES_PATH", str(ROOT / "data" / "samples")))
    reports = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports")))
    n = ingest_samples_and_reports(deps.retriever, samples_dir=samples, reports_dir=reports)
    print(f"indexed {n} Chunks")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from pathlib import Path

from oil_gas_analyst.deps import ROOT, build_deps, download_full_reports
from oil_gas_analyst.retrieve import ensure_index


def main() -> None:
    """CLI entry: download Full Reports and force a Chroma rebuild.

    Example:
        $ python -m oil_gas_analyst
        indexed 142 Chunks
    """
    download_full_reports()
    deps = build_deps(ingest_if_empty=False)
    samples = Path(os.environ.get("SAMPLES_PATH", str(ROOT / "data" / "samples")))
    reports = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports")))
    n = ensure_index(deps.retriever, samples_dir=samples, reports_dir=reports, force=True)
    print(f"indexed {n} Chunks")


if __name__ == "__main__":
    main()

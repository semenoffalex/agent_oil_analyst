from oil_gas_analyst.ingest import chunk_pages, load_ingest_config


def test_heading_split_assigns_world_oil_demand():
    cfg = load_ingest_config()
    pages = [
        (41, "Cover and table of contents\nOPEC MOMR"),
        (
            42,
            "World Oil Demand\nThe global oil demand growth forecast for 2026 remains at a healthy 1.4 mb/d, y-o-y.",
        ),
        (43, "OECD demand rose. Non-OECD demand rose."),
    ]
    chunks = chunk_pages(
        pages,
        title="OPEC Monthly Oil Market Report — March 2026 (excerpt, World Oil Demand)",
        date="2026-03",
        excerpt=True,
        agency="OPEC",
        config=cfg,
        token_count=lambda text: len(text.split()),
        url="https://www.opec.org/assets/assetdb/momr-march-2026.pdf",
    )
    headings = [c.heading for c in chunks]
    assert any("World Oil Demand" in h for h in headings)
    demand = next(c for c in chunks if "World Oil Demand" in c.heading)
    assert demand.page_start == 42
    assert demand.excerpt is True
    assert "1.4 mb/d" in demand.text
    assert demand.agency == "OPEC"
    assert demand.date == "2026-03"
    assert demand.url == "https://www.opec.org/assets/assetdb/momr-march-2026.pdf"


def test_sample_momr_pdf_yields_demand_chunk():
    from pathlib import Path

    from oil_gas_analyst.ingest import chunk_pdf

    pdf = Path("data/samples/momr-june-2026.pdf")
    chunks = chunk_pdf(pdf, agency="OPEC", excerpt=False, date="2026-06", title="OPEC MOMR June 2026")
    assert chunks
    assert any("Demand" in c.heading or "demand" in c.text.lower() for c in chunks)
    assert all(c.page_start is not None for c in chunks)
    assert all(c.agency == "OPEC" for c in chunks)
    assert all(c.date == "2026-06" for c in chunks)


def test_sample_cbr_pdf_keeps_oil_mention_and_bulletin_heading():
    from pathlib import Path

    from oil_gas_analyst.ingest import chunk_pdf

    pdf = Path("data/samples/cbr_ec_research_mb_bulletin_26-05.pdf")
    chunks = chunk_pdf(
        pdf,
        agency="CBR",
        excerpt=False,
        date="2026-07",
        title="Банк России — О чем говорят тренды № 5 (88), июль 2026",
    )
    assert chunks
    assert all(c.agency == "CBR" for c in chunks)
    assert all(c.date == "2026-07" for c in chunks)
    assert any("О чем говорят тренды" in c.heading for c in chunks)
    blob = " ".join(c.text.lower() for c in chunks)
    assert "нефтян" in blob


def test_cbr_heading_split_assigns_oil_section():
    cfg = load_ingest_config()
    pages = [
        (1, "О чем говорят тренды\nМакрообзор Банка России."),
        (2, "Нефть\nИюньская деэскалация вызвала коррекцию вниз нефтяных цен."),
    ]
    chunks = chunk_pages(
        pages,
        title="Банк России — О чем говорят тренды",
        date="2026-07",
        excerpt=False,
        agency="CBR",
        config=cfg,
        token_count=lambda text: len(text.split()),
        url="https://www.cbr.ru/analytics/dkp/ddb/",
    )
    oil = next(c for c in chunks if c.heading == "Нефть")
    assert "нефтяных цен" in oil.text
    assert oil.agency == "CBR"
    assert oil.page_start == 2


def test_drop_redundant_excerpts_skips_steo_excerpt_when_full_listed():
    from oil_gas_analyst.retrieve import drop_redundant_excerpts

    kept = drop_redundant_excerpts(
        [
            {
                "path": "data/samples/eia-steo-excerpt.pdf",
                "agency": "EIA",
                "date": "2026-08",
                "excerpt": True,
            },
            {
                "path": "data/samples/steo_full.pdf",
                "agency": "EIA",
                "date": "2026-08",
                "excerpt": False,
            },
            {
                "path": "data/samples/momr-june-2026.pdf",
                "agency": "OPEC",
                "date": "2026-06",
                "excerpt": False,
            },
        ]
    )
    paths = [sample["path"] for sample in kept]
    assert "data/samples/eia-steo-excerpt.pdf" not in paths
    assert "data/samples/steo_full.pdf" in paths
    assert "data/samples/momr-june-2026.pdf" in paths


def test_drop_redundant_excerpts_keeps_excerpt_without_full():
    from oil_gas_analyst.retrieve import drop_redundant_excerpts

    kept = drop_redundant_excerpts(
        [
            {
                "path": "data/samples/eia-steo-excerpt.pdf",
                "agency": "EIA",
                "date": "2026-08",
                "excerpt": True,
            }
        ]
    )
    assert len(kept) == 1
    assert kept[0]["excerpt"] is True


def test_corpus_fingerprint_omits_steo_excerpt_when_full_exists():
    from pathlib import Path

    from oil_gas_analyst.retrieve import corpus_fingerprint, iter_ingest_jobs

    samples = Path("data/samples")
    reports = Path("data/reports")
    names = [job["path"].name for job in iter_ingest_jobs(samples, reports)]
    assert "eia-steo-excerpt.pdf" not in names
    assert "steo_full.pdf" in names
    fp = corpus_fingerprint(samples, reports)
    assert len(fp) == 64
    assert fp == corpus_fingerprint(samples, reports)


def test_ensure_index_rebuilds_stale_volume_then_skips(monkeypatch):
    from pathlib import Path

    from oil_gas_analyst.retrieve import ensure_index

    ingest_calls: list[str] = []

    class Fake:
        def __init__(self):
            self._empty = False
            self.fp = None
            self.resets = 0

        def is_empty(self) -> bool:
            return self._empty

        def reset(self) -> None:
            self.resets += 1
            self._empty = True

        def stored_fingerprint(self) -> str | None:
            return self.fp

        def write_fingerprint(self, fp: str) -> None:
            self.fp = fp
            self._empty = False

    def fake_ingest(retriever, *, samples_dir, reports_dir):
        ingest_calls.append("ingest")
        retriever._empty = False
        return 1

    monkeypatch.setattr("oil_gas_analyst.retrieve.ingest_samples_and_reports", fake_ingest)
    monkeypatch.setattr("oil_gas_analyst.retrieve.corpus_fingerprint", lambda *a, **k: "abc")
    fake = Fake()
    samples = Path("data/samples")
    reports = Path("data/reports")
    ensure_index(fake, samples_dir=samples, reports_dir=reports)
    assert fake.resets == 1
    assert ingest_calls == ["ingest"]
    assert fake.fp == "abc"
    ensure_index(fake, samples_dir=samples, reports_dir=reports)
    assert fake.resets == 1
    assert ingest_calls == ["ingest"]


def test_ensure_index_force_rebuilds_matching_fingerprint(monkeypatch):
    from pathlib import Path

    from oil_gas_analyst.retrieve import ensure_index

    ingest_calls = []

    class Fake:
        def __init__(self):
            self._empty = False
            self.fp = "abc"
            self.resets = 0

        def is_empty(self) -> bool:
            return self._empty

        def reset(self) -> None:
            self.resets += 1
            self._empty = True

        def stored_fingerprint(self) -> str | None:
            return self.fp

        def write_fingerprint(self, fp: str) -> None:
            self.fp = fp
            self._empty = False

    monkeypatch.setattr(
        "oil_gas_analyst.retrieve.ingest_samples_and_reports",
        lambda *a, **k: ingest_calls.append(1) or 1,
    )
    monkeypatch.setattr("oil_gas_analyst.retrieve.corpus_fingerprint", lambda *a, **k: "abc")
    fake = Fake()
    ensure_index(
        fake,
        samples_dir=Path("data/samples"),
        reports_dir=Path("data/reports"),
        force=True,
    )
    assert fake.resets == 1
    assert ingest_calls == [1]


def test_e5_token_count_is_whitespace_without_transformers():
    from oil_gas_analyst.ingest import e5_token_count

    assert e5_token_count("one two three") == 3


def test_make_embedding_function_uses_openrouter_nemotron(monkeypatch):
    from oil_gas_analyst.retrieve import (
        OpenAICompatibleEmbeddingFunction,
        make_embedding_function,
    )

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_BASE_URL", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    fn = make_embedding_function()
    assert isinstance(fn, OpenAICompatibleEmbeddingFunction)
    assert "/api/v1/embeddings" in fn._url
    assert fn._model == "nvidia/nemotron-3-embed-1b:free"
    assert fn._api_key == "sk-or-test"
    assert fn._e5_prefixes is False
    assert fn._nemotron_input_type is True


def test_make_embedding_function_raises_without_key(monkeypatch):
    from oil_gas_analyst.retrieve import make_embedding_function

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    try:
        make_embedding_function()
    except RuntimeError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_missing_sample_report_breaks_ingest(tmp_path):
    from oil_gas_analyst.retrieve import iter_ingest_jobs

    cfg = {
        "samples": [
            {
                "path": str(tmp_path / "missing-momr.pdf"),
                "agency": "OPEC",
                "date": "2026-03",
                "excerpt": True,
                "title": "missing",
            }
        ]
    }
    try:
        iter_ingest_jobs(tmp_path, tmp_path, cfg)
        raised = False
    except FileNotFoundError as exc:
        raised = True
        assert "Sample Report missing" in str(exc)
    assert raised is True

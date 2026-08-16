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


def test_june_2026_momr_outranks_older_price_chunk():
    from pathlib import Path

    from oil_gas_analyst.ingest import chunk_pdf
    from oil_gas_analyst.retrieve import select_report_chunks
    from oil_gas_analyst.types import Chunk

    pdf = Path("data/samples/momr-june-2026.pdf")
    june_2026 = chunk_pdf(
        pdf, agency="OPEC", excerpt=False, date="2026-06", title="OPEC MOMR June 2026"
    )
    older_price = Chunk(
        text="Brent averaged $83/b in May 2024.",
        title="OPEC Monthly Oil Market Report — June 2024",
        date="2024-06",
        page_start=10,
        page_end=12,
        heading="Crude Oil Price Movements",
        agency="OPEC",
    )
    picked = select_report_chunks(
        "Какой тренд в прогнозах цен на нефть на ближайший месяц?",
        [older_price, *june_2026],
        k=5,
    )
    assert picked
    assert picked[0].date == "2026-06"
    assert picked[0].agency == "OPEC"
    assert "Tanker" not in picked[0].heading


def test_outlook_prefers_newer_price_section_over_tanker():
    from oil_gas_analyst.retrieve import select_report_chunks
    from oil_gas_analyst.types import Chunk

    older_price = Chunk(
        text="Brent averaged $83/b in May 2024.",
        title="OPEC Monthly Oil Market Report — June 2024",
        date="2024-06",
        page_start=10,
        page_end=12,
        heading="Crude Oil Price Movements",
        agency="OPEC",
    )
    newer_tanker = Chunk(
        text="VLCC freight rates rose.",
        title="OPEC Monthly Oil Market Report — June 2026",
        date="2026-06",
        page_start=80,
        page_end=82,
        heading="Tanker Market",
        agency="OPEC",
    )
    newer_price = Chunk(
        text="Brent averaged $78/b in May 2026.",
        title="OPEC Monthly Oil Market Report — June 2026",
        date="2026-06",
        page_start=9,
        page_end=11,
        heading="Crude Oil Price Movements",
        agency="OPEC",
    )
    picked = select_report_chunks(
        "Какой тренд в прогнозах цен на нефть на ближайший месяц?",
        [older_price, newer_tanker, newer_price],
        k=2,
    )
    assert [c.date for c in picked] == ["2026-06", "2024-06"]
    assert picked[0].heading == "Crude Oil Price Movements"
    assert picked[0].text == "Brent averaged $78/b in May 2026."
    assert all("Tanker" not in c.heading for c in picked)


def test_full_report_outranks_same_date_excerpt():
    from oil_gas_analyst.retrieve import select_report_chunks
    from oil_gas_analyst.types import Chunk

    excerpt = Chunk(
        text="Brent averaged $78/b in the excerpt.",
        title="EIA STEO August 2026 (excerpt, Global Oil Markets)",
        date="2026-08",
        page_start=1,
        page_end=2,
        heading="Global oil prices",
        excerpt=True,
        agency="EIA",
    )
    full = Chunk(
        text="Brent averaged $78/b in the full STEO.",
        title="EIA Short-Term Energy Outlook — August 2026",
        date="2026-08",
        page_start=8,
        page_end=12,
        heading="Global oil prices",
        excerpt=False,
        agency="EIA",
    )
    picked = select_report_chunks("What is the EIA oil price outlook?", [excerpt, full], k=1)
    assert len(picked) == 1
    assert picked[0].excerpt is False
    assert "full STEO" in picked[0].text


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


def test_e5_token_count_uses_tokenizer_when_embedding_url_set(monkeypatch):
    import oil_gas_analyst.ingest as ingest

    class Tok:
        def encode(self, text, add_special_tokens=False):
            return [1, 2, 3, 4, 5, 6, 7]

    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://host.docker.internal:1234/v1")
    previous = ingest._E5_TOK
    ingest._E5_TOK = Tok()
    try:
        assert ingest.e5_token_count("one two three") == 7
    finally:
        ingest._E5_TOK = previous


def test_e5_tokenizer_name_prefers_local_model_over_lm_studio_id(monkeypatch):
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://host.docker.internal:1234/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-multilingual-e5-base")
    monkeypatch.setenv("EMBEDDING_LOCAL_MODEL", "/opt/models/multilingual-e5-base")
    from oil_gas_analyst.ingest import e5_tokenizer_name

    assert e5_tokenizer_name() == "/opt/models/multilingual-e5-base"

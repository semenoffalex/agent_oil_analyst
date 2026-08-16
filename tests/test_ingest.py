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

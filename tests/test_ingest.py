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
    )
    headings = [c.heading for c in chunks]
    assert any("World Oil Demand" in h for h in headings)
    demand = next(c for c in chunks if "World Oil Demand" in c.heading)
    assert demand.page_start == 42
    assert demand.excerpt is True
    assert "1.4 mb/d" in demand.text


def test_sample_momr_pdf_yields_demand_chunk():
    from pathlib import Path

    from oil_gas_analyst.ingest import chunk_pdf

    pdf = Path("data/samples/opec-momr-excerpt.pdf")
    chunks = chunk_pdf(pdf, agency="OPEC", excerpt=True, date="2026-03", title="OPEC MOMR excerpt")
    assert chunks
    assert any("Demand" in c.heading or "demand" in c.text.lower() for c in chunks)
    assert all(c.page_start is not None for c in chunks)

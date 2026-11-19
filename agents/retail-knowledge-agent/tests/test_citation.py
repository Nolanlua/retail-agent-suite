from app.retrieval.citation import CitationBuilder


class FakeChunk:
    chunk_id = "c1"
    doc_id = "d1"
    title = "陈列端头执行标准"
    source = "门店运营中心"
    section = "display"
    text = "端头陈列面不少于 3 个。"


def test_citation_builder_and_validator() -> None:
    builder = CitationBuilder()
    context, citations = builder.build([FakeChunk()])
    assert "[1]" in context
    report = builder.validate("端头陈列面不少于 3 个 [1]", citations)
    assert report.valid is True


def test_out_of_range_citation_is_invalid() -> None:
    builder = CitationBuilder()
    _, citations = builder.build([FakeChunk()])
    report = builder.validate("端头陈列面不少于 3 个 [2]", citations)
    assert report.valid is False
    assert report.invalid_indexes == [2]

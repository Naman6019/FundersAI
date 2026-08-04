from app.mf_ingestion.jobs.index_parsed_documents import _build_summary


def test_index_summary_counts_each_checkpointed_document() -> None:
    summary = _build_summary(
        status="running",
        requested_amcs=["hdfc"],
        candidate_pdf_count=5,
        previously_indexed_count=1,
        indexed=[{"document_id": "a"}],
        skipped=[{"document_id": "b"}],
        failures=[{"document_id": "c"}],
    )

    assert summary["processed_document_count"] == 3
    assert summary["available_document_count"] == 2

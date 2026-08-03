from datetime import datetime, timezone

from onecool_os.market.ai_revolution import (
    AIRevolutionError,
    COMPANIES,
    OfficialIRClient,
    SecClient,
    latest_periodic_filing,
    latest_usd_fact,
    refresh_ai_revolution,
    tesla_update_urls,
)


def submissions(accession: str = "0000000000-26-000001") -> dict:
    return {
        "cik": "789019",
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q"],
                "filingDate": ["2026-07-25", "2026-07-24"],
                "reportDate": ["2026-07-25", "2026-06-30"],
                "accessionNumber": ["0000000000-26-000002", accession],
                "primaryDocument": ["eight-k.htm", "ten-q.htm"],
            }
        },
    }


def companyfacts() -> dict:
    return {
        "facts": {
            "us-gaap": {
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            {
                                "start": "2026-01-01",
                                "end": "2026-06-30",
                                "val": 100,
                                "filed": "2026-07-24",
                                "form": "10-Q",
                                "accn": "0000000000-26-000001",
                            }
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            {
                                "start": "2026-01-01",
                                "end": "2026-06-30",
                                "val": 300,
                                "filed": "2026-07-24",
                                "form": "10-Q",
                                "accn": "0000000000-26-000001",
                            }
                        ]
                    }
                },
            }
        }
    }


def test_latest_periodic_filing_ignores_8k() -> None:
    filing = latest_periodic_filing(submissions())
    assert filing["form"] == "10-Q"
    assert filing["report_date"] == "2026-06-30"
    assert filing["source_url"].startswith("https://www.sec.gov/Archives/")


def test_latest_fact_keeps_raw_official_value() -> None:
    fact = latest_usd_fact(
        companyfacts(), ("PaymentsToAcquirePropertyPlantAndEquipment",)
    )
    assert fact["value_usd"] == 100
    assert fact["form"] == "10-Q"


def test_new_filings_force_review_and_block_lights() -> None:
    def request(url: str, _: str) -> dict:
        return submissions() if "submissions" in url else companyfacts()

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=request),
        previous={},
        review={
            "reviewed_accessions": {},
            "signals": {
                "overall": {
                    "status": "GREEN",
                    "reason": "Old review",
                    "reviewed_at": "2026-04-30",
                }
            },
        },
        generated_at="2026-07-28T00:00:00+00:00",
    )

    assert len(payload["companies"]) == len(COMPANIES) == 7
    assert payload["data_coverage_pct"] == 100.0
    assert payload["review_required"] is True
    assert payload["signals"]["overall"]["usable_for_report"] is False


def test_matching_reviewed_accessions_unlock_reviewed_signal() -> None:
    accession = "0000000000-26-000001"

    def request(url: str, _: str) -> dict:
        return submissions(accession) if "submissions" in url else companyfacts()

    review = {
        "reviewed_accessions": {company: accession for company in COMPANIES},
        "signals": {
            "overall": {
                "status": "GREEN",
                "reason": "Seven official filings reviewed.",
                "reviewed_at": "2026-07-28",
            }
        },
    }
    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=request),
        review=review,
    )

    assert payload["review_required"] is False
    assert payload["signals"]["overall"]["usable_for_report"] is True


def test_complete_provider_failure_forces_unknown_review_gate() -> None:
    def request(_: str, __: str) -> dict:
        raise AIRevolutionError("HTTP 403: Forbidden")

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=request)
    )

    assert payload["companies_valid"] == 0
    assert payload["data_coverage_pct"] == 0.0
    assert payload["cache_status"] == "UNKNOWN"
    assert payload["review_required"] is True
    assert payload["unreviewed_companies"] == list(COMPANIES)
    assert all(
        item["refresh_error"] == "AIRevolutionError: HTTP 403: Forbidden"
        for item in payload["companies"]
    )


def test_partial_provider_failure_cannot_unlock_lights() -> None:
    successful_cik = next(iter(COMPANIES.values()))

    def request(url: str, _: str) -> dict:
        if successful_cik not in url:
            raise AIRevolutionError("HTTP 403: Forbidden")
        return submissions() if "submissions" in url else companyfacts()

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=request)
    )

    assert payload["companies_valid"] == 1
    assert payload["cache_status"] == "PARTIAL"
    assert payload["review_required"] is True
    assert payload["signals"]["overall"]["usable_for_report"] is False


def test_transient_failure_keeps_recent_official_revision_valid() -> None:
    previous = {
        "generated_at": "2026-07-31T00:00:00+00:00",
        "companies": [
            {
                "company": company,
                "cik": cik,
                "data_status": "OFFICIAL_IR_AVAILABLE",
                "evidence_revision": f"ir:{company}",
                "official_ir": {"fetched_at": "2026-07-31T00:00:00+00:00"},
            }
            for company, cik in COMPANIES.items()
        ],
    }

    def fail(*_):
        raise AIRevolutionError("temporary provider failure")

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=fail),
        previous=previous,
        ir_client=OfficialIRClient(
            "OnecoolOS test test@example.com", request=fail
        ),
        generated_at="2026-08-03T00:00:00+00:00",
    )

    assert payload["companies_official_evidence_valid"] == 7
    assert payload["official_evidence_coverage_pct"] == 100.0
    assert payload["cache_status"] == "VALID"
    assert {item["data_status"] for item in payload["companies"]} == {
        "LAST_KNOWN_VALID"
    }


def test_official_ir_fallback_tracks_revision_without_inventing_facts() -> None:
    def sec_request(_: str, __: str) -> dict:
        raise AIRevolutionError("HTTP 403: Forbidden")

    def ir_request(url: str, _: str) -> str:
        return (
            "<html><body><h1>Investor relations</h1>"
            f"<p>{url}</p><p>{'official evidence ' * 20}</p></body></html>"
        )

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=sec_request),
        review={},
        ir_client=OfficialIRClient(
            "OnecoolOS test test@example.com", request=ir_request
        ),
        generated_at="2026-07-28T00:00:00+00:00",
    )

    assert payload["companies_valid"] == 7
    assert payload["companies_sec_structured_valid"] == 0
    assert payload["official_evidence_coverage_pct"] == 100.0
    assert payload["cache_status"] == "VALID"
    assert payload["review_required"] is True
    assert all(
        item["data_status"] == "OFFICIAL_IR_AVAILABLE"
        and item["evidence_revision"].startswith("ir:")
        and item["latest_capex_fact"] is None
        for item in payload["companies"]
    )


def test_tesla_tries_alternate_official_ir_endpoint() -> None:
    attempted = []

    def request(url: str, _: str) -> str:
        attempted.append(url)
        if url.endswith("/press"):
            raise AIRevolutionError("HTTP 403: Forbidden")
        return f"<html><body>{url} {'official Tesla evidence ' * 20}</body></html>"

    evidence = OfficialIRClient(
        "OnecoolOS test test@example.com", request=request
    ).fetch_first((
        "https://ir.tesla.com/press",
        (
            "https://ir.tesla.com/press-release/"
            "tesla-releases-second-quarter-2026-financial-results"
        ),
    ))

    assert attempted == [
        "https://ir.tesla.com/press",
        (
            "https://ir.tesla.com/press-release/"
            "tesla-releases-second-quarter-2026-financial-results"
        ),
    ]
    assert "second-quarter-2026" in evidence["source_url"]


def test_tesla_quarterly_pdf_candidates_roll_back_across_year() -> None:
    urls = tesla_update_urls(datetime(2026, 1, 15, tzinfo=timezone.utc))

    assert urls[0].endswith("TSLA-Q1-2026-Update.pdf")
    assert urls[1].endswith("TSLA-Q4-2025-Update.pdf")
    assert urls[-1].endswith("TSLA-Q4-2024-Update.pdf")


def test_tesla_official_urls_include_stable_ir_and_sec_pages() -> None:
    from onecool_os.market.ai_revolution import OFFICIAL_IR_URLS

    assert OFFICIAL_IR_URLS["Tesla"][:2] == (
        "https://ir.tesla.com/",
        "https://ir.tesla.com/sec-filings",
    )


def test_official_ir_client_fingerprints_pdf_bytes() -> None:
    body = b"%PDF-1.7\n" + (b"official Tesla quarterly evidence\n" * 100)
    evidence = OfficialIRClient(
        "OnecoolOS test test@example.com",
        request=lambda _url, _agent: body,
    ).fetch("https://assets-ir.tesla.com/example.pdf")

    assert evidence["content_kind"] == "PDF"
    assert evidence["content_length"] == len(body)


def test_matching_ir_revisions_unlock_only_reviewed_signal() -> None:
    def sec_request(_: str, __: str) -> dict:
        raise AIRevolutionError("HTTP 403: Forbidden")

    def ir_request(url: str, _: str) -> str:
        return f"<html><body>{url} {'evidence ' * 30}</body></html>"

    ir_client = OfficialIRClient(
        "OnecoolOS test test@example.com", request=ir_request
    )
    initial = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=sec_request),
        ir_client=ir_client,
    )
    revisions = {
        item["company"]: item["evidence_revision"] for item in initial["companies"]
    }
    reviewed = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=sec_request),
        review={
            "reviewed_revisions": revisions,
            "signals": {
                "overall": {
                    "status": "GREEN",
                    "reason": "Official evidence reviewed.",
                    "reviewed_at": "2026-07-28",
                }
            },
        },
        ir_client=ir_client,
    )

    assert reviewed["review_required"] is False
    assert reviewed["signals"]["overall"]["usable_for_report"] is True

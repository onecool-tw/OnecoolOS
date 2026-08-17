from onecool_os.market.ai_revolution import (
    AIRevolutionError,
    COMPANIES,
    OfficialIRClient,
    SecClient,
    latest_periodic_filing,
    latest_usd_fact,
    refresh_ai_revolution,
)


def test_committed_six_company_review_baseline_is_reportable() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    review = json.loads(
        (root / "config" / "ai_revolution_review.json").read_text(
            encoding="utf-8"
        )
    )
    cache = json.loads(
        (
            root
            / "data"
            / "market"
            / "ai_revolution"
            / "ai_revolution_latest.json"
        ).read_text(encoding="utf-8")
    )

    revisions = {
        item["company"]: item["evidence_revision"]
        for item in cache["companies"]
    }
    assert set(revisions) == set(COMPANIES)
    assert review["reviewed_revisions"] == revisions
    assert cache["review_required"] is False
    assert cache["unreviewed_companies"] == []
    assert all(
        signal["status"] in {"GREEN", "YELLOW", "RED"}
        and signal["usable_for_report"] is True
        for signal in cache["signals"].values()
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

    assert len(payload["companies"]) == len(COMPANIES) == 6
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
                "reason": "Six official filings reviewed.",
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

    assert payload["companies_official_evidence_valid"] == 6
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

    assert payload["companies_valid"] == 6
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


def test_tesla_is_excluded_from_ai_revolution_universe() -> None:
    from onecool_os.market.ai_revolution import OFFICIAL_IR_URLS

    assert "Tesla" not in COMPANIES
    assert "Tesla" not in OFFICIAL_IR_URLS


def test_official_ir_client_fingerprints_pdf_bytes() -> None:
    body = b"%PDF-1.7\n" + (b"official quarterly evidence\n" * 100)
    evidence = OfficialIRClient(
        "OnecoolOS test test@example.com",
        request=lambda _url, _agent: body,
    ).fetch("https://example.com/official-quarterly-update.pdf")

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


def test_ai_monitor_exposes_demand_quality_and_capital_efficiency() -> None:
    def request(url: str, _: str) -> dict:
        return submissions() if "submissions" in url else companyfacts()

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=request)
    )

    assert set(payload["signals"]) == {
        "ai_infrastructure",
        "ai_capex",
        "ai_adoption",
        "independent_demand_quality",
        "capital_efficiency",
        "overall",
    }
    methodology = payload["signal_methodology"]
    assert "supplier loans" in methodology["independent_demand_quality"]
    assert "Do not double count" in methodology["independent_demand_quality"]
    assert "free cash flow" in methodology["capital_efficiency"]
    assert payload["schema_version"] == "1.3"


def test_complete_review_unlocks_independent_demand_quality() -> None:
    accession = "0000000000-26-000001"

    def request(url: str, _: str) -> dict:
        return submissions(accession) if "submissions" in url else companyfacts()

    payload = refresh_ai_revolution(
        SecClient("OnecoolOS test test@example.com", request=request),
        review={
            "reviewed_accessions": {company: accession for company in COMPANIES},
            "signals": {
                "independent_demand_quality": {
                    "status": "YELLOW",
                    "reason": "Supplier-supported purchases were down-weighted.",
                    "reviewed_at": "2026-08-10",
                },
                "capital_efficiency": {
                    "status": "YELLOW",
                    "reason": "Cash conversion trails gross capex growth.",
                    "reviewed_at": "2026-08-10",
                },
            },
        },
    )

    assert payload["review_required"] is False
    assert (
        payload["signals"]["independent_demand_quality"]["usable_for_report"] is True
    )
    assert payload["signals"]["independent_demand_quality"]["status"] == "YELLOW"
    assert payload["signals"]["capital_efficiency"]["usable_for_report"] is True

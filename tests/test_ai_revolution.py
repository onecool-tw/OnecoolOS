from onecool_os.market.ai_revolution import (
    COMPANIES,
    SecClient,
    latest_periodic_filing,
    latest_usd_fact,
    refresh_ai_revolution,
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

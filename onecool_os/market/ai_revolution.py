"""Official-evidence cache for the Onecool AI Revolution Monitor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.request import Request, urlopen


COMPANIES = {
    "Microsoft": "0000789019",
    "Amazon": "0001018724",
    "Alphabet": "0001652044",
    "Meta": "0001326801",
    "Nvidia": "0001045810",
    "Apple": "0000320193",
    "Tesla": "0001318605",
}

CAPEX_TAGS = (
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsForProceedsFromOtherPropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
)
OPERATING_CASH_FLOW_TAGS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
PERIODIC_FORMS = {"10-Q", "10-K"}


class AIRevolutionError(RuntimeError):
    """Raised when official AI evidence cannot be refreshed safely."""


@dataclass(frozen=True)
class SecClient:
    """Minimal SEC JSON client with an attributable User-Agent."""

    user_agent: str
    request: Callable[[str, str], dict[str, Any]] | None = None

    def fetch_submissions(self, cik: str) -> dict[str, Any]:
        return self._fetch(f"https://data.sec.gov/submissions/CIK{cik}.json")

    def fetch_companyfacts(self, cik: str) -> dict[str, Any]:
        return self._fetch(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        )

    def _fetch(self, url: str) -> dict[str, Any]:
        if self.request:
            return self.request(url, self.user_agent)
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed SEC host.
            return json.loads(response.read())


def latest_periodic_filing(submissions: dict[str, Any]) -> dict[str, Any] | None:
    """Return the most recently filed 10-Q/10-K from SEC submissions."""

    recent = submissions.get("filings", {}).get("recent", {})
    records = []
    for index, form in enumerate(recent.get("form", [])):
        if form not in PERIODIC_FORMS:
            continue
        accession = recent["accessionNumber"][index]
        primary = recent["primaryDocument"][index]
        records.append(
            {
                "form": form,
                "filing_date": recent["filingDate"][index],
                "report_date": recent["reportDate"][index],
                "accession_number": accession,
                "source_url": (
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{int(submissions['cik'])}/{accession.replace('-', '')}/{primary}"
                ),
            }
        )
    return max(records, key=lambda item: item["filing_date"]) if records else None


def latest_usd_fact(
    companyfacts: dict[str, Any], tags: tuple[str, ...]
) -> dict[str, Any] | None:
    """Return the latest filed USD fact without inferring a trend or AI attribution."""

    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    candidates = []
    for tag in tags:
        for fact in us_gaap.get(tag, {}).get("units", {}).get("USD", []):
            if fact.get("form") not in PERIODIC_FORMS or "val" not in fact:
                continue
            candidates.append(
                {
                    "tag": tag,
                    "value_usd": fact["val"],
                    "start": fact.get("start"),
                    "end": fact.get("end"),
                    "filed": fact.get("filed"),
                    "form": fact.get("form"),
                    "accession_number": fact.get("accn"),
                    "frame": fact.get("frame"),
                }
            )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.get("filed") or "",
            item.get("end") or "",
            item.get("start") or "",
        ),
    )


def refresh_ai_revolution(
    client: SecClient,
    previous: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Refresh seven-company SEC evidence and gate stale qualitative signals."""

    previous = previous or {}
    review = review or {}
    previous_companies = {
        item.get("company"): item for item in previous.get("companies", [])
    }
    companies = []
    valid = 0
    changed = []

    for company, cik in COMPANIES.items():
        try:
            submissions = client.fetch_submissions(cik)
            companyfacts = client.fetch_companyfacts(cik)
            filing = latest_periodic_filing(submissions)
            capex = latest_usd_fact(companyfacts, CAPEX_TAGS)
            operating_cash_flow = latest_usd_fact(
                companyfacts, OPERATING_CASH_FLOW_TAGS
            )
            old_accession = (
                previous_companies.get(company, {})
                .get("latest_periodic_filing", {})
                .get("accession_number")
            )
            new_accession = (filing or {}).get("accession_number")
            filing_changed = bool(new_accession and new_accession != old_accession)
            if filing_changed:
                changed.append(company)
            companies.append(
                {
                    "company": company,
                    "cik": cik,
                    "data_status": "VALID",
                    "latest_periodic_filing": filing,
                    "latest_capex_fact": capex,
                    "latest_operating_cash_flow_fact": operating_cash_flow,
                    "filing_changed": filing_changed,
                    "interpretation_policy": (
                        "Raw official evidence only; AI attribution and ROI require review."
                    ),
                }
            )
            valid += 1
        except Exception as exc:  # One issuer must not erase six valid records.
            old = previous_companies.get(company)
            if old:
                companies.append(
                    {
                        **old,
                        "data_status": "STALE",
                        "refresh_error": type(exc).__name__,
                        "filing_changed": False,
                    }
                )
            else:
                companies.append(
                    {
                        "company": company,
                        "cik": cik,
                        "data_status": "UNKNOWN",
                        "latest_periodic_filing": None,
                        "latest_capex_fact": None,
                        "latest_operating_cash_flow_fact": None,
                        "filing_changed": False,
                        "refresh_error": type(exc).__name__,
                    }
                )

    reviewed_accessions = review.get("reviewed_accessions", {})
    unreviewed = [
        item["company"]
        for item in companies
        if (item.get("latest_periodic_filing") or {}).get("accession_number")
        != reviewed_accessions.get(item["company"])
    ]
    review_required = bool(unreviewed)
    reviewed_signals = review.get("signals", {})
    signals = {}
    for name in ("ai_infrastructure", "ai_capex", "ai_adoption", "overall"):
        signal = reviewed_signals.get(name, {})
        signals[name] = {
            "status": signal.get("status", "UNKNOWN"),
            "reason": signal.get(
                "reason", "No complete seven-company official review is available."
            ),
            "reviewed_at": signal.get("reviewed_at"),
            "usable_for_report": not review_required and signal.get("status") != "UNKNOWN",
        }

    generated = generated_at or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "1.0",
        "generated_at": generated,
        "source_policy": "SEC official filings and companyfacts only",
        "companies_expected": len(COMPANIES),
        "companies_valid": valid,
        "data_coverage_pct": round(valid / len(COMPANIES) * 100, 2),
        "review_required": review_required,
        "unreviewed_companies": unreviewed,
        "new_periodic_filings": changed,
        "signals": signals,
        "companies": companies,
        "decision_policy": (
            "Do not output current AI lights unless all latest periodic filings "
            "have been reviewed against official evidence."
        ),
    }

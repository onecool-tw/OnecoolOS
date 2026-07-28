"""Official-evidence cache for the Onecool AI Revolution Monitor."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.error import HTTPError
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

OFFICIAL_IR_URLS = {
    "Microsoft": ("https://www.microsoft.com/en-us/Investor",),
    "Amazon": ("https://ir.aboutamazon.com/quarterly-results/default.aspx",),
    "Alphabet": ("https://abc.xyz/investor/",),
    "Meta": ("https://investor.atmeta.com/financials/default.aspx",),
    "Nvidia": ((
        "https://investor.nvidia.com/financial-info/"
        "financial-reports-and-results/default.aspx"
    ),),
    "Apple": ("https://investor.apple.com/investor-relations/default.aspx",),
    "Tesla": (
        "https://ir.tesla.com/press",
        (
            "https://ir.tesla.com/press-release/"
            "tesla-releases-second-quarter-2026-financial-results"
        ),
        "https://ir.tesla.com/#quarterly-disclosure",
    ),
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


@dataclass
class SecClient:
    """Minimal SEC JSON client with an attributable User-Agent."""

    user_agent: str
    request: Callable[[str, str], dict[str, Any]] | None = None
    sleeper: Callable[[float], None] = time.sleep
    request_spacing_seconds: float = 0.25
    retry_delays: tuple[float, ...] = (2.0, 5.0)

    def fetch_submissions(self, cik: str) -> dict[str, Any]:
        return self._fetch(f"https://data.sec.gov/submissions/CIK{cik}.json")

    def fetch_companyfacts(self, cik: str) -> dict[str, Any]:
        return self._fetch(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        )

    def _fetch(self, url: str) -> dict[str, Any]:
        if self.request:
            return self.request(url, self.user_agent)
        last_error: Exception | None = None
        for retry_delay in (*self.retry_delays, 0.0):
            self.sleeper(self.request_spacing_seconds)
            request = Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "From": self.user_agent.rsplit(" ", 1)[-1],
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "Connection": "close",
                },
            )
            try:
                with urlopen(  # noqa: S310 - fixed SEC host.
                    request, timeout=60
                ) as response:
                    body = response.read()
                    if response.headers.get("Content-Encoding") == "gzip":
                        body = gzip.decompress(body)
                    return json.loads(body)
            except Exception as exc:  # Provider boundary; preserve final status.
                last_error = exc
                if retry_delay:
                    self.sleeper(retry_delay)
        raise AIRevolutionError(_error_details(last_error))


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


@dataclass
class OfficialIRClient:
    """Fetch and fingerprint official investor-relations landing pages."""

    user_agent: str
    request: Callable[[str, str], bytes | str] | None = None

    def fetch(self, url: str) -> dict[str, Any]:
        if self.request:
            body = self.request(url, self.user_agent)
            if isinstance(body, str):
                body = body.encode("utf-8")
        else:
            request = Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Encoding": "gzip",
                },
            )
            try:
                with urlopen(request, timeout=60) as response:  # noqa: S310
                    body = response.read()
                    if response.headers.get("Content-Encoding") == "gzip":
                        body = gzip.decompress(body)
            except Exception as exc:
                raise AIRevolutionError(_error_details(exc)) from exc
        if body.startswith(b"%PDF"):
            if len(body) < 1_000:
                raise AIRevolutionError("Official IR PDF returned insufficient content")
            return {
                "source_url": url,
                "content_sha256": hashlib.sha256(body).hexdigest(),
                "content_length": len(body),
                "content_kind": "PDF",
            }
        parser = _VisibleTextParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        normalized = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
        if len(normalized) < 100:
            raise AIRevolutionError("Official IR page returned insufficient content")
        return {
            "source_url": url,
            "content_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "content_length": len(normalized),
            "content_kind": "HTML",
        }

    def fetch_first(self, urls: tuple[str, ...]) -> dict[str, Any]:
        """Return the first reachable official endpoint and retain all failures."""

        errors = []
        for url in urls:
            try:
                return self.fetch(url)
            except Exception as exc:
                errors.append(f"{url}: {_error_details(exc)}")
        raise AIRevolutionError("; ".join(errors))


def _error_details(exc: Exception | None) -> str:
    """Return an auditable provider error without leaking request headers."""

    if isinstance(exc, HTTPError):
        return f"HTTP {exc.code}: {exc.reason}"
    if exc is None:
        return "Unknown SEC provider error"
    return f"{type(exc).__name__}: {exc}"


def tesla_update_urls(reference: datetime) -> tuple[str, ...]:
    """Build newest-first official Tesla quarterly-update PDF candidates."""

    year = reference.year
    quarter = (reference.month - 1) // 3 + 1
    urls = []
    for _ in range(6):
        urls.append(
            "https://assets-ir.tesla.com/tesla-contents/IR/"
            f"TSLA-Q{quarter}-{year}-Update.pdf"
        )
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    return tuple(urls)


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
    ir_client: OfficialIRClient | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Refresh seven-company SEC evidence and gate stale qualitative signals."""

    previous = previous or {}
    review = review or {}
    previous_companies = {
        item.get("company"): item for item in previous.get("companies", [])
    }
    companies = []
    sec_valid = 0
    official_valid = 0
    changed = []
    reference_time = (
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if generated_at
        else datetime.now(timezone.utc)
    )

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
            evidence_revision = f"sec:{new_accession}" if new_accession else None
            companies.append(
                {
                    "company": company,
                    "cik": cik,
                    "data_status": "VALID",
                    "evidence_source": "SEC",
                    "evidence_revision": evidence_revision,
                    "latest_periodic_filing": filing,
                    "latest_capex_fact": capex,
                    "latest_operating_cash_flow_fact": operating_cash_flow,
                    "filing_changed": filing_changed,
                    "interpretation_policy": (
                        "Raw official evidence only; AI attribution and ROI require review."
                    ),
                }
            )
            sec_valid += 1
            official_valid += 1
        except Exception as exc:  # One issuer must not erase six valid records.
            old = previous_companies.get(company)
            refresh_error = _error_details(exc)
            ir_evidence = None
            ir_error = None
            if ir_client:
                try:
                    urls = OFFICIAL_IR_URLS[company]
                    if company == "Tesla":
                        urls = tesla_update_urls(reference_time) + urls
                    ir_evidence = ir_client.fetch_first(urls)
                except Exception as ir_exc:
                    ir_error = _error_details(ir_exc)
            if ir_evidence:
                old_hash = (old or {}).get("official_ir", {}).get("content_sha256")
                content_changed = ir_evidence["content_sha256"] != old_hash
                if content_changed:
                    changed.append(company)
                companies.append(
                    {
                        "company": company,
                        "cik": cik,
                        "data_status": "OFFICIAL_IR_AVAILABLE",
                        "evidence_source": "OFFICIAL_IR",
                        "evidence_revision": f"ir:{ir_evidence['content_sha256']}",
                        "latest_periodic_filing": (old or {}).get(
                            "latest_periodic_filing"
                        ),
                        "latest_capex_fact": (old or {}).get("latest_capex_fact"),
                        "latest_operating_cash_flow_fact": (old or {}).get(
                            "latest_operating_cash_flow_fact"
                        ),
                        "official_ir": {
                            **ir_evidence,
                            "fetched_at": generated_at
                            or datetime.now(timezone.utc).isoformat(),
                            "content_changed": content_changed,
                        },
                        "filing_changed": False,
                        "sec_refresh_error": refresh_error,
                        "interpretation_policy": (
                            "Official IR change detection only; quantitative facts, "
                            "AI attribution and ROI require review."
                        ),
                    }
                )
                official_valid += 1
            elif old:
                companies.append(
                    {
                        **old,
                        "data_status": "STALE",
                        "refresh_error": refresh_error,
                        "official_ir_refresh_error": ir_error,
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
                        "refresh_error": refresh_error,
                        "official_ir_refresh_error": ir_error,
                    }
                )

    reviewed_revisions = review.get("reviewed_revisions")
    if reviewed_revisions is None:
        reviewed_revisions = {
            company: f"sec:{accession}"
            for company, accession in review.get("reviewed_accessions", {}).items()
        }
    unreviewed = [
        item["company"]
        for item in companies
        if not item.get("evidence_revision")
        or item.get("evidence_revision") != reviewed_revisions.get(item["company"])
    ]
    review_required = official_valid != len(COMPANIES) or bool(unreviewed)
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
        "schema_version": "1.1",
        "generated_at": generated,
        "source_policy": (
            "SEC filings/companyfacts primary; official company IR pages fallback"
        ),
        "companies_expected": len(COMPANIES),
        "companies_valid": official_valid,
        "data_coverage_pct": round(official_valid / len(COMPANIES) * 100, 2),
        "companies_sec_structured_valid": sec_valid,
        "sec_structured_coverage_pct": round(sec_valid / len(COMPANIES) * 100, 2),
        "companies_official_evidence_valid": official_valid,
        "official_evidence_coverage_pct": round(
            official_valid / len(COMPANIES) * 100, 2
        ),
        "cache_status": (
            "VALID"
            if official_valid == len(COMPANIES)
            else "PARTIAL"
            if official_valid
            else "UNKNOWN"
        ),
        "review_required": review_required,
        "unreviewed_companies": unreviewed,
        "new_periodic_filings": changed,
        "signals": signals,
        "companies": companies,
        "decision_policy": (
            "Do not output current AI lights unless every current evidence revision "
            "(SEC accession or official IR fingerprint) has been reviewed."
        ),
    }

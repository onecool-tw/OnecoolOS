"""Convert dated, source-backed raw filing inputs, never stored scores."""

from datetime import date

from onecool_os.market.us_breakout_scan import (
    FundamentalMetrics, US_SECURITY_MASTER, _optional_number,
    fundamental_validation_error,
)


def load_reviewed_fundamentals(payload, expected_as_of):
    expected = date.fromisoformat(expected_as_of)
    results = {}
    selected_versions = {}
    for row in payload.get("results", []):
        try:
            symbol = row["symbol"]
            if symbol not in US_SECURITY_MASTER or row["accounting_basis"] != "GAAP":
                continue
            if row["review_status"] != "VERIFIED" or not row["sources"]:
                continue
            sources = row["sources"]
            published = max(date.fromisoformat(s["published_as_of"]) for s in sources)
            effective = date.fromisoformat(row.get("effective_from", published.isoformat()))
            if not published <= effective <= expected or effective > date.fromisoformat(row["valid_through"]):
                continue
            if any(not s["url"].startswith("https://") or
                   date.fromisoformat(s["published_as_of"]) > expected for s in sources):
                continue
            rates = []
            for key in ("quarterly_eps", "quarterly_revenue", "annual_eps"):
                pair = row[key]
                current, prior = pair["current"], pair["prior"]
                if _optional_number(current) is None or _optional_number(prior) is None or prior <= 0:
                    raise ValueError("nonpositive or missing comparison base")
                if not 350 <= (date.fromisoformat(pair["period_end"]) -
                               date.fromisoformat(pair["prior_period_end"])).days <= 380:
                    raise ValueError("not a comparable yearly period")
                if date.fromisoformat(pair["period_end"]) > expected:
                    raise ValueError("future period")
                rates.append(current / prior - 1)
            if row["quarterly_eps"]["period_end"] != row["quarterly_revenue"]["period_end"]:
                continue
            f = FundamentalMetrics(
                as_of=row["quarterly_eps"]["period_end"],
                quarterly_eps_growth=rates[0], quarterly_revenue_growth=rates[1],
                annual_eps_growth=rates[2],
                institutional_holders_available=row.get("institutional_holders_available", False),
                source_urls=tuple(s["url"] for s in sources),
                published_as_of=max(s["published_as_of"] for s in sources),
                valid_through=row["valid_through"],
            )
            if fundamental_validation_error(f, expected) is None:
                version = (f.as_of, effective, published)
                if symbol not in selected_versions or version > selected_versions[symbol]:
                    results[symbol] = f
                    selected_versions[symbol] = version
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            continue
    return results

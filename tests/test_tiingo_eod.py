"""The independent EOD source must stay transient and fail closed."""

import io
import json
from datetime import date
from urllib.error import HTTPError

import pytest

from onecool_os.market.tiingo_eod import TiingoEODClient, TiingoEODError


def test_bounded_window_and_auth_header() -> None:
    requests = []

    def request(query, *, timeout):
        requests.append((query, timeout))
        return io.BytesIO(json.dumps([{"date": "2026-09-22"}]).encode())

    rows = TiingoEODClient("private-token", request=request).fetch_window(
        "AAPL", date(2026, 9, 21), date(2026, 9, 23))
    assert rows == [{"date": "2026-09-22"}]
    assert requests[0][0].get_header("Authorization") == "Token private-token"
    assert "private-token" not in requests[0][0].full_url
    assert requests[0][1] == 15


def test_provider_error_does_not_include_credentials() -> None:
    def request(query, *, timeout):
        raise HTTPError(query.full_url, 429, "private-token", {}, None)

    with pytest.raises(TiingoEODError, match="^HTTP_429$") as error:
        TiingoEODClient("private-token", request=request).fetch_window(
            "AAPL", date(2026, 9, 21), date(2026, 9, 23))
    assert "private-token" not in str(error.value)

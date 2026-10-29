import io

import pytest

from onecool_os.market import us_valuation_inputs


@pytest.mark.parametrize("identity", [None, "", "   \t"])
def test_blank_sec_identity_uses_attributable_default(monkeypatch, identity):
    def open_request(request, timeout):
        assert request.get_header("User-agent") == "OnecoolOS research onecool-tw@users.noreply.github.com"
        assert request.get_header("Accept") == "application/json"
        assert timeout == 12
        return io.BytesIO(b'{"cik": 320193}')

    monkeypatch.setattr(us_valuation_inputs, "urlopen", open_request)
    assert us_valuation_inputs.fetch_sec_json("https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json", identity) == {"cik": 320193}


def test_configured_sec_identity_is_preserved(monkeypatch):
    def open_request(request, timeout):
        assert request.get_header("User-agent") == "Luke research luke@example.com"
        return io.BytesIO(b'{}')

    monkeypatch.setattr(us_valuation_inputs, "urlopen", open_request)
    assert us_valuation_inputs.fetch_sec_json("https://data.sec.gov/submissions/CIK0000320193.json", "  Luke research luke@example.com  ") == {}

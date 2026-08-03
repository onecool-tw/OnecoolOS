from datetime import date
from types import SimpleNamespace

from scripts.update_stockq_rotation import _fetch_twd_fx


def bar(day: date, value: float):
    return SimpleNamespace(
        trading_date=day,
        adjusted_close=value,
        close=value,
    )


class InverseBridgeBootstrapper:
    def __init__(self) -> None:
        self.calls = []

    def fetch_adjusted_daily(self, symbol: str):
        self.calls.append(symbol)
        if symbol in {"PLNTWD=X", "PLNUSD=X"}:
            raise RuntimeError("direct pair unavailable")
        if symbol == "USDPLN=X":
            return [
                bar(date(2026, 7, 24), 4.0),
                bar(date(2026, 7, 31), 5.0),
            ]
        if symbol == "USDTWD=X":
            return [
                bar(date(2026, 7, 24), 32.0),
                bar(date(2026, 7, 31), 33.0),
            ]
        raise AssertionError(symbol)


def test_pln_twd_uses_inverse_usd_bridge_when_direct_pair_fails() -> None:
    client = InverseBridgeBootstrapper()

    values, method = _fetch_twd_fx("PLNTWD=X", client)

    assert method == "TRIANGULAR:1/USDPLN=X*USDTWD=X"
    assert [(item.value_date, item.value) for item in values] == [
        (date(2026, 7, 24), 8.0),
        (date(2026, 7, 31), 6.6),
    ]
    assert "PLNUSD=X" not in client.calls

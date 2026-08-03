from datetime import date, timedelta

from onecool_os.market.etf_cta import DailyBar
from scripts.update_stockq_rotation import (
    REQUIRED_TWD_FX_SYMBOLS,
    TRIANGULAR_TWD_FX,
    TWD_SERIES,
    _fetch_twd_fx,
)


def test_required_twd_currency_pairs_are_covered() -> None:
    assert REQUIRED_TWD_FX_SYMBOLS <= {
        fx_symbol for _, fx_symbol in TWD_SERIES.values()
    }


def test_current_stockq_names_and_currency_groups_are_mapped() -> None:
    expected = {
        "波蘭股市": ("^WIG", "PLNTWD=X"),
        "S&P 500": ("^GSPC", "USDTWD=X"),
        "費城半導體": ("^SOX", "USDTWD=X"),
        "NBI生技": ("^NBI", "USDTWD=X"),
        "德國DAX": ("^GDAXI", "EURTWD=X"),
        "奧地利": ("^ATX", "EURTWD=X"),
        "西班牙": ("^IBEX", "EURTWD=X"),
        "義大利": ("FTSEMIB.MI", "EURTWD=X"),
        "葡萄牙": ("PSI20.LS", "EURTWD=X"),
        "英國": ("^FTSE", "GBPTWD=X"),
        "澳洲": ("^AXJO", "AUDTWD=X"),
        "加拿大": ("^GSPTSE", "CADTWD=X"),
        "瑞士": ("^SSMI", "CHFTWD=X"),
        "印度": ("^NSEI", "INRTWD=X"),
        "印尼": ("^JKSE", "IDRTWD=X"),
        "馬來西亞": ("^KLSE", "MYRTWD=X"),
        "菲律賓": ("PSEI.PS", "PHPTWD=X"),
        "泰國": ("^SET.BK", "THBTWD=X"),
        "新加坡": ("^STI", "SGDTWD=X"),
        "日經225": ("^N225", "JPYTWD=X"),
        "南韓": ("^KS11", "KRWTWD=X"),
        "香港恆生": ("^HSI", "HKDTWD=X"),
        "匈牙利": ("^BUX", "HUFTWD=X"),
    }

    for market, series in expected.items():
        assert TWD_SERIES[market] == series


def test_every_mapping_uses_a_direct_twd_pair() -> None:
    assert all(fx_symbol.endswith("TWD=X") for _, fx_symbol in TWD_SERIES.values())


def test_pln_and_huf_have_same_date_usd_bridge() -> None:
    assert TRIANGULAR_TWD_FX["PLNTWD=X"] == (
        ("USDPLN=X", "USDTWD=X", True),
        ("PLNUSD=X", "USDTWD=X", False),
    )
    assert TRIANGULAR_TWD_FX["HUFTWD=X"] == (
        ("USDHUF=X", "USDTWD=X", True),
        ("HUFUSD=X", "USDTWD=X", False),
    )


def test_fx_falls_back_to_same_date_triangulation() -> None:
    start = date(2026, 7, 1)

    class Bootstrapper:
        def fetch_adjusted_daily(self, symbol):
            if symbol in {"PLNTWD=X", "USDPLN=X"}:
                raise RuntimeError("direct pair unavailable")
            value = 0.25 if symbol == "PLNUSD=X" else 30.0
            return [
                DailyBar(
                    trading_date=start + timedelta(days=index),
                    open=value,
                    high=value,
                    low=value,
                    close=value,
                    volume=0,
                    adjusted_close=value,
                )
                for index in range(2)
            ]

    values, method = _fetch_twd_fx("PLNTWD=X", Bootstrapper())

    assert method == "TRIANGULAR:PLNUSD=X*USDTWD=X"
    assert [item.value for item in values] == [7.5, 7.5]


def test_fx_uses_inverse_same_date_triangulation() -> None:
    start = date(2026, 7, 1)

    class Bootstrapper:
        def fetch_adjusted_daily(self, symbol):
            if symbol == "PLNTWD=X":
                raise RuntimeError("direct pair unavailable")
            value = 4.0 if symbol == "USDPLN=X" else 30.0
            return [
                DailyBar(
                    trading_date=start + timedelta(days=index),
                    open=value,
                    high=value,
                    low=value,
                    close=value,
                    volume=0,
                    adjusted_close=value,
                )
                for index in range(2)
            ]

    values, method = _fetch_twd_fx("PLNTWD=X", Bootstrapper())

    assert method == "TRIANGULAR:1/USDPLN=X*USDTWD=X"
    assert [item.value for item in values] == [7.5, 7.5]

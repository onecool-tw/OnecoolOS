import json
from decimal import Decimal
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.assets.cash.loader import CashLoader, CashLoaderError
from onecool_os.assets.cash.models import CashAsset, CashError, CashPosition


def write_settings(config_dir: Path, root_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        f"""
app:
  name: Onecool OS
  version: 0.5.0
  timezone: Asia/Taipei
  language: en
database:
  path: {root_dir / "onecool.sqlite3"}
paths:
  data_dir: {root_dir / "data"}
  cache_dir: {root_dir / "cache"}
  logs_dir: {root_dir / "logs"}
  exports_dir: {root_dir / "exports"}
runtime:
  debug: false
  environment: test
logging:
  level: INFO
""".strip(),
        encoding="utf-8",
    )


def test_cash_asset_creation() -> None:
    cash = sample_cash_asset()
    asset = cash.to_asset()

    assert cash.asset_type == "CASH"
    assert cash.currency == "USD"
    assert cash.institution == "Demo Brokerage"
    assert asset.asset_type == "CASH"
    assert asset.symbol == "USD"


def test_cash_asset_rejects_invalid_currency() -> None:
    try:
        CashAsset(
            asset_id="bad",
            asset_type="CASH",
            name="Bad Cash",
            currency="usd",
            account_type="checking",
        )
    except CashError as exc:
        assert "Invalid currency" in str(exc)
    else:
        raise AssertionError("Invalid currency should be rejected.")


def test_cash_position_market_value() -> None:
    position = CashPosition(
        asset=sample_cash_asset(),
        amount=Decimal("2500"),
        currency="USD",
        fx_rate_to_base=Decimal("32.5"),
        base_currency="TWD",
        notes="Demo only.",
    )

    assert position.market_value() == Decimal("2500")
    assert position.market_value_base() == Decimal("81250.0")
    assert position.unrealized_pnl() == Decimal("0")


def test_cash_position_base_currency_without_fx_rate() -> None:
    asset = CashAsset(
        asset_id="CASH-TWD-DEMO",
        asset_type="CASH",
        name="Demo TWD Cash",
        currency="TWD",
        account_type="checking",
    )
    position = CashPosition(
        asset=asset,
        amount=Decimal("120000"),
        currency="TWD",
        fx_rate_to_base=None,
        base_currency="TWD",
        notes="Demo only.",
    )

    assert position.market_value_base() == Decimal("120000")


def test_cash_loader_valid_json(tmp_path: Path) -> None:
    result = CashLoader().load(write_cash_json(tmp_path))

    assert len(result.positions) == 2
    assert result.positions[0].asset.name == "Demo TWD Cash"
    assert result.positions[1].market_value_base() == Decimal("81250.0")


def test_cash_loader_invalid_json(tmp_path: Path) -> None:
    json_path = tmp_path / "cash.json"
    json_path.write_text("{invalid", encoding="utf-8")

    try:
        CashLoader().load(json_path)
    except CashLoaderError as exc:
        assert "Invalid cash JSON" in str(exc)
    else:
        raise AssertionError("Invalid JSON should be rejected.")


def test_cash_loader_missing_fields(tmp_path: Path) -> None:
    payload = cash_json_payload()
    del payload["cash_accounts"][0]["amount"]
    json_path = write_cash_json(tmp_path, payload)

    try:
        CashLoader().load(json_path)
    except CashLoaderError as exc:
        assert "Missing required field" in str(exc)
        assert "amount" in str(exc)
    else:
        raise AssertionError("Missing fields should be rejected.")


def test_cash_loader_invalid_amount(tmp_path: Path) -> None:
    payload = cash_json_payload()
    payload["cash_accounts"][0]["amount"] = "-1"
    json_path = write_cash_json(tmp_path, payload)

    try:
        CashLoader().load(json_path)
    except CashLoaderError as exc:
        assert "Invalid amount" in str(exc)
    else:
        raise AssertionError("Invalid amount should be rejected.")


def test_cash_loader_invalid_currency(tmp_path: Path) -> None:
    payload = cash_json_payload()
    payload["cash_accounts"][0]["currency"] = "twd"
    json_path = write_cash_json(tmp_path, payload)

    try:
        CashLoader().load(json_path)
    except CashLoaderError as exc:
        assert "Invalid currency" in str(exc)
    else:
        raise AssertionError("Invalid currency should be rejected.")


def test_cash_loader_invalid_fx_rate(tmp_path: Path) -> None:
    payload = cash_json_payload()
    payload["cash_accounts"][1]["fx_rate_to_base"] = "0"
    json_path = write_cash_json(tmp_path, payload)

    try:
        CashLoader().load(json_path)
    except CashLoaderError as exc:
        assert "Invalid fx_rate_to_base" in str(exc)
    else:
        raise AssertionError("Invalid fx_rate should be rejected.")


def test_cli_cash_demo_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    assert main(["cash", "demo"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["cash_accounts"]) == 2
    assert payload["cash_accounts"][0]["cash_account"] == "Demo TWD Cash"
    assert payload["cash_accounts"][0]["currency"] == "TWD"
    assert payload["cash_accounts"][0]["amount"] == "120000.00"
    assert payload["cash_accounts"][0]["fx_rate_to_base"] is None
    assert payload["cash_accounts"][0]["base_currency_value"] == "120000.00"
    assert payload["cash_accounts"][1]["cash_account"] == "Demo USD Cash"
    assert payload["cash_accounts"][1]["fx_rate_to_base"] == "32.50"
    assert payload["cash_accounts"][1]["base_currency_value"] == "81250.00"


def sample_cash_asset() -> CashAsset:
    return CashAsset(
        asset_id="CASH-USD-DEMO",
        asset_type="CASH",
        name="Demo USD Cash",
        currency="USD",
        account_type="savings",
        institution="Demo Brokerage",
        country="United States",
    )


def cash_json_payload() -> dict[str, object]:
    return {
        "cash_accounts": [
            {
                "asset_id": "CASH-TWD-DEMO",
                "asset_type": "CASH",
                "name": "Demo TWD Cash",
                "currency": "TWD",
                "account_type": "checking",
                "institution": "Demo Bank",
                "country": "Taiwan",
                "amount": "120000",
                "fx_rate_to_base": "",
                "base_currency": "TWD",
                "notes": "Sample TWD cash balance only.",
            },
            {
                "asset_id": "CASH-USD-DEMO",
                "asset_type": "CASH",
                "name": "Demo USD Cash",
                "currency": "USD",
                "account_type": "savings",
                "institution": "Demo Brokerage",
                "country": "United States",
                "amount": "2500",
                "fx_rate_to_base": "32.5",
                "base_currency": "TWD",
                "notes": "Sample USD cash balance only.",
            },
        ],
    }


def write_cash_json(
    tmp_path: Path,
    payload: dict[str, object] | None = None,
) -> Path:
    json_path = tmp_path / "cash.json"
    json_path.write_text(
        json.dumps(payload or cash_json_payload()),
        encoding="utf-8",
    )
    return json_path
